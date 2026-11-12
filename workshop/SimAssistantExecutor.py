import os
import httpx
from typing import List
from uuid import uuid4

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part, Role

from beeai_framework.backend.chat import ChatModel
from beeai_framework.agents.react import ReActAgent
from beeai_framework.memory.token_memory import TokenMemory
from beeai_framework.backend.message import SystemMessage
from beeai_framework.tools import AnyTool
from beeai_framework.tools.mcp import MCPTool

from mcp.client.streamable_http import streamable_http_client
from mcp import ClientSession

MCP_URL = os.environ.get("MCP_URL", "http://localhost:8000/mcp")

class SimAssistantAgent:
    def __init__(self):
        # Initialise the LLM once
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY environment value is not set.")
        
        self.llm = ChatModel.from_name("openai:gpt-4o-mini")
        self.tools: List[AnyTool] = []
        
        self.system_prompt = (
            "You are a Mobile SIM activation assistant working in an Australian Telco.\n"
            "Follow instructions precisely: respond only to SIM/Mobile activation/deactivation.\n"
            "1) If no mobile number provided, ask: 'What is your mobile number?'\n"
            "2) Mobile number must be in Australian format (e.g. 04 or +61). If not, stop.\n"
            "3) Check SIM status using tools:\n"
            "   - If 'active': reply exactly 'your sim is already active'.\n"
            "   - If 'inactive': you MUST call set_number_status with new_status 'active'. "
            "Only after that tool returns status 'active', reply 'Your SIM was activated.' "
            "Never say the SIM was activated without calling set_number_status.\n"
            "   - If 'not_found': reply exactly 'Mobile number not found'.\n"
            "If 'error' is in tool response, stop and report it.\n"
            "Only use the responses specified. You have access to tools. Do not output MCP instructions."
        )

    async def invoke(self, user_text: str) -> str:
        async with httpx.AsyncClient(headers={"x-api-key": "123"}) as http_client:
            async with streamable_http_client(
                url=MCP_URL,
                http_client=http_client,
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    # The tools are bound to this MCP session, which is closed
                    # at the end of the call, so reload them on every request.
                    mcp_tools = await MCPTool.from_client(client=session)
                    self.tools = [
                        t for t in mcp_tools
                        if t.name in ["get_number_status", "set_number_status"]
                    ]

                    # Fresh memory for every request: a memory shared by all
                    # requests made the model stop calling the tools.
                    memory = TokenMemory(self.llm)
                    await memory.add(SystemMessage(self.system_prompt))
                    agent = ReActAgent(
                        llm=self.llm, tools=self.tools, memory=memory
                    )

                    run_output = await agent.run(user_text)

                    # Return the last message text from history
                    return run_output.output[-1].text


class SimAssistantExecutor(AgentExecutor):
    def __init__(self):
        self.agent = SimAssistantAgent()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_text = context.get_user_input()
        result = await self.agent.invoke(user_text)
        message = Message(
            role=Role.ROLE_AGENT,
            parts=[Part(text=result)],
            message_id=uuid4().hex,
        )
        await event_queue.enqueue_event(message)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        print("Cancellation requested but not supported.")
