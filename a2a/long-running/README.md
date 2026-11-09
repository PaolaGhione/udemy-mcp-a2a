# Long-running A2A agent (task lifecycle and streaming)

An A2A (Agent2Agent) example of an agent that does slow work and reports its progress. Instead of answering with a single `Message`, the server creates a **task** and streams events while it runs: status changes (`SUBMITTED`, `WORKING`, `COMPLETED`) and partial results (artifacts).

Tested with `a2a-sdk` 1.1.0.

## Files

| File | Role |
|---|---|
| `LongRunningExecutor.py` | The agent logic: simulates slow work and publishes task events |
| `server.py` | Describes the agent (agent card) and serves it over HTTP on port 9999 |

There is no client in this folder. Any client that reads the stream works, for example `..\basic\client.py` (it prints every event it receives).

## Setup

```powershell
pip install "a2a-sdk[http-server,fastapi]" uvicorn httpx
```

## Running

Start the server in one terminal and the client in another:

```powershell
python .\server.py
python ..\basic\client.py
```

The events arrive one at a time over about 6 seconds, not all at once. Expected sequence:

| # | Event | State |
|---|---|---|
| 1 | `task` | `TASK_STATE_SUBMITTED` |
| 2 | `status_update` | `TASK_STATE_WORKING` (`info: "Working..."`) |
| 3 | `artifact_update` | text `This is part of the result for: Hello, Agent.` |
| 4-7 | steps 2 and 3 repeated | two more times |
| 8 | `status_update` | `TASK_STATE_COMPLETED` (`info: "Completed..."`) |

After any change to the server: CTRL+C and restart.

## How it works

### LongRunningExecutor.py

`execute(context, event_queue)` does the following:

1. Reads the user text from `context.message.parts[0].text`. It is echoed back in the text of each artifact.
2. Enqueues a `Task` in state `SUBMITTED`. This must be the first event of a new task (see Notes). `context.task_id` and `context.context_id` are filled in by the server.
3. Repeats three times: enqueues a `TaskStatusUpdateEvent` with state `WORKING`, waits 2 seconds with `asyncio.sleep` (the "long" work), then enqueues a `TaskArtifactUpdateEvent` carrying an `Artifact` with one text `Part`.
4. Enqueues a `TaskStatusUpdateEvent` with state `COMPLETED`.

`metadata` is an optional free-form dictionary attached to an event. Here it carries a short `info` text. `cancel()` does nothing in this example.

### server.py

- `AgentCard` describes the agent: name, version, input and output modes, skills and where it can be reached (`AgentInterface` with URL and `JSONRPC` transport).
- `AgentCapabilities(streaming=True)` declares that the agent can send its answer as a stream of events. This is what makes the progress updates reach the client while the task is still running.
- `DefaultRequestHandler` links the HTTP layer to the executor. `InMemoryTaskStore` keeps tasks in memory, so they are lost on restart. Here a task is really created, unlike in the basic example.
- Two routes are mounted on a FastAPI app and served by uvicorn on port 9999:
  - `GET /.well-known/agent-card.json` returns the agent card.
  - `POST /` receives the messages as JSON-RPC.

## Notes

- Sending a `TaskStatusUpdateEvent` before any `Task` fails with `Agent should enqueue Task before TaskStatusUpdateEvent event` (JSON-RPC error `-32006`). That is why step 2 enqueues a `Task` instead of a status update.
- Because the task is created by the first event, the `COMPLETED` status update closes the stream: the client's `async for` loop ends after it.
- The server listens on `0.0.0.0`, so it is reachable from other machines on the network. Use `127.0.0.1` in `uvicorn.run` to keep it local.
