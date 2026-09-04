# dispatching-native-agents

给 **Codex 桌面会话**使用的原生子代理派工与深度审核说明书。子代理必须使用原生 `spawn_agent`：短小、机械、只读且容易复核的分支优先 Spark；Luna 负责事实覆盖；Sol 负责判断门卫、设计选择、默认写入和难以逆转的工作，判断、设计评分和深审门卫可以并行，但不承担搜索覆盖；用户明确指定其他 model/effort 时使用 Custom（`agent_type=default`）。不是 `codex exec`、`python -m workflow`、CLI 或任何 JavaScript host。

完整派工、Sol gate、生命周期和写入边界见 [SKILL.md](SKILL.md)；多波次模式见 [references/patterns.md](references/patterns.md)。

## Routing summary

- 通常按独立 evidence lens 派 2–8 个覆盖代理；该范围只计算 Spark/Luna 查找和 completeness critic，对抗反驳另算。命中深审、判断或高风险触发时，每条结论使用 2–3 个 item-local 反驳人。任何反驳人失败或未返回时，先标记 `contested`；否则，有效票少于 2 或平票也标记 `contested`，只有指向包内证据的多数 `unsupported` 才能否决。`uncertain` 不计票。全部结论被否决时列为 `REJECT`，不算 `completed-empty`。
- 反驳或 Sol 名额少于待审结论时，按严重度只反驳前缀，记录 `verify-cap` 丢掉项，交给 completeness critic 点名捞回；捞回不是新的搜索波，也不准重扫仓库。没有名额压力时不要发明截断。
- 深度审核、全面审核、对抗审核、多代理审核、仓库深审和旧 Agent Fleet 说法都进入自适应深审。
- Root 先核引用，再在 item-local 反驳前复核候选身份；覆盖停波且所有已分配反驳人（含排队项）终结后再次复核并分配稳定 `C-###`，每个 Sol 门卫前和最终作答前再复核。纯事实和 `completed-empty` 路径也执行适用的复核。快照须写出正在审的 ref 与读法；本地 `HEAD` 落后且已点名 published ref 时，不得把工作区当真相。
- Scout/Map 产出冻结只读 brief（facts、risks、关键路径、named refs、as-of 身份），Root 注入每个 Find prompt。Map→Find 是正当屏障；Scout 不派工；brief 不进 refuter/Sol 包；Find 不等待兄弟 Finders 才开始 item-local 反驳。
- 等价临时 claim 复用同一 anchor 和反驳链；稳定 `C-###` 在整个 Root 任务内单调递增，不按波次或阶段重置。可能改变处置的新证据在同一 ID 上增加 evidence revision，只能新增一次对应 Sol gate，不能重跑反驳。
- 去重后，互相独立的判断性结论可以并行进入各自的 Sol 门卫；Sol 也可并行承担设计提案、设计评分和深审反驳，但不承担搜索覆盖。设计使用 2–3 个 Sol 提案、2–3 个新 Sol 评分和 Root 底座嫁接，禁止投票；平分只增加一个 Sol 断平局。
- 实现任务默认一个 writer；Spark 不写入，用户固定 Spark 写入任务时必须停下让用户改选，未固定 route 的 Spark model/effort 精确匹配则用 Custom 保留参数。只有当前请求明确要求并行写、存在两个以上互斥 writer 且适用工作区已有合同，才按该合同创建隔离 worktree，不重复询问创建权限。`D:\codex` 的合同是 `D:\codex\docs\agent-workflows\worktree-parallel-dispatch.md`。
- 子代理首次超时后最多追问一次；追问后的下一次无进展超时会中断一次并记为 `UNKNOWN`，不重放、不改路由。
- Managed Workflow、Worktree Writer v2、固定人数表、强制复现阶段和完整失败状态机不迁移。

## Source and installation

仓库源码目录：

```text
D:\codex\projects\codex-workflow\skill\dispatching-native-agents\
```

安装时先解析当前进程的 `CODEX_HOME`，再同步整个目录到：

```text
<CODEX_HOME>\skills\dispatching-native-agents\
```

只有 `CODEX_HOME` 未设置且目标环境允许使用平台默认目录时，才使用：

```text
~\.codex\skills\dispatching-native-agents\
```

在本工作区中，如果 `CODEX_HOME` 未设置，停止并询问。未经用户明确授权，不要写入 `C:\Users\Orz\.codex`。

源码与安装副本是独立目录，除非现场明确证明它们是链接。修改源码后需要重新同步并验证安装副本；不要根据用户名或历史路径猜测安装位置。

满足 description 时可自动选择本 Skill；需要明确指定时，在对话中显式调用：

```text
$dispatching-native-agents
```

旧 `dynamic-workflow` 的安装目录已删除；运行时 catalog 及实际自动路由以刷新或新开的任务回执为准，静态文件和值不能代替运行时验证。`agents/openai.yaml` 保持 `policy.allow_implicit_invocation: true`。
