import asyncio
from openai import AsyncOpenAI
from mcp import ClientSession, types
from mcp.client.streamable_http import streamable_http_client
from mcp.types import TextContent
from mcp.shared.context import RequestContext

# Reads OPENAI_API_KEY from the OS environment variables
# (Windows system variables)
llm_client = AsyncOpenAI()


async def sampling_handler(
    context: RequestContext,
    params: types.CreateMessageRequestParams,
) -> types.CreateMessageResult:
    prompt_text = params.messages[0].content.text

    # Call LLM
    response = await llm_client.chat.completions.create(
        model="gpt-4o",
        max_tokens=params.maxTokens,
        messages=[{"role": "user", "content": prompt_text}]
    )
    choice = response.choices[0]
    llm_output = choice.message.content
    truncated = choice.finish_reason == "length"
    stop_reason = "maxTokens" if truncated else "endTurn"

    return types.CreateMessageResult(
        role="assistant",
        content=TextContent(type="text", text=llm_output),
        model="gpt-4o",
        stopReason=stop_reason,
    )


async def main():
    server_url = "http://localhost:8000/mcp"
    topic = input("Enter a topic for a poem:")
    async with streamable_http_client(server_url) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(
            read_stream,
            write_stream,
            sampling_callback=sampling_handler,
        ) as session:
            await session.initialize()
            tool_result = await session.call_tool(
                name="generate_poem",
                arguments={"topic": topic},
            )
            print(tool_result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
