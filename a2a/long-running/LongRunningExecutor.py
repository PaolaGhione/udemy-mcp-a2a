import asyncio
from uuid import uuid4

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    Artifact,
    Part,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)


class LongRunningExecutor(AgentExecutor):
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        # 1. Read input from context
        user_text = ""
        if context.message.parts:
            user_text = context.message.parts[0].text

        # 2. Signal Task Submitted
        # In a2a-sdk 1.x the first event of a new task must be a Task object:
        # status updates and artifacts are only accepted after it.
        await event_queue.enqueue_event(
            Task(
                id=context.task_id,
                context_id=context.context_id,
                status=TaskStatus(state=TaskState.TASK_STATE_SUBMITTED),
            )
        )

        # 3. Simulate work with status and artifact updates
        for _ in range(1, 4):
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=context.task_id,
                    context_id=context.context_id,
                    status=TaskStatus(state=TaskState.TASK_STATE_WORKING),
                    metadata={"info": "Working..."},
                )
            )

            await asyncio.sleep(2)  # Long running work

            result_text = f"This is part of the result for: {user_text}"
            artifact = Artifact(
                artifact_id=uuid4().hex,
                name="Artifact",
                description="Partial Result",
                parts=[Part(text=result_text)],
            )

            await event_queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    task_id=context.task_id,
                    context_id=context.context_id,
                    artifact=artifact,
                )
            )

        # 4. Signal Task Completed
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                status=TaskStatus(state=TaskState.TASK_STATE_COMPLETED),
                metadata={"info": "Completed..."},
            )
        )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        pass
