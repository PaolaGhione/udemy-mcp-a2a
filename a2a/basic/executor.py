from uuid import uuid4

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part, Role


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
        message = Message(
            role=Role.ROLE_AGENT,
            parts=[Part(text=result)],
            message_id=uuid4().hex,
        )
        await event_queue.enqueue_event(message)

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        raise Exception("Cancellation is not supported.")
