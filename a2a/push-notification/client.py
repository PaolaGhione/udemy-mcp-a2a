import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from google.protobuf.json_format import MessageToDict, ParseDict

from a2a.client import ClientConfig, ClientFactory
from a2a.client.card_resolver import A2ACardResolver
from a2a.types import (
    AuthenticationInfo,
    Message,
    Part,
    Role,
    SendMessageConfiguration,
    SendMessageRequest,
    StreamResponse,
    TaskPushNotificationConfig,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Start the agent request once the webhook server is up
    task = asyncio.create_task(initiate_agent_request())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)

SERVER_URL = "http://localhost:9999"
CALLBACK_URL = "http://localhost:8000/notifications"
API_KEY = "YOUR API KEY"


@app.post("/notifications")
async def handle_push_notification(
    request: Request,
    x_a2a_notification_token: str | None = Header(None),
):
    # Debug: uncomment to print the headers sent by the server
    # (they include the token)
    # print("HEADERS:", dict(request.headers))

    # The server sends the config's `token` in the
    # X-A2A-Notification-Token header
    if x_a2a_notification_token != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorised")

    payload = await request.json()
    event = ParseDict(payload, StreamResponse())
    kind = event.WhichOneof("payload")

    if kind == "task":
        print(f"Task: {event.task.id} - {event.task.status.state}")

    elif kind == "status_update":
        info = MessageToDict(event.status_update.metadata).get("info")
        state = event.status_update.status.state
        print(f"Status: {state} - {info}")

    elif kind == "artifact_update":
        print(f"Artifact Received: {event.artifact_update.artifact.name}")

    return {"status": "ok"}


async def initiate_agent_request():
    await asyncio.sleep(2)

    async with httpx.AsyncClient() as httpx_client:
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=SERVER_URL,
            agent_card_path="/.well-known/agent-card.json",
        )

        agent_card = await resolver.get_agent_card()
        config = ClientConfig(httpx_client=httpx_client)
        factory = ClientFactory(config=config)
        client = factory.create(card=agent_card)

        notification_cfg = TaskPushNotificationConfig(
            url=CALLBACK_URL,
            token=API_KEY,
            authentication=AuthenticationInfo(
                scheme="Bearer",
                credentials=API_KEY,
            ),
        )

        request = SendMessageRequest(
            message=Message(
                role=Role.ROLE_USER,
                parts=[Part(text="Execute long task with push.")],
                message_id=uuid4().hex,
            ),
            # Signals the server to use Push Notifications
            configuration=SendMessageConfiguration(
                task_push_notification_config=notification_cfg,
            ),
        )

        async for response_event in client.send_message(request):
            # You still stream events here while the server
            # also sends them to your /notifications endpoint
            kind = response_event.WhichOneof("payload")
            print(f"Streamed: {kind}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
