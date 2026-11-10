from uuid import uuid4

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Artifact, Part, Task, TaskState, TaskStatus


class HelloWorldAgent:
    async def invoke(self) -> str:
        return "Hello World"


class HelloWorldAgentExecutor(AgentExecutor):
    def __init__(self):
        self.agent = HelloWorldAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        result = await self.agent.invoke()

        # The course replies with a plain Message, which is never stored.
        # Here we reply with a completed Task, so the task store (Redis)
        # has something to persist. In a2a-sdk 1.x a new task must start
        # with a Task object.
        await event_queue.enqueue_event(
            Task(
                id=context.task_id,
                context_id=context.context_id,
                status=TaskStatus(state=TaskState.TASK_STATE_COMPLETED),
                artifacts=[
                    Artifact(
                        artifact_id=uuid4().hex,
                        name="Result",
                        parts=[Part(text=result)],
                    )
                ],
            )
        )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        raise Exception("Cancellation is not supported.")
