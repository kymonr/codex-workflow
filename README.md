# Codex Workflow

Codex 上的 JavaScript Dynamic Workflow 宿主。

模型编写 JavaScript；本地宿主执行动态控制流；每个 `agent()` 由宿主转换为受限的 `codex exec`。这不是声明式 IR 产品。

旧的声明式 Dynamic Workflow 仍在：

`D:\codex\projects\codex-dynamic-workflow`

本仓库与它分开维护，不兼容双运行时。

## 当前状态

PR2（稳定化）：能力受限的 QuickJS 运行时 + 异步只读 `agent()` + `parallel()` / `pipeline()`。

已实现：

- 脚本在嵌入式 QuickJS 中运行，没有 Node 的 `fs`、`os`、`require`
- QuickJS 上下文始终只由调用线程操作；agent 工作在有界线程池中执行
- `agent()` 立即返回 Promise；调用序号在 JS 登记时分配，不受 worker 调度顺序影响
- agent 的 opts、schema 和 argv 在进入 worker 前完成预检；预检失败也写入 agent journal
- 运行时 pending、done、error 和宿主 bridge 保存在用户脚本不可引用的闭包中
- `Date`、`Math.random`、`eval`、直接及间接 `Function` 构造器被锁定
- 宿主依赖的 Promise、JSON、Array 和 String 内建引用在脚本运行前捕获
- 默认并发上限为 `min(16, max(1, (CPU 数或 2) - 2))`
- 单次运行最多接受 1000 个可执行 agent
- `parallel()` 保持下标；单个槽失败变成 `null`，其它槽继续
- `pipeline()` 为每个条目启动独立阶段链，没有跨条目的阶段屏障；某条目失败后该槽为 `null`
- `parallel()` 和 `pipeline()` 的输入数组最多 4096 项，超过时拒绝，不静默截断
- schema 使用封闭子集并在执行前严格验证关键词类型、适用范围、上下界和嵌套深度
- 每次运行保存脚本副本、版本化 `journal.jsonl`、每个 agent 的 argv、last message 和日志
- `examples/hello.js` 与 `examples/parallel-hello.js` 可用 `--mock` 验收

尚未实现：`phase()`、args、budget、resume、`isolation: "worktree"`、嵌套 `workflow()`。

## 怎么跑

在项目目录打开终端：

```text
py -3.12 -m pip install -r requirements.txt
py -3.12 -m unittest discover -s tests -t . -v
py -3.12 -m workflow run examples/hello.js --mock
py -3.12 -m workflow run examples/parallel-hello.js --mock
```

`--mock` 不会启动真实 `codex exec`，但仍会执行脚本、预检 opts/schema、构造锁定 argv 并写出完整运行记录。去掉 `--mock` 会启动真实 Codex，消耗额度，并可能把提示词及仓库内容发送给相应服务。

## 安全边界

- 所有普通 agent 固定为 `codex exec -s read-only`
- JavaScript 不能设置 argv、sandbox、审批策略、工作目录或可执行文件
- 唯一放行的 `-c` 是 `model_reasoning_effort=<low|medium|high|xhigh>`
- 禁止 `danger-full-access`、`workspace-write`、`--full-auto`、`--approval-policy`、`--ask-for-approval`、`--config`
- 只有未来由宿主创建并验证的隔离 worktree 才可能使用 `workspace-write`
- 当前不自动 apply 到主目录，不自动 `git add`、commit 或 push
- 脚本、agent payload、prompt 和 schema 都有独立大小上限

## 已知限制

当前运行时面向可信的工作流脚本，不是用于执行任意来源不可信 JavaScript 的对抗性系统沙箱。

QuickJS 启用 Python callable 时不能同时使用 `set_time_limit`。当前还没有外部 supervisor 或运行级 wall-clock watchdog，因此同步无限循环（例如 `while (true) {}`）会卡住运行进程。顶层脚本失败时，已经启动的 agent 也尚不能被主动取消，可能等待到其完成或 900 秒单 agent 超时。

在增加外部进程监督、整棵子进程树取消和资源配额前，不应把本项目暴露为无人值守的公共脚本执行服务。
