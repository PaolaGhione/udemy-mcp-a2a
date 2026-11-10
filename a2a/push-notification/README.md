# Push notification A2A agent (webhook callbacks)

An A2A (Agent2Agent) example of an agent that does slow work and **pushes** its progress to the client. The client registers a webhook URL when it sends the message. While the task runs, the server calls that URL with every event (task created, status changes, partial results), so the client does not have to keep a connection open to hear about them.

The work is the same as in `..\long-running`. What changes is how the events reach the client.

Tested with `a2a-sdk` 1.1.0.

## Files

| File | Role |
|---|---|
| `PushExecutor.py` | The agent logic: simulates slow work and publishes task events |
| `server.py` | Describes the agent (agent card), enables push notifications and serves it over HTTP on port 9999 |
| `client.py` | Runs a webhook server on port 8000, sends a message asking for push notifications and also prints the streamed events |

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

The client starts its webhook server, waits 2 seconds and then sends the message. The events arrive one at a time over about 6 seconds. Expected client output:

```text
Task: <task id> - 1
Streamed: task
Status: 2 - Working...
Streamed: status_update
Artifact Received: Artifact
Streamed: artifact_update
Status: 2 - Working...
Streamed: status_update
Artifact Received: Artifact
Streamed: artifact_update
Status: 2 - Working...
Streamed: status_update
Artifact Received: Artifact
Streamed: artifact_update
Status: 3 - Completed...
Streamed: status_update
```

There are two sources of lines, and their relative order can vary:

- Lines starting with `Task:`, `Status:` or `Artifact Received:` come from the **webhook** (push).
- Lines starting with `Streamed:` come from the **stream** returned by `client.send_message()`.

The same event arrives both ways, which is on purpose: it shows push and streaming side by side. The state is printed as a number because it is a protobuf enum: `1` is `TASK_STATE_SUBMITTED`, `2` is `TASK_STATE_WORKING`, `3` is `TASK_STATE_COMPLETED`.

The client keeps running after the last event because the webhook server stays up. Stop it with CTRL+C. After any change to the server: CTRL+C and restart.

## How it works

### PushExecutor.py

`execute(context, event_queue)` is the same as in `..\long-running`:

1. Reads the user text from `context.message.parts[0].text`. It is echoed back in the text of each artifact.
2. Enqueues a `Task` in state `SUBMITTED`. This must be the first event of a new task (see Notes). `context.task_id` and `context.context_id` are filled in by the server.
3. Repeats three times: enqueues a `TaskStatusUpdateEvent` with state `WORKING`, waits 2 seconds with `asyncio.sleep` (the "long" work), then enqueues a `TaskArtifactUpdateEvent` carrying an `Artifact` with one text `Part`.
4. Enqueues a `TaskStatusUpdateEvent` with state `COMPLETED`.

The executor knows nothing about push notifications. It only publishes events. Sending them to the webhook is done by the server components described below. `cancel()` does nothing in this example.

### server.py

- `AgentCard` describes the agent: name, version, input and output modes (`text/plain`), skills and where it can be reached (`AgentInterface` with URL and `JSONRPC` transport).
- `AgentCapabilities(streaming=True, push_notifications=True)` declares that the agent can stream events and can call webhooks. The client can read this from the card.
- `InMemoryPushNotificationConfigStore` remembers the webhook registered for each task. It is in memory, so registrations are lost on restart, like the tasks in `InMemoryTaskStore`.
- `BasePushNotificationSender` is given the store and an `httpx.AsyncClient`. For every event of a task it looks up the registered webhooks and sends an HTTP `POST` to each one.
- `DefaultRequestHandler` links the HTTP layer to the executor. It receives the store and the sender through `push_config_store` and `push_sender`. Without them the webhook sent by the client would be ignored and nothing would be pushed.
- Two routes are mounted on a FastAPI app and served by uvicorn on port 9999:
  - `GET /.well-known/agent-card.json` returns the agent card.
  - `POST /` receives the messages as JSON-RPC.

### client.py

The client plays two roles in one process.

**Webhook receiver** (`POST /notifications`, port 8000):

- Checks the `X-A2A-Notification-Token` header against `API_KEY` and answers `401` if it does not match.
- Converts the JSON body into a `StreamResponse` with `ParseDict`. `WhichOneof("payload")` tells which kind of event it is: `task`, `status_update` or `artifact_update`.
- Prints one line per event. The `info` text of a status update is in `metadata`, read with `MessageToDict`.

**Caller** (`initiate_agent_request`):

- Waits 2 seconds so that the webhook server is ready, then uses `A2ACardResolver` and `ClientFactory` as in the other examples.
- Builds a `TaskPushNotificationConfig` with the callback `url` and a `token`. The `token` is what the server sends back in the `X-A2A-Notification-Token` header.
- Sends it inside `SendMessageRequest(configuration=SendMessageConfiguration(task_push_notification_config=...))`. This is how the client asks the server for push notifications.
- Reads the stream with `async for` and prints the type of each event.

The call is started from a FastAPI `lifespan` handler and is cancelled when the webhook server stops.

## Request flow

| Step | Who | What happens |
|---|---|---|
| 1 | Client | Starts the webhook server on port 8000 |
| 2 | Client | `GET /.well-known/agent-card.json`, then `POST /` with the message and the webhook config |
| 3 | `DefaultRequestHandler` | Saves the webhook config in the store, calls `executor.execute()` |
| 4 | Executor | Enqueues the `Task`, then status and artifact events, then `COMPLETED` |
| 5 | Server | Sends each event to the client's stream |
| 6 | `BasePushNotificationSender` | Also sends each event as `POST /notifications` with the token header |
| 7 | Client | Prints the pushed events (webhook) and the streamed ones (`async for`) |

## What the logs show

Server:

```text
GET /.well-known/agent-card.json HTTP/1.1  200 OK
POST / HTTP/1.1                            200 OK
```

Client (webhook server), one line for each pushed event:

```text
POST /notifications HTTP/1.1  200 OK
```

There are 8 pushed events: the task, three `WORKING` updates, three artifacts and `COMPLETED`.

## Notes

- Authentication uses the `token` field. The default sender in `a2a-sdk` 1.1.0 sends only the `X-A2A-Notification-Token` header with that value (checked by printing the headers received by the webhook: there is no `Authorization` header). The `authentication` field (`scheme`, `credentials`) is set in the example but is not used by the default sender.
- The `API_KEY` in `client.py` is a placeholder. Use a real secret outside of a demo.
- The webhook receives the same JSON the stream carries, with camelCase names, for example `{"statusUpdate": {"taskId": ..., "status": {"state": "TASK_STATE_WORKING"}, ...}}`. It is the JSON form of `StreamResponse`.
- Sending a `TaskStatusUpdateEvent` before any `Task` fails with `Agent should enqueue Task before TaskStatusUpdateEvent event`, so the executor starts with a `Task`.
- In a real use of push, the caller usually does not stay connected: it sends the message, gets the task back and waits for the webhook. Here the client also reads the stream only to show both mechanisms.
- If you see `address already in use` on startup, a previous run of the server (port 9999) or of the client (port 8000) is still alive. Stop it before starting again.
- Both programs listen on `0.0.0.0`, so they are reachable from other machines on the network. Use `127.0.0.1` in `uvicorn.run` to keep them local.
