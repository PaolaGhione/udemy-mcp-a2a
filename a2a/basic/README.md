# Basic A2A agent (Hello World)

A minimal A2A (Agent2Agent) example: a server that exposes an agent which always answers `Hello World`, and a client that discovers the agent, sends it a message and prints the reply.

Tested with `a2a-sdk` 1.1.0.

## Files

| File | Role |
|---|---|
| `executor.py` | The agent logic and its adapter to the A2A protocol |
| `server.py` | Describes the agent (agent card) and serves it over HTTP on port 9999 |
| `client.py` | Fetches the agent card, sends a message and prints the response |

## Setup

```powershell
pip install "a2a-sdk[http-server,fastapi]" uvicorn httpx
```

## Running

Start the server in one terminal and the client in another, from this folder:

```powershell
python .\server.py
python .\client.py
```

Expected client output:

```
message {
  message_id: "..."
  role: ROLE_AGENT
  parts {
    text: "Hello World"
  }
}
```

After any change to the server: CTRL+C and restart.

## How it works

### executor.py

- `HelloWorldAgent` is the agent itself. Its only method, `invoke()`, returns the string `Hello World`. In a real project this is where an LLM call or tools would go.
- `HelloWorldAgentExecutor` extends `AgentExecutor` and connects the agent to A2A:
  - `execute(context, event_queue)` is called by the server for every request. It calls the agent, wraps the result in a `Message` (role `ROLE_AGENT`, one text `Part`, a unique `message_id`) and puts it on the queue with `enqueue_event`.
  - `cancel()` is not supported here and raises an exception.
- The executor does not `return` the answer: it publishes events on the queue and the server reads them and sends them to the client. The queue expects event objects such as `Message`, not plain strings.

### server.py

- `AgentCard` describes the agent: name, version, input and output modes, skills and the address where it can be reached. `AgentInterface` declares the URL and the transport (`JSONRPC`).
- `AgentSkill` describes what the agent can do. `AgentCapabilities(streaming=False)` means the answer arrives in a single response, not in chunks.
- `DefaultRequestHandler` links the HTTP layer to the executor: it receives requests, prepares the event queue and calls `execute()`. `InMemoryTaskStore` keeps tasks in memory, so they are lost on restart. In this example the agent answers with a plain `Message` and no task is created.
- Two routes are mounted on a FastAPI app and served by uvicorn on port 9999:
  - `GET /.well-known/agent-card.json` returns the agent card.
  - `POST /` receives the messages as JSON-RPC.

### client.py

- `A2ACardResolver` downloads the agent card, so the client learns how to talk to the agent without being told.
- `ClientFactory` creates the client from the card, picking the matching transport.
- `SendMessageRequest` wraps a `Message` with role `ROLE_USER` and the text `Hello, Agent.`.
- `client.send_message()` is an async iterator, read with `async for`. Since streaming is off, a single event arrives: the agent's message.

## Request flow

| Step | Who | What happens |
|---|---|---|
| 1 | Client | `GET /.well-known/agent-card.json` |
| 2 | Server | Returns the agent card |
| 3 | Client | Builds the client from the card and sends `POST /` with the `SendMessageRequest` |
| 4 | `DefaultRequestHandler` | Prepares context and event queue, calls `executor.execute()` |
| 5 | Executor | Calls `HelloWorldAgent.invoke()` and gets `Hello World` |
| 6 | Executor | Builds the `Message` and enqueues it |
| 7 | `DefaultRequestHandler` | Reads the event from the queue and returns it as the HTTP response |
| 8 | Client | Receives the event in the `async for` loop and prints it |

## What the server log shows

```
GET /.well-known/agent-card.json HTTP/1.1  200 OK
POST / HTTP/1.1                            200 OK
```

One request for the card and one for the message, both `200`.

## Notes

- Opening `http://localhost:9999/` in a browser does not show a page: `POST /` is a protocol endpoint that expects JSON-RPC requests. The agent card is readable at `http://localhost:9999/.well-known/agent-card.json`.
- The server listens on `0.0.0.0`, so it is reachable from other machines on the network. Use `127.0.0.1` in `uvicorn.run` to keep it local.
- The `context` parameter of `execute()` and `cancel()` is unused here, but the `AgentExecutor` signature requires it.
