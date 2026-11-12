# MCP tool to get the status of a mobile number (in Australian format)
from fastmcp import FastMCP
from pydantic import BaseModel
import asyncio
import re
import sqlite3
import os

# Below classes are imported to add a middleware to starlett app
# so it intercepts http request and check x-api-key header.
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class Status(BaseModel):
    status: str = "not_found"
    number: str = ""


app = FastMCP(name="get-sim-status-mcp")



def normalize_number(number: str) -> str | None:
    """Returns the Australian mobile number in the 04xxxxxxxx form,
    or None if the number is not a valid Australian mobile number."""
    cleaned = re.sub(r"[\s-]", "", number)
    if cleaned.startswith("+61"):
        cleaned = "0" + cleaned[3:]
    return cleaned if re.fullmatch(r"04\d{8}", cleaned) else None


@app.tool(name="get_number_status", description="Gets a SIM card's (of a mobile number) status by SIM or mobile number. If the number is a valid Australian mobile number that does not exist yet, it is added as 'inactive'.")
async def get_number_status(number: str) -> Status:
    result = Status(number=number)

    normalized = normalize_number(number)
    if normalized is None:
        # Not an Australian mobile number: nothing is stored.
        return result
    result.number = normalized

    conn = sqlite3.connect("mcp-a2a.db", check_same_thread=False)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT status FROM numbers WHERE number = ?",
                       (normalized,))
        row = cursor.fetchone()
        if row:
            result.status = row[0]
        else:
            # New SIM: it is registered as inactive by default.
            cursor.execute(
                "INSERT INTO numbers (number, status) VALUES (?, 'inactive')",
                (normalized,))
            conn.commit()
            result.status = "inactive"
    except ValueError as e:
        result.status = str(e)
    cursor.close()
    conn.close()
    return result


@app.tool(name="set_number_status",
          description="Sets a SIM card's (of a mobile number) status by SIM or mobile number.")
async def set_number_status(number: str, new_status: str) -> Status:
    result = Status(number=number)

    normalized = normalize_number(number)
    if normalized is None:
        return result
    result.number = normalized

    print("set_number_status")
    conn = sqlite3.connect("mcp-a2a.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("UPDATE numbers set status=? WHERE number = ?", (new_status,
                                                                    normalized))
    conn.commit()

    if cursor.rowcount > 0:
        result.status = new_status
    else:
        result.status = "not_found"
    cursor.close()
    return result


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Read the body
        body = await request.body()
        if body:
            print(f"DEBUG MCP Body: {body.decode()}")

        # Re-wrap the request so the next handler can read the body again
        async def receive():
            return {"type": "http.request", "body": body}

        new_request = Request(request.scope, receive=receive)

        provided_key = request.headers.get("x-api-key")
        expected_key = os.environ.get("mcp_api_key", "123")

        if provided_key != expected_key:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        return await call_next(new_request)


async def main():
    import uvicorn

    starlette_app = app.http_app()
    starlette_app.add_middleware(APIKeyMiddleware)
    config = uvicorn.Config(
        starlette_app,
        host="0.0.0.0",
        port=8000
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
