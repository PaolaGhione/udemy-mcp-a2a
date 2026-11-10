import httpx
import uvicorn
from fastapi import FastAPI

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.routes.fastapi_routes import add_a2a_routes_to_fastapi
from a2a.server.tasks import (
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore,
)
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

from PushExecutor import PushExecutor

if __name__ == "__main__":
    agent_skill = AgentSkill(
        id="push_skill",
        name="Push Notification Skill",
        description="I demonstrate push notifications",
        tags=["SES", "Task", "Push"],
    )

    agent_capability = AgentCapabilities(
        streaming=True,
        push_notifications=True,
    )

    agent_card = AgentCard(
        name="Push Notification Demo Server",
        description="",
        version="1.0",
        supported_interfaces=[
            AgentInterface(
                url="http://localhost:9999",
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            )
        ],
        skills=[agent_skill],
        capabilities=agent_capability,
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
    )

    httpx_client = httpx.AsyncClient()
    push_config_store = InMemoryPushNotificationConfigStore()
    push_sender = BasePushNotificationSender(
        httpx_client=httpx_client,
        config_store=push_config_store,
    )

    request_handler = DefaultRequestHandler(
        agent_executor=PushExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
        push_config_store=push_config_store,
        push_sender=push_sender,
    )

    app = FastAPI()
    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(agent_card),
        jsonrpc_routes=create_jsonrpc_routes(request_handler, rpc_url="/"),
    )

    uvicorn.run(app, host="0.0.0.0", port=9999)
