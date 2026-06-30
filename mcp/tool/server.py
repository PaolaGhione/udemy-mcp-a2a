# from fastmcp import FastMCP
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

mcp = FastMCP()


class Greeting(BaseModel):
    message: str


@mcp.tool("Greetings")
def greetings(name: str) -> Greeting:
    """A tool that accepts a name and returns a personalised greeting."""
    return Greeting(message=f"Hello, {name}")
