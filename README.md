# Codex Workflow

Codex 上的 Claude 风格 JavaScript Dynamic Workflow 宿主。

模型编写 JavaScript；本地宿主隔离执行；每个 `agent()` 变成一次 `codex exec`。这不是声明式 IR 产品。

旧的声明式 Dynamic Workflow 仍在：

`D:\codex\projects\codex-dynamic-workflow`

本仓库与它分开维护，不兼容双运行时。

## 当前状态

接手前基线。尚未实现 JS 沙箱、`agent()`、pipeline、resume。

## 硬规则

- 默认 `codex exec -s read-only`
- 只有 `isolation: "worktree"` 才允许在宿主创建的隔离 worktree 里使用 `-s workspace-write`
- 禁止 `danger-full-access`、`--full-auto`、`--approval-policy`，以及会改变沙箱或审批语义的 `-c` / `--config`（唯一放行的 `-c` 是 `model_reasoning_effort`）
- 不自动 apply 到主目录，不自动 `git add` / commit / push
