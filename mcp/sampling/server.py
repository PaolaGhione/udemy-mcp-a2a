from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from mcp.types import SamplingMessage, TextContent

mcp = FastMCP(name="Sampling Example")


@mcp.tool()
async def generate_poem(topic: str, ctx: Context) -> str:
    prompt = f"Write a poem of exactly 4 lines about {topic}"

    result = await ctx.session.create_message(
        messages=[
            SamplingMessage(
                role="user",
                content=TextContent(type="text", text=prompt),
            )
        ],
        max_tokens=200,
    )

    if result.stopReason == "maxTokens":
        raise ToolError("Poem truncated: token limit reached")
    if result.content.type == "text":
        return result.content.text
    return str(result.content)


if __name__ == "__main__":
    mcp.run(transport='streamable-http')
