from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from openai import AsyncOpenAI

mcp = FastMCP(name="Direct LLM Example")

# Reads OPENAI_API_KEY from the OS environment variables
# (Windows system variables)
llm_client = AsyncOpenAI()


@mcp.tool()
async def generate_poem(topic: str) -> str:
    response = await llm_client.chat.completions.create(
        model="gpt-4o",
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": f"Write a poem of exactly 4 lines about {topic}",
        }],
    )
    choice = response.choices[0]
    if choice.finish_reason == "length":
        raise ToolError("Poem truncated: token limit reached")
    return choice.message.content


if __name__ == "__main__":
    mcp.run(transport='streamable-http')
