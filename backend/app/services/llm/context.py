from contextvars import ContextVar

current_case_id: ContextVar[str | None] = ContextVar("current_case_id", default=None)
current_task: ContextVar[str | None] = ContextVar("current_task", default=None)

# Mutable counter shared across asyncio tasks spawned from the same parent.
# Set to [0] at pipeline entry; llm_client.call() auto-increments.
current_call_count: ContextVar[list[int] | None] = ContextVar("current_call_count", default=None)
