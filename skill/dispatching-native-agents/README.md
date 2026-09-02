# dispatching-native-agents

给 **Codex 桌面会话**使用的原生子代理派工说明书。子代理必须使用原生 `spawn_agent`：默认由 Luna 做事实覆盖；Sol 负责判断门卫、设计选择、默认写入和难以逆转的工作，但保持稀缺；短小、机械、只读的任务可以使用 Spark；用户明确指定其他 model/effort 时使用 Custom（`agent_type=default`）。不是 `codex exec`、`python -m workflow`、CLI 或任何 JavaScript host。

完整派工、Sol gate、生命周期和写入边界见 [SKILL.md](SKILL.md)；多波次模式见 [references/patterns.md](references/patterns.md)。

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

完成发现后，在对话中显式调用：

```text
$dispatching-native-agents
```

`agents/openai.yaml` 默认关闭隐式触发，避免迁移期间与旧的 `dynamic-workflow` skill 抢占普通任务。隐式触发状态以该文件中的 `policy.allow_implicit_invocation` 为准。
