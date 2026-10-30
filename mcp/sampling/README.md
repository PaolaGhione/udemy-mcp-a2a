# MCP Sampling and the direct LLM alternative

This folder contains two versions of the same example: a `generate_poem` tool that writes a 4-line poem about a topic chosen by the user.

> **Sampling is deprecated.** As of protocol version `2026-07-28` (SEP-2577), the MCP specification advises against adopting it in new implementations and recommends that existing ones migrate to integrating directly with LLM provider APIs. It stays in the specification for at least 12 months after that revision's release, after which it may be removed. The `includeContext` values `"thisServer"` and `"allServers"` are deprecated as well (SEP-2596).
>
> Specification: <https://modelcontextprotocol.io/specification/draft/client/sampling>
>
> The draft also changes the mechanism: the server no longer sends a standalone `sampling/createMessage` request. It wraps the request in an `InputRequiredResult`, and the client retries the call with `inputResponses`. This example uses the classic model with `sampling_callback`, which works with fastmcp 3.4.2.

## The two versions

| | Sampling | Direct call |
|---|---|---|
| Files | `server.py` + `client.py` | `server_direct.py` + `client_direct.py` |
| Who calls OpenAI | the client, through `sampling_callback` | the server |
| Where `OPENAI_API_KEY` is needed | on the client | on the server |
| Status in the specification | deprecated | recommended approach |

In the sampling version the server has no key: it asks the client to generate the text with `ctx.session.create_message`. In the direct version the tool calls OpenAI itself and the client has no LLM.

## OpenAI key

The code uses `AsyncOpenAI()` with no arguments: the SDK reads `OPENAI_API_KEY` from the operating system environment variables (on Windows, the system or user variables). No `.env` file is needed.

A variable set after VS Code or the terminal was opened is not visible to processes that are already running: reopen the editor or the terminal.

## Running

Both versions use the same port (8000): run one at a time and stop it with CTRL+C before starting the other.

Sampling version:

```powershell
python .\mcp\sampling\server.py
python .\mcp\sampling\client.py
```

Direct version:

```powershell
python .\mcp\sampling\server_direct.py
python .\mcp\sampling\client_direct.py
```

Start the server in one terminal and the client in another. After any change to the server: CTRL+C and restart.

## Token limit and truncated responses

- `maxTokens` is required in the sampling request and the client **must** respect it: `client.py` passes it to OpenAI with `max_tokens=params.maxTokens`.
- Tokens are not characters: 100 tokens are roughly 75 English words, and the model stops when it runs out, even mid-sentence.
- The prompt asks for exactly 4 lines and `max_tokens` is 200, to leave some margin.
- If the response is truncated anyway (`finish_reason == "length"` in OpenAI), `client.py` returns `stopReason="maxTokens"` and `server.py` raises a `ToolError`. In the direct version `server_direct.py` checks `finish_reason` and raises the same error. To try it, lower `max_tokens` to 10.

## What the server log shows

| Version | Requests | Meaning |
|---|---|---|
| Sampling | `POST` 200, `GET` 200, `POST` 202, `POST` 200, `POST` 202, `POST` 200, `DELETE` 200 | The second `202` is the client's reply to the server with the sampling result |
| Direct | `POST` 200, `GET` 200, `POST` 202, `POST` 200, `POST` 200, `DELETE` 200 | A single `202`, the `initialized` notification: the server answers without asking the client for anything |

Opening `http://127.0.0.1:8000/mcp` in a browser returns an error (`406 Not Acceptable`): `/mcp` is not a web page but a protocol endpoint that expects JSON-RPC requests.

## Notes

- The code is tested with fastmcp 3.4.2. The banner suggests 4.x: upgrading may require further changes.
- The `context` parameter of `sampling_handler` is unused, but the MCP callback signature requires it.
