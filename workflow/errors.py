class WorkflowError(Exception):
    """Host or sandbox failure. Message is safe to show to the user."""


class SandboxError(WorkflowError):
    """JavaScript sandbox refused or failed the script."""


class ArgvError(WorkflowError):
    """codex exec argv failed the PR1 allowlist."""


class AgentError(WorkflowError):
    """agent() call failed before, during, or after codex exec."""


class SchemaError(WorkflowError):
    """JSON Schema subset rejected a document or instance."""
