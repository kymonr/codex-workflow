# Codex Workflow

面向 Codex 的 JavaScript Dynamic Workflow 宿主。

模型或用户编写 JavaScript；Python 宿主在受限 QuickJS 中执行动态控制流；
每个 `agent()` 由宿主转换成经过白名单校验的 `codex exec`。本项目不是声明式
Workflow IR，也不读取旧产品的运行时或配置。

> 当前状态：实验性 / pre-alpha。CLI 已使用独立 runtime 进程监督，但工作流脚本
> 仍应视为可信输入；请先用 `--mock` 验收，再决定是否运行真实 Codex。

## 已实现

- 受限 QuickJS：无 Node、`std`、`os`、`require`、`process` 或任意 shell
- 禁用 `Date`、`Math.random`、`eval` 和直接/间接 `Function` 构造器
- 异步 Promise 版 `agent()`，QuickJS 上下文始终只由单线程操作
- `parallel()`：槽位隔离失败，保持输入顺序
- `pipeline()`：每个条目独立推进，不引入跨条目的阶段屏障
- `phase(title)`：只记录 journal 分组，不改变调度
- 脚本级 `args`、诚实的 `budget` 视图和硬 `--max-agents`
- `--resume-from`：按 agent 调用顺序执行前缀缓存
- 宿主创建的隔离 Git worktree，可授权单个 agent 使用 `workspace-write`
- 一层 `workflow({scriptPath}, args)` 嵌套，共享泵、上限、journal 和 resume 指针
- 外部 supervisor、wall-clock 超时、Ctrl+C/失败取消和子进程树终止
- agent stdout/stderr 直接流式写入独立日志文件

## 快速开始

要求 Python 3.12，固定依赖 `quickjs==1.19.4`。

```text
py -3.12 -m pip install -e .
py -3.12 -m unittest discover -s tests -t . -v
codex-workflow run examples/hello.js --mock
codex-workflow run examples/parallel-hello.js --mock
codex-workflow run examples/nested-parent.js --mock --args-file examples/nested-args.json
```

CLI 默认通过 supervisor 启动独立 runtime 进程，wall-clock 超时为 3600 秒。
未安装 console script 时，也可使用 `py -3.12 -m workflow` 执行同一 CLI。
可使用 `--timeout-seconds` 调整。`--mock` 不会启动真实 `codex exec`，但仍执行
脚本、参数校验、schema 校验、argv 构造、journal 和运行产物写入。
若脚本请求 `isolation: "worktree"`，mock 仍会创建真实 Git worktree，
只是不会启动 Codex。

## JavaScript 示例

```javascript
phase("Scan");

const results = await parallel([
  function () {
    return agent("只读分析入口模块", { label: "entry" });
  },
  function () {
    return agent("只读分析测试覆盖", { label: "tests" });
  }
]);

const verified = await pipeline(
  results,
  function (previous, original, index) {
    return agent("复核第 " + index + " 项：" + String(previous));
  }
);

if (budget.total && budget.remaining() > 50000) {
  await agent("在预算目标存在时继续分析");
}

await workflow(
  { scriptPath: "nested-child.js" },
  { q: args.q }
);
```

`budget.spent()` 当前固定返回 `0`，因为 Codex CLI 尚无可靠、统一的 token usage
输入。`--budget-tokens` 是脚本可见的目标，不是假装存在的硬 token 上限；真正的
硬停止由 `--max-agents` 和 supervisor 超时提供。

## CLI

```text
codex-workflow --version
codex-workflow run <script>
  [--mock]
  [--runs-root <path>]
  [--cd <workdir>]
  [-m <model>]
  [--effort low|medium|high|xhigh]
  [--args <json> | --args-file <path>]
  [--budget-tokens <positive-int>]
  [--max-agents <1..1000>]
  [--resume-from <old-run-dir>]
  [--timeout-seconds <positive-finite-number>]
```

`--resume-from` 是严格的调用顺序前缀缓存：第一处 identity 不一致后，本次运行
余下的 agent 全部转为 live，不会在旧 journal 中重新搜索匹配项。缓存命中不占
live agent 上限，但仍写入新 journal 并标记 `"cache": true`。

## 权限边界

普通 agent 的 argv 固定包含：

```text
codex exec
  -s read-only
  -C <absolute-workdir>
  -c model_reasoning_effort=<allowed>
  --color never
  --output-last-message <absolute-path>
```

只有 `isolation: "worktree"` 才会由宿主创建隔离 Git worktree，并将该 agent
切换为 `-s workspace-write`。JavaScript 不能指定 worktree 路径、argv、sandbox
或审批策略。worktree 不自动 apply、commit、删除或合并，留给用户检查。

任何路径都继续禁止：

- `danger-full-access`
- `--full-auto`
- `--approval-policy` / `--ask-for-approval`
- `--dangerously-bypass-approvals-and-sandbox`
- 任意额外 `-c` / `--config`
- 自动 `git add`、commit、push、merge、checkout 或 reset

## 运行产物

```text
<runs-root>/<timestamp>-<script>/
  script.js
  journal.jsonl
  agents/000-<label>/
    argv.json
    schema.json        # 可选
    last.txt
    stdout.log
    stderr.log
```

`journal.jsonl` 当前版本为 1。它记录完整 prompt、resolved opts、argv 和模型结果，
因此可能包含源代码或敏感信息；不要把运行目录直接公开。

## 已知限制

- supervisor 能终止同步无限循环，但被强制终止的 run 可能留下没有
  `run.finished` 的不完整 journal。
- token usage 尚未接入，`budget.spent()` 不会下降。
- resume 依赖实际 agent 调用顺序；并发 pipeline 的完成时序变化可能降低后续
  前缀命中率。
- worktree 由宿主保留，不自动清理；请确认修改后手工处理。
- Windows `.cmd` Codex shim 仍应在发布前持续做特殊字符回归测试。
- 当前是实验性实现，不宣称能安全执行任意来源的不可信 JavaScript。

## 文档

- [`docs/API.md`](docs/API.md)：JavaScript 和 CLI 合同
- [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md)：能力边界与剩余风险
- [`docs/JOURNAL.md`](docs/JOURNAL.md)：运行目录与 journal v1
- [`SECURITY.md`](SECURITY.md)：安全问题报告方式
- [`CONTRIBUTING.md`](CONTRIBUTING.md)：开发与验收要求
- [`CHANGELOG.md`](CHANGELOG.md)：版本变更
- [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md)：公开发布前检查

## 许可证

仓库目前尚未选择开源许可证。公开可见不等于获得复制、修改或再发布许可；
发布正式版本前需要由仓库所有者明确选择许可证。
