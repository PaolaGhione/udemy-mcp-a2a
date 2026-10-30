# MCP with Auth0 authentication (Client Credentials)

A FastMCP server that validates a JWT issued by Auth0, and a client that obtains the token and calls the `Greetings` tool.

The code is compatible with **fastmcp 3.4.2** and a recent version of **authlib**.

## Running

Server, in one terminal:

```powershell
python .\server.py
```

Client, in another terminal, with the credentials of the Auth0 M2M application:

```powershell
$env:CLIENT_ID="..."
$env:CLIENT_SECRET="..."
python .\http-client.py
```

In PowerShell `set CLIENT_ID=...` does not create an environment variable (it is an alias of `Set-Variable`): you need `$env:`. `set` only works in cmd.

Before using the code, replace the tenant values in `server.py` and `http-client.py` (`OAUTH_ISSUER`, `JWKS_URI`, `AUDIENCE`, `token_endpoint`, `audience`) with your own.

## Differences from earlier library versions

| Where | Earlier version | Current version |
|---|---|---|
| `server.py`, constructor | `FastMCP(stateless_http=True)` | `FastMCP()` |
| `server.py`, startup | `run_streamable_http_async()` | `run_http_async(stateless_http=True)` |
| `server.py`, headers | `get_http_headers()` | `get_http_headers(include_all=True)`: by default the `authorization` header is stripped |
| `server.py`, reading headers | `headers.get("Authorization")` | `headers.get("authorization")`: header names are lowercase |
| `server.py`, validation | `claims.validate(iss=..., aud=...)` | `iss` and `aud` go in `claims_options` of `decode()`, then `claims.validate()` with no arguments |

## Checking the token (JWT debugger)

A JWT has three dot-separated parts: header, payload (the claims) and signature.

| Part | Field | Expected value | Why |
|---|---|---|---|
| Header | `alg` | `RS256` | It is the only algorithm the server accepts |
| Header | `kid` | same as `Kid:` in the server log | Used to pick the public key in the JWKS |
| Payload | `iss` | tenant URL, with trailing slash | Must match `OAUTH_ISSUER` |
| Payload | `aud` | `https://<tenant>/api/v2/` | Must match `AUDIENCE` |
| Payload | `exp` | a future date | After this date the token has expired |
| Payload | `gty` | `client-credentials` | Confirms the flow type |
| Payload | `sub` | ends with `@clients` | Same value as `User Id:` in the log |

The client's token may carry many permissions on the tenant: do not paste it into external sites. To read the payload locally, without verifying the signature:

```powershell
$token = "paste_the_token_here"
$payload = $token.Split(".")[1]
python -c "import base64,json,sys; p=sys.argv[1]; p+='='*(-len(p)%4); print(json.dumps(json.loads(base64.urlsafe_b64decode(p)), indent=2))" $payload
```

## Authentication tests

Server in one terminal, client in another. After every change to the server: CTRL+C and restart.

| # | Test | How | Expected |
|---|---|---|---|
| 1 | Happy path | `python .\http-client.py` | Client: `Available tools: ['Greetings']` and the greeting. Server: `200`, `202`, `200`, `200` requests, then `User Id:`, `Kid:`, `Claims:` |
| 2 | Wrong credentials | wrong `CLIENT_SECRET` | The client fails before reaching the server (Auth0 rejects the token request) |
| 3 | No token | Remove `auth=BearerAuth(token=token)` in the client | Server: `No valid Authorization header found` |
| 4 | Tampered token | `BearerAuth(token=token[:-4] + "abcd")` | Server: `Token validation failed: ...` (invalid signature) |
| 5 | Different audience | Change `AUDIENCE` in the server and restart | Server: `Token validation failed: ...` with an error on the `aud` claim |
| 6 | Expired token | Hard to test: the client requests a new token on every run | The `exp` check is done by `claims.validate()` |

After each negative test restore the code and verify with `git diff`.

## Things to keep in mind

- **The server does not block invalid requests.** In tests 3, 4 and 5 the tool still replies with the greeting: failures only show up in the logs. To block them, the `else` and `except` branches would need to raise an error.
- `http-client.py` prints the token and the server prints all the claims. That is fine locally, but do not share that output.
- The code is tested with fastmcp 3.4.2. Upgrading to 4.x (the banner suggests it) may require further changes.
