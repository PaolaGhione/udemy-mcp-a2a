import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.routes.fastapi_routes import add_a2a_routes_to_fastapi
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

from SimAssistantExecutor import SimAssistantExecutor

if __name__ == "__main__":

    agent_skill = AgentSkill(
        id="sim_activation_skill",
        name="SIM Activation",
        description="Activate or deactivate SIM cards",
        tags=["SIM", "Activation", "Telco"]
    )

    agent_capabilities = AgentCapabilities(
        streaming=False
    )

    agent_card = AgentCard(
        name="SimAssistant",
        description="Activate Australian SIMs using MCP-backed tools",
        version="1.0",
        supported_interfaces=[
            AgentInterface(
                url="http://localhost:9000",
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            )
        ],
        default_input_modes=["text"],
        default_output_modes=["text"],
        skills=[agent_skill],
        capabilities=agent_capabilities
    )

    request_handler = DefaultRequestHandler(
        agent_executor=SimAssistantExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card
    )

    server = FastAPI()
    add_a2a_routes_to_fastapi(
        server,
        agent_card_routes=create_agent_card_routes(agent_card),
        # chat.html still sends the old A2A 0.3 format ("message/send"),
        # so we keep the 0.3 compatibility layer enabled.
        jsonrpc_routes=create_jsonrpc_routes(
            request_handler, rpc_url="/", enable_v0_3_compat=True
        ),
    )

    server.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8080"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    uvicorn.run(
        server,
        host="0.0.0.0",
        port=9000
    )
