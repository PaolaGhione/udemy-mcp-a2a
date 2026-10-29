# MCP con autenticazione Auth0 (Client Credentials)

Server FastMCP che valida un JWT emesso da Auth0, e client che ottiene il token e chiama il tool `Greetings`.

Il codice del corso è stato adattato a **fastmcp 3.4.2** e a una versione più recente di **authlib**.

## Avvio

Server, in un terminale:

```powershell
python .\server.py
```

Client, in un altro terminale, con le credenziali dell'applicazione M2M di Auth0:

```powershell
$env:CLIENT_ID="..."
$env:CLIENT_SECRET="..."
python .\http-client.py
```

In PowerShell `set CLIENT_ID=...` non crea una variabile d'ambiente (è un alias di `Set-Variable`): serve `$env:`. `set` funziona solo in cmd.

Prima di usare il codice, sostituisci in `server.py` e `http-client.py` i valori del tenant (`OAUTH_ISSUER`, `JWKS_URI`, `AUDIENCE`, `token_endpoint`, `audience`) con i tuoi.

## Differenze rispetto al corso

| Dove | Corso | Versione attuale |
|---|---|---|
| `server.py`, costruttore | `FastMCP(stateless_http=True)` | `FastMCP()` |
| `server.py`, avvio | `run_streamable_http_async()` | `run_http_async(stateless_http=True)` |
| `server.py`, header | `get_http_headers()` | `get_http_headers(include_all=True)`: di default l'header `authorization` viene rimosso |
| `server.py`, lettura header | `headers.get("Authorization")` | `headers.get("authorization")`: i nomi degli header sono in minuscolo |
| `server.py`, validazione | `claims.validate(iss=..., aud=...)` | `iss` e `aud` in `claims_options` di `decode()`, poi `claims.validate()` senza argomenti |

## Controllo del token (debugger JWT)

Un JWT ha tre parti separate da punti: header, payload (i claim) e firma.

| Parte | Campo | Valore atteso | Perché |
|---|---|---|---|
| Header | `alg` | `RS256` | È l'unico algoritmo accettato dal server |
| Header | `kid` | uguale a `Kid:` nel log del server | Serve per scegliere la chiave pubblica nel JWKS |
| Payload | `iss` | URL del tenant, con slash finale | Deve combaciare con `OAUTH_ISSUER` |
| Payload | `aud` | `https://<tenant>/api/v2/` | Deve combaciare con `AUDIENCE` |
| Payload | `exp` | data futura | Dopo questa data il token è scaduto |
| Payload | `gty` | `client-credentials` | Conferma il tipo di flusso |
| Payload | `sub` | finisce in `@clients` | È lo stesso valore di `User Id:` nel log |

Il token del client può avere molti permessi sul tenant: non incollarlo su siti esterni. Per leggere il payload in locale, senza verificare la firma:

```powershell
$token = "incolla_qui_il_token"
$payload = $token.Split(".")[1]
python -c "import base64,json,sys; p=sys.argv[1]; p+='='*(-len(p)%4); print(json.dumps(json.loads(base64.urlsafe_b64decode(p)), indent=2))" $payload
```

## Test dell'autenticazione

Server in un terminale, client in un altro. Dopo ogni modifica al server: CTRL+C e rilancio.

| # | Test | Come | Atteso |
|---|---|---|---|
| 1 | Caso positivo | `python .\http-client.py` | Client: `Available tools: ['Greetings']` e il saluto. Server: richieste `200`, `202`, `200`, `200`, poi `User Id:`, `Kid:`, `Claims:` |
| 2 | Credenziali sbagliate | `CLIENT_SECRET` errato | Il client fallisce prima di arrivare al server (Auth0 rifiuta la richiesta del token) |
| 3 | Nessun token | Togli `auth=BearerAuth(token=token)` nel client | Server: `No valid Authorization header found` |
| 4 | Token manomesso | `BearerAuth(token=token[:-4] + "abcd")` | Server: `Token validation failed: ...` (firma non valida) |
| 5 | Audience diversa | Cambia `AUDIENCE` nel server e riavvia | Server: `Token validation failed: ...` con errore sul claim `aud` |
| 6 | Token scaduto | Difficile da provare: il client ne chiede uno nuovo a ogni esecuzione | Il controllo su `exp` lo fa `claims.validate()` |

Dopo ogni test negativo ripristina il codice e verifica con `git diff`.

## Limiti da ricordare

- **Il server non blocca le richieste non valide.** Nei test 3, 4 e 5 il tool risponde comunque con il saluto: i fallimenti si vedono solo nei log. Per bloccarle bisognerebbe sollevare un errore nei rami `else` ed `except`. Il corso non lo prevede.
- `http-client.py` stampa il token e il server stampa tutti i claim. Va bene in locale, ma non condividere quell'output.
- Non aggiornare fastmcp (il banner propone la 4.x) a metà corso: il codice potrebbe cambiare di nuovo.
