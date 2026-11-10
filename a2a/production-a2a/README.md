# Production A2A agent (shared task store in Redis and tracing with Jaeger)

An A2A (Agent2Agent) example of the two things an agent needs when it runs in production, as several copies behind a load balancer:

- **A task store shared by all the copies.** The load balancer may send each request to a different copy, so tasks cannot live in the memory of one process. Here they are saved in **Redis** through a custom `RedisTaskStore`.
- **Distributed tracing.** Every request is recorded as a trace with OpenTelemetry and sent to **Jaeger**, a tool that shows how long each step took.

The agent itself is the same "Hello World" agent as in `..\basic`.

Tested with `a2a-sdk` 1.1.0.

## Files

| File | Role |
|---|---|
| `RedisTaskStore.py` | A `TaskStore` that saves, reads, lists and deletes tasks in Redis |
| `executor.py` | The agent logic: answers "Hello World" as a completed task |
| `server.py` | Describes the agent (agent card), sets up tracing, picks the task store and serves it over HTTP on port 9999 |
| `client.py` | Sends one message and prints what comes back |
| `docker.txt` | The command that starts Jaeger (bash syntax, see below for PowerShell) |

## Setup

```powershell
pip install "a2a-sdk[http-server,fastapi]" uvicorn httpx redis opentelemetry-sdk opentelemetry-exporter-otlp-proto-http
```

Redis and Jaeger are not Python packages. They are servers, and the easiest way to get them is Docker (Docker Desktop must be running). Both are free and need no account.

## Running

### 1. Start Redis and Jaeger

```powershell
docker run -d --rm --name redis-test -p 6379:6379 redis:7
docker run -d --rm --name jaeger -p 16686:16686 -p 4317:4317 -p 4318:4318 jaegertracing/jaeger
docker ps
docker exec redis-test redis-cli PING
```

`docker ps` must list both containers as `Up` and `PING` must answer `PONG`. `-d` runs them in the background and `--rm` removes them when they stop. Jaeger keeps its data in memory only.

The Jaeger command is the one in `docker.txt`, written on one line for PowerShell (the `\` line breaks of the file only work in bash).

### 2. Start the server

From this folder, in a terminal with the virtual environment active:

```powershell
$env:REDIS_URL = "redis://localhost:6379/0"
python .\server.py
```

If `REDIS_URL` is not set the server uses `InMemoryTaskStore` instead. Everything else works the same, but nothing is saved in Redis.

### 3. Send a message

In another terminal:

```powershell
python .\client.py
```

Expected output:

```text
task {
  id: "<task id>"
  context_id: "<context id>"
  status {
    state: TASK_STATE_COMPLETED
  }
  artifacts {
    artifact_id: "<artifact id>"
    name: "Result"
    parts {
      text: "Hello World"
    }
  }
}
```

The server log shows two requests, both `200 OK`: the `GET` of the agent card and the `POST /` with the message.

### 4. Check the task in Redis

```powershell
docker exec redis-test redis-cli KEYS "task:*"
docker exec redis-test redis-cli GET task:<task id>
```

`KEYS` lists one key `task:<task id>`. `GET` returns the same task as JSON, with `TASK_STATE_COMPLETED` and the `Hello World` artifact. The task is stored outside the Python process, which is what lets several copies of the agent share it.

### 5. Check the traces in Jaeger

Open `http://localhost:16686`, choose the service `a2a-helloworld-service` and press *Find Traces*. There are two traces:

| Trace | Spans | What it is |
|---|---|---|
| `A2A GET /.well-known/agent-card.json` | 1 | The client reading the agent card |
| `A2A POST /` | about 31 | The message. The first span is created by the middleware in `server.py`, the others by `a2a-sdk` itself |

The trace of the `POST` is marked with **1 error**. See Notes: it is harmless.

### 6. Stop everything

```powershell
# in the server terminal: CTRL+C, then
Remove-Item Env:REDIS_URL

docker stop redis-test jaeger
docker ps
```

`docker ps` must be empty. After any change to the server: CTRL+C and restart.

## How it works

### RedisTaskStore.py

`TaskStore` is the abstract class that `DefaultRequestHandler` uses to keep tasks. `a2a-sdk` ships an in-memory store and a SQL one (it needs SQLAlchemy), but no Redis one, so this class implements the interface:

- `save(task, context)`: writes the task under the key `task:<task id>`.
- `get(task_id, context)`: reads the key and rebuilds the task, or returns `None` if it does not exist.
- `delete(task_id, context)`: deletes the key.
- `list(params, context)`: returns the tasks, filtered by `context_id` and by status. It is a simple version for the demo, see Notes.

In `a2a-sdk` 1.x a `Task` is a **protobuf** message, not a Pydantic model. For that reason it is converted with `MessageToJson` and rebuilt with `Parse` (from `google.protobuf.json_format`). The value kept in Redis is readable JSON.

The client is `redis.asyncio`, created with `redis.from_url(url, decode_responses=True)`, so the code never blocks the server while it waits for Redis.

### executor.py

`execute(context, event_queue)` calls the agent, which returns `"Hello World"`, and enqueues a single `Task` that is already in state `COMPLETED` and has the text as an `Artifact`. `context.task_id` and `context.context_id` are filled in by the server. `cancel()` raises an exception because cancellation is not supported.

### server.py

- **Tracing setup.** `Resource` gives the service the name `a2a-helloworld-service`. `OTLPSpanExporter` sends the spans over HTTP to `http://host.docker.internal:4318/v1/traces`, where Jaeger listens. `BatchSpanProcessor` sends them in the background and `TracerProvider` is registered as the global one. Because it is global, `a2a-sdk` uses it too, which is where the many `a2a.server...` spans come from.
- **Middleware.** An HTTP middleware opens a span called `A2A <method> <path>` for every request and records the status code.
- **Agent card.** `AgentCard` describes the agent (name, version, input and output modes, skills, and an `AgentInterface` with URL and `JSONRPC` transport).
- **Task store.** If the environment variable `REDIS_URL` is set it uses `RedisTaskStore`, otherwise `InMemoryTaskStore`. The same code can then run on a laptop or in a container, with the setting coming from the environment.
- **Routes.** `DefaultRequestHandler` links the HTTP layer to the executor. Two routes are mounted on a FastAPI app and served by uvicorn on port 9999: `GET /.well-known/agent-card.json` returns the agent card and `POST /` receives the messages as JSON-RPC.

### client.py

Reads the agent card with `A2ACardResolver`, creates a client with `ClientFactory`, sends a `SendMessageRequest` with the text `Hello, Agent.` and prints every event it receives.

## Request flow

| Step | Who | What happens |
|---|---|---|
| 1 | Client | `GET /.well-known/agent-card.json` |
| 2 | Client | `POST /` with the message |
| 3 | Middleware | Opens the span `A2A POST /` |
| 4 | `DefaultRequestHandler` | Calls `executor.execute()` |
| 5 | Executor | Enqueues the completed `Task` |
| 6 | `DefaultRequestHandler` | Saves the task with `RedisTaskStore.save()` |
| 7 | Server | Returns the task to the client; the middleware closes the span and `BatchSpanProcessor` sends the spans to Jaeger |

## Notes

- **What changes from the course code.** The course is written for `a2a-sdk` 0.x. With 1.x: `Task` is protobuf (`MessageToJson` and `Parse` instead of `model_dump_json` and `model_validate_json`), its id is `task.id` (not `task_id`), `TaskStore` has a fourth abstract method `list`, the `context` argument is required, `A2AFastAPIApplication` is replaced by `FastAPI` plus `add_a2a_routes_to_fastapi`, and the agent card uses `supported_interfaces` instead of `url`.
- **The executor creates a task on purpose.** In the course the executor answers with a plain `Message`. A `Message` is never saved by the task store, so Redis would stay empty. Here the executor answers with a completed `Task` so that there is something to persist. In `a2a-sdk` 1.x the first event of a new task must be a `Task` (a status update before it fails).
- **The error in the `POST` trace is harmless.** It is a `QueueShutDown` exception on the span `EventQueueSource.dequeue_event`, recorded twice (once by the SDK's tracing wrapper and once by OpenTelemetry when the exception leaves the span). It is raised by `asyncio.Queue.get()` inside the SDK when its internal event queue is closed at the end of the task, and it happens after the response has been sent. The request ends with `200 OK` and the right result. Jaeger shows it in red only because the SDK records every exception as an error.
- **The Jaeger warnings `clock skew adjustment disabled`** on some spans only say that spans a fraction of a millisecond apart were not time-corrected. Ignore them.
- **`list` is a simple version.** It reads all the `task:*` keys, filters by `context_id` and status, sorts by id and returns the first page. It does not support page tokens. `InMemoryTaskStore` also separates tasks by user (owner); `RedisTaskStore` does not, so all users share the same keys. Add the owner to the key for a real multi-user service.
- **Tasks never expire.** `save` does not set a time to live, so tasks pile up in Redis. In production add an expiration or a clean-up.
- **The tracing endpoint** `host.docker.internal:4318` is the address of the host as seen from inside a container. It also resolves from Windows when Docker Desktop is installed. If the server log shows errors exporting spans, use `http://localhost:4318/v1/traces` instead. If Jaeger is not running the server still works, it only logs that it cannot export the spans.
- **Ports used:** 9999 (agent), 6379 (Redis), 16686 (Jaeger web page), 4318 (Jaeger receiving spans over HTTP). Port 4317 (gRPC) is published by the command but not used here. `address already in use` means a previous server or container is still running.
- The server listens on `0.0.0.0`, so it is reachable from other machines on the network. Use `127.0.0.1` in `uvicorn.run` to keep it local.
