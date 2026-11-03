import uvicorn
from fastapi import FastAPI

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.routes.fastapi_routes import add_a2a_routes_to_fastapi
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

from executor import HelloWorldAgentExecutor

if __name__ == "__main__":
    agent_skill = AgentSkill(
        id="say_hello_skill",
        name="Hello Skill",
        description="I can say hello",
        tags=["Hello", "World"],
    )

    agent_capabiliy = AgentCapabilities(streaming=False)

    agent_card = AgentCard(
        name="Basic Server Agent (HelloWorld)",
        description="",
        version="1.0",
        supported_interfaces=[
            AgentInterface(
                url="http://localhost:9999",
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            )
        ],
        default_input_modes=["text"],
        default_output_modes=["text"],
        skills=[agent_skill],
        capabilities=agent_capabiliy,
    )

    request_handler = DefaultRequestHandler(
        agent_executor=HelloWorldAgentExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )

    app = FastAPI()
    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(agent_card),
        jsonrpc_routes=create_jsonrpc_routes(request_handler, rpc_url="/"),
    )

    uvicorn.run(app, host="0.0.0.0", port=9999)
