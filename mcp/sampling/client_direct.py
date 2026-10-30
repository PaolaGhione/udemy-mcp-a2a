import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    server_url = "http://localhost:8000/mcp"
    topic = input("Enter a topic for a poem:")
    async with streamable_http_client(server_url) as (
        read_stream,
        write_stream,
        _,
    ):
        # No sampling_callback: the server calls the LLM provider itself
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tool_result = await session.call_tool(name="generate_poem",
                                                  arguments={"topic": topic})
            print(tool_result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
