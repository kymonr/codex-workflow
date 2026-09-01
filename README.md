# Codex Workflow

Codex 上的 Claude 风格 JavaScript Dynamic Workflow 宿主。

模型编写 JavaScript；本地宿主隔离执行；每个 `agent()` 变成一次 `codex exec`。这不是声明式 IR 产品。

旧的声明式 Dynamic Workflow 仍在：

`D:\codex\projects\codex-dynamic-workflow`

本仓库与它分开维护，不兼容双运行时。

## 当前状态

PR2：隔离 QuickJS 沙箱 + 异步只读 `agent()` + `parallel()` / `pipeline()`。

已实现：

- 脚本在嵌入式 QuickJS 里跑，没有 Node 的 `fs` / `os` / `require`
- `Date.now()`、`new Date()`、`Math.random()`、`eval`、`Function` 被关掉
- `agent()` 立即返回 Promise；宿主在有界线程池里执行 agent，QuickJS 上下文始终只由主线程操作
- 默认并发上限为 `min(16, max(1, (CPU 数或 2) - 2))`，单次运行最多登记 1000 个 agent
- `parallel()` 并发执行函数数组；单个槽失败变成 `null`，其它槽继续
- `pipeline()` 为每个条目启动独立阶段链，没有跨条目的阶段屏障；某条目失败后该槽为 `null`
- `parallel()` 和 `pipeline()` 的输入数组最多 4096 项，超过时拒绝，不静默截断
- 所有普通 agent 只能变成 `codex exec -s read-only`
- 每次运行写出目录：脚本副本、`journal.jsonl`、每个 agent 的 argv / last message / 日志
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

`--mock` 不会启动真实 `codex exec`，只检查沙箱和锁定的命令行。真实运行会消耗 Codex 额度，需要时再去掉 `--mock`。

## 硬规则

- 默认 `codex exec -s read-only`
- 只有 `isolation: "worktree"` 才允许在宿主创建的隔离 worktree 里使用 `-s workspace-write`；该能力尚未实现，当前一律拒绝
- 禁止 `danger-full-access`、`--full-auto`、`--approval-policy`，以及会改变沙箱或审批语义的 `-c` / `--config`（唯一放行的 `-c` 是 `model_reasoning_effort`）
- 不自动 apply 到主目录，不自动 `git add` / commit / push
