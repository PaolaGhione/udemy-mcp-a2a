import asyncio
from uuid import uuid4

import httpx

from a2a.client import ClientConfig, ClientFactory
from a2a.client.card_resolver import A2ACardResolver
from a2a.types import Message, Part, Role, SendMessageRequest


async def main():
    server_url = "http://localhost:9999"

    async with httpx.AsyncClient() as httpx_client:
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=server_url,
            agent_card_path="/.well-known/agent-card.json",
        )

        agent_card = await resolver.get_agent_card()

        config = ClientConfig(httpx_client=httpx_client)
        factory = ClientFactory(config=config)
        client = factory.create(card=agent_card)

        request = SendMessageRequest(
            message=Message(
                role=Role.ROLE_USER,
                parts=[Part(text="Hello, Agent.")],
                message_id=uuid4().hex,
            )
        )

        async for event in client.send_message(request):
            print(event)


if __name__ == "__main__":
    asyncio.run(main())
