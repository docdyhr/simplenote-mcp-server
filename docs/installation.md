# Installation

This page covers installing the Simplenote MCP Server, connecting it to an MCP
client such as Claude Desktop or Claude Code, and upgrading or removing it.

## Choose an install method

| Method | Use it when | Transport |
| --- | --- | --- |
| [Python package](#install-the-python-package) (pipx, uv or pip) | The client runs on the same Mac or Linux machine. This is the simplest setup for Claude Desktop and Claude Code. | stdio |
| [Docker](#docker) | You want the server in a container, started by the client or running as a service. Also the way to run it on Windows. | stdio or HTTP |
| [Kubernetes (Helm)](#kubernetes-helm) | You run it as a service in a cluster. | HTTP |
| [From source](#install-from-source) | You're changing the code. | stdio |

With stdio, the client starts the server as a child process and talks to it
over stdin and stdout. With HTTP, the server runs on its own and clients
connect to it at `http://<host>:8000/mcp`.

## Requirements

- A Simplenote account.
- For the Python package: macOS or Linux, and Python 3.10 or newer. The
  package doesn't start on native Windows, where Python has no `os.getuid()`,
  which the server calls at startup. On Windows, use the Docker image, or
  install the package inside WSL. On macOS, the `/usr/bin/python3` from
  Apple's command line tools is 3.9, which is too old. pipx and uv find or
  install a newer Python, and Homebrew's `python3` is new enough.
- For the Docker image: Docker on `linux/amd64` or `linux/arm64`. Docker
  Desktop on macOS and Windows runs it.

## Before you start: credentials and write mode

### Signing in

The server reads its settings only from environment variables. It doesn't
load a `.env` file itself. `SIMPLENOTE_EMAIL` and `SIMPLENOTE_PASSWORD` must
both be set, or the server stops at startup with:

```text
SIMPLENOTE_EMAIL (or SIMPLENOTE_USERNAME) and SIMPLENOTE_PASSWORD environment variables must be set
```

To call Simplenote's API, the server needs a token. It uses the first one it
finds:

1. `SIMPLENOTE_TOKEN`, if you set it.
2. The token it cached at an earlier start, in
   `~/.config/simplenote-mcp/<email>.token`, with the `@` in the email written
   as `_at_`.
3. On macOS, the token of the signed-in Simplenote desktop app, read from your
   login keychain. macOS asks once whether to allow this. Answer within 5
   seconds, or the server moves on to step 4 for that start. If that's too
   short, run the `security` command below once in Terminal and choose
   **Always Allow**: the server runs the same command.
4. A sign-in with your email and password.

The password is required even when the token comes from steps 1–3. A token
from step 3 or 4 is written to the cache file from step 2, in plain text,
readable only by you (mode 0600). The server keeps using a cached token even
after Simplenote rejects it, so you have to delete the file yourself (see
[Troubleshooting](#troubleshooting)).

A container can't reach your keychain, and its token cache lives inside the
container, so a new container signs in with your password. With Compose, whose
home directory is a temporary mount, so does every restart. Password sign-in
goes to Simplenote's `auth.simperium.com`, which has been unreachable for long
stretches before (see version 1.17.1 in the
[changelog](https://github.com/docdyhr/simplenote-mcp-server/blob/main/CHANGELOG.md)).
If sign-in fails, set `SIMPLENOTE_TOKEN` (for Compose and Helm, see their
sections below). On a Mac where the Simplenote app is signed in, this prints
the app's token:

```bash
security find-generic-password -s chalk-bump-f49 -a you@example.com -w
```

Treat the token like your password.

### Write mode

By default the server offers only tools that read, such as `search_notes`,
`get_note`, `list_tags` and `get_server_info`. Set `SIMPLENOTE_WRITE_MODE=true`
to add the tools that create, change and delete notes, such as `create_note`,
`update_note` and `delete_note`, and the irreversible `permanent_delete_note`
and `empty_trash`. Write mode also adds `publish_note`, which makes a note
readable by anyone with its URL. It caps writes at 20 per 60 seconds by
default (`SIMPLENOTE_WRITE_BUDGET`, `SIMPLENOTE_WRITE_BUDGET_WINDOW`).

## Install the Python package

The package is
[`simplenote-mcp-server` on PyPI](https://pypi.org/project/simplenote-mcp-server/).
It installs one command, `simplenote-mcp-server`. Use one of these installers.

With pipx, which installs the command in its own virtual environment:

```bash
pipx install simplenote-mcp-server
```

With uv, which does the same as a uv tool:

```bash
uv tool install simplenote-mcp-server
```

With pip, into a virtual environment you manage:

```bash
python3 -m venv ~/.venvs/simplenote-mcp
~/.venvs/simplenote-mcp/bin/pip install simplenote-mcp-server
```

If your shell then can't find `simplenote-mcp-server`, run `pipx ensurepath`
or `uv tool update-shell` and open a new terminal. The pip route doesn't put
the command on your `PATH`: it's `~/.venvs/simplenote-mcp/bin/simplenote-mcp-server`,
so use that full path wherever this page says `simplenote-mcp-server`.

With uv you can also skip the install: a client can start the server with
`uvx simplenote-mcp-server`, which fetches the package the first time.

### Check the install

The command has no `--version` or `--help` option: it ignores its arguments and
starts the server. To see the installed version, run `pipx list`,
`uv tool list` or `~/.venvs/simplenote-mcp/bin/pip show simplenote-mcp-server`.

To check that the server starts, run it in offline mode, which uses an empty
in-memory note store and never contacts Simplenote. With stdin closed, it exits
straight away:

```bash
SIMPLENOTE_OFFLINE_MODE=true simplenote-mcp-server < /dev/null
```

Its log, on stderr, includes the line `MCP server run completed normally`, and
it exits with status 0.

## Connect a client

The examples below turn on write mode. Leave out `SIMPLENOTE_WRITE_MODE` to
keep the server read-only.

### Claude Desktop

1. In Claude Desktop, open **Settings → Developer → Edit Config**. This opens
   `claude_desktop_config.json`:
    - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
    - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
2. Add the server under `mcpServers`:

    ```json
    {
      "mcpServers": {
        "simplenote": {
          "command": "simplenote-mcp-server",
          "env": {
            "SIMPLENOTE_EMAIL": "you@example.com",
            "SIMPLENOTE_PASSWORD": "your-password",
            "SIMPLENOTE_WRITE_MODE": "true"
          }
        }
      }
    }
    ```

    To run it through uv without installing it, set `"command": "uvx"` and
    `"args": ["simplenote-mcp-server"]`. On Windows, use the
    [Docker configuration](#let-the-client-start-the-container) instead.

3. Quit Claude Desktop completely, not just its window, and start it again.

Claude Desktop starts servers with a minimal `PATH` and doesn't expand `~`. If
it can't find the command, set `command` to its absolute path. On macOS,
`command -v simplenote-mcp-server` prints it; the same works for `uvx` and
`docker`.

The config file now holds your password in plain text, so keep it readable
only by you. To check the connection, ask Claude to run the `get_server_info`
tool, which returns the server's version. Claude Desktop writes the server's
stderr to `mcp-server-simplenote.log` in `~/Library/Logs/Claude/` (macOS) or
`%APPDATA%\Claude\logs\` (Windows).

### Claude Code

```bash
claude mcp add --env SIMPLENOTE_EMAIL=you@example.com \
  --env SIMPLENOTE_PASSWORD=your-password \
  --env SIMPLENOTE_WRITE_MODE=true \
  --transport stdio simplenote -- simplenote-mcp-server
```

Claude Code needs another option, such as `--transport stdio`, between the last
`--env` and the server name. Quote a value that contains characters your shell
treats specially.

This adds the server for you in the current project. Add `--scope user` to make
it available in all your projects. Either way, Claude Code saves the values,
password included, in plain text in `~/.claude.json`, and the command line
stays in your shell history. Don't use `--scope project` here: it writes the
entry to `.mcp.json`, which is meant to be committed. Check the connection with
`claude mcp get simplenote`, or with `/mcp` inside Claude Code.

### Other clients

Any MCP client that starts stdio servers can run the same command,
`simplenote-mcp-server` with no arguments, with the environment variables
above. For clients that connect over HTTP, see
[Run the server over HTTP](#run-the-server-over-http).

## Run the server over HTTP

With `MCP_TRANSPORT=http`, the server listens on `MCP_HTTP_HOST` and
`MCP_HTTP_PORT` (default `127.0.0.1:8000`) and serves MCP's Streamable HTTP
transport at `MCP_HTTP_PATH` (default `/mcp`). Other paths return 404.

- Bound to `127.0.0.1` or `localhost`, it needs no token, and it accepts only
  requests whose `Host` header names one of those (DNS-rebinding protection).
- Bound to any other address, such as `0.0.0.0` in a container, it won't start
  unless `MCP_HTTP_AUTH_TOKEN` is set, and DNS-rebinding protection is off.
  To turn it on, list in `MCP_HTTP_ALLOWED_HOSTS` each `Host` value exactly as
  clients send it: `name:port` for a non-default port (or `name:*` for any
  port), and the bare name for clients on port 80 or 443, such as those behind
  a reverse proxy. Any other `Host` gets 421. The list then replaces the
  loopback default as well.
- While the protection is on, a request with an `Origin` header that isn't
  listed in `MCP_HTTP_ALLOWED_ORIGINS` gets 403. Browser-based clients send
  one, so list the origin of the page they run on, for example
  `http://localhost:*` for any local port.

If a token is set, clients must send `Authorization: Bearer <token>`, and
requests without it get 401. Generate one with `openssl rand -hex 32`. A
shared token can't be revoked for one client and doesn't expire, so keep the
port on a private network, such as a VPN, Tailscale or an SSH tunnel, rather
than the open internet.

To add a running server to Claude Code:

```bash
claude mcp add --transport http simplenote-http http://127.0.0.1:8000/mcp \
  --header "Authorization: Bearer <token>"
```

## Docker

The image is published as
[`docdyhr/simplenote-mcp-server`](https://hub.docker.com/r/docdyhr/simplenote-mcp-server)
on Docker Hub and as
[`ghcr.io/docdyhr/simplenote-mcp-server`](https://github.com/docdyhr/simplenote-mcp-server/pkgs/container/simplenote-mcp-server)
on GitHub, for `linux/amd64` and `linux/arm64`. Both carry the same tags:

| Tag | What it is |
| --- | --- |
| `X.Y.Z`, `vX.Y.Z` | A [release](https://github.com/docdyhr/simplenote-mcp-server/releases). Pin one of these. |
| `latest`, `main` | The newest build of the `main` branch, not of a release. It's replaced as `main` moves on. |

The examples use `X.Y.Z`; replace it with a release number. The image runs the
server as user `mcp` (UID 1000) and uses stdio unless you set `MCP_TRANSPORT`.

### Let the client start the container

For Claude Desktop, or any stdio client, make Docker the command. First put
the variables in an env file, one `NAME=value` per line and without quotes
(Docker keeps quotes as part of the value):

```text
SIMPLENOTE_EMAIL=you@example.com
SIMPLENOTE_PASSWORD=your-password
SIMPLENOTE_WRITE_MODE=true
```

Keep the file outside any git repository and readable only by you
(`chmod 600`). Then give its absolute path in the client's config. On Windows,
write the path with forward slashes or doubled backslashes, as JSON requires.

```json
{
  "mcpServers": {
    "simplenote": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm", "--no-healthcheck",
        "--env-file", "/absolute/path/to/simplenote.env",
        "docdyhr/simplenote-mcp-server:X.Y.Z"
      ]
    }
  }
}
```

- Use `-i` without `-t`: stdio needs stdin kept open, not a terminal.
- `--rm` removes the container when the client stops the server.
- `--no-healthcheck` skips the image's health check, which queries a
  monitoring server that isn't running here. Without it, `docker ps` lists the
  container as unhealthy.

To keep the variables in the client's config instead of a file, pass each name
with `-e` and no value, and set the values under `"env"`. A `-e` without a value
passes that variable on from the environment the client gives Docker:

```json
{
  "mcpServers": {
    "simplenote": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm", "--no-healthcheck",
        "-e", "SIMPLENOTE_EMAIL", "-e", "SIMPLENOTE_PASSWORD", "-e", "SIMPLENOTE_WRITE_MODE",
        "docdyhr/simplenote-mcp-server:X.Y.Z"
      ],
      "env": {
        "SIMPLENOTE_EMAIL": "you@example.com",
        "SIMPLENOTE_PASSWORD": "your-password",
        "SIMPLENOTE_WRITE_MODE": "true"
      }
    }
  }
}
```

### Run it as a service

Add `MCP_HTTP_AUTH_TOKEN=<token>` to the env file, then:

```bash
docker run -d --name simplenote-mcp --restart unless-stopped \
  --env-file /absolute/path/to/simplenote.env \
  -e MCP_TRANSPORT=http -e MCP_HTTP_HOST=0.0.0.0 \
  -e ENABLE_HTTP_ENDPOINT=true \
  -p 127.0.0.1:8000:8000 \
  docdyhr/simplenote-mcp-server:X.Y.Z
```

Clients connect to `http://127.0.0.1:8000/mcp` with the token.

- Inside the container the server binds `0.0.0.0`, which isn't loopback, so it
  won't start without `MCP_HTTP_AUTH_TOKEN`.
- `-p 127.0.0.1:8000:8000` publishes the port on the host's loopback interface
  only. `-p 8000:8000` would publish it on every interface.
- `ENABLE_HTTP_ENDPOINT=true` starts the monitoring server that the image's
  health check queries, on port 8080 inside the container. Without it,
  `docker ps` reports the container as unhealthy.
- Without `MCP_TRANSPORT=http`, the server uses stdio, finds stdin closed and
  exits at once with status 0, and `--restart unless-stopped` starts it again,
  in a loop.

Read the logs with `docker logs simplenote-mcp`. Stop and remove the container
with `docker rm -f simplenote-mcp`.

[Vault encryption](security/encryption-design.md) needs
`SIMPLENOTE_VAULT_KEY_FILE` in a container: the image has no keychain backend,
so without it, encrypting fails with `No vault key is available`. Put the file
on persistent storage that UID 1000 can write, such as a named volume or a bind
mount (a PersistentVolumeClaim in Kubernetes), not under `/home/mcp` or `/tmp`,
which the Compose file and the chart mount as temporary storage. A key that's
lost with its container leaves the notes it encrypted unreadable.

### Docker Compose

The repository's
[`docker-compose.yml`](https://github.com/docdyhr/simplenote-mcp-server/blob/main/docker-compose.yml)
runs the same service with a read-only root filesystem, resource limits and the
health check turned on. Get a clone and work from its root:

```bash
git clone https://github.com/docdyhr/simplenote-mcp-server.git
cd simplenote-mcp-server
```

Create `.env` there (git ignores it) with your credentials and a token. Put a
value in single quotes if it contains `$`, `#` or a space: unquoted, Compose
expands `$` and drops everything from ` #` on.

```text
SIMPLENOTE_EMAIL=you@example.com
SIMPLENOTE_PASSWORD='your-password'
MCP_HTTP_AUTH_TOKEN=<token>
```

The file uses the `latest` tag, publishes port 8000 on every host interface,
and passes the container only the variables it lists, so neither
`SIMPLENOTE_WRITE_MODE` nor `SIMPLENOTE_TOKEN` reaches the server from `.env`
alone. To change any of that, don't edit the tracked file, which a later
`git pull` would have to merge. Put the changes in a
`docker-compose.override.yml` beside it instead. Compose reads that file
automatically, and git leaves it alone because it's untracked:

```yaml
services:
  simplenote-mcp:
    image: docdyhr/simplenote-mcp-server:X.Y.Z
    environment:
      - SIMPLENOTE_WRITE_MODE=true
      - SIMPLENOTE_TOKEN=${SIMPLENOTE_TOKEN}
    ports: !override
      - "127.0.0.1:8000:8000"
```

This pins a release, turns on write mode, passes `SIMPLENOTE_TOKEN` from
`.env` (leave that line out if you don't use a token), and publishes the port
on the host's loopback interface only. `!override` replaces the file's port
list instead of adding to it.

Compose mounts `./logs` at `/app/simplenote_mcp/logs`, and the container runs
as UID 1000, which must be able to write to it. Create the directory first. On
Linux, if your user isn't UID 1000, also run `sudo chown 1000:1000 logs`. Then
start the service and follow its log:

```bash
mkdir -p logs
docker compose up -d
docker compose logs -f
```

Without `MCP_HTTP_AUTH_TOKEN`, Compose stops with
`required variable MCP_HTTP_AUTH_TOKEN is missing a value`.

### Build the image yourself

From the root of a clone, run `docker build -t simplenote-mcp-server .`. The
build installs the pinned versions in `requirements-runtime-lock.txt`, which
target Python 3.13, the default `PYTHON_VERSION` build argument. A build with
`--build-arg PYTHON_VERSION=3.10` fails.

## Kubernetes (Helm)

The chart lives in the repository, at `helm/simplenote-mcp-server`, and isn't
published to a chart repository, so install it from a clone. Run these
commands from the clone's root, since the chart path is relative to it.

The chart runs the HTTP transport bound to `0.0.0.0`, so it needs a bearer
token as well as your credentials. Create a Secret, and tell the chart to use
it:

```bash
token=$(openssl rand -hex 32)
kubectl create secret generic simplenote-credentials \
  --from-literal=SIMPLENOTE_EMAIL=you@example.com \
  --from-literal=SIMPLENOTE_PASSWORD='your-password' \
  --from-literal=MCP_HTTP_AUTH_TOKEN="$token"

helm install simplenote-mcp-server ./helm/simplenote-mcp-server \
  --set externalSecrets.enabled=true
```

Clients need the token to connect. To read it back later:

```bash
kubectl get secret simplenote-credentials -o jsonpath='{.data.MCP_HTTP_AUTH_TOKEN}' | base64 -d
```

With `externalSecrets.enabled=true`, the chart creates no Secret of its own. It
reads the one named by `externalSecrets.target.name`, default
`simplenote-credentials`, which a secrets operator can also manage. Instead,
you can pass `--set simplenote.email=…`, `--set simplenote.password=…` and
`--set mcpHttp.authToken=…`. The chart then creates the Secret from those
values, and Helm keeps them in the release.

To turn on write mode, add
`--set-string configMap.data.SIMPLENOTE_WRITE_MODE=true`. Use `--set-string`
rather than `--set`, because ConfigMap values must be strings. The chart
doesn't read `SIMPLENOTE_TOKEN` from the Secret. If password sign-in fails in
the cluster, `--set-string configMap.data.SIMPLENOTE_TOKEN=<token>` passes a
token, but it sits in the ConfigMap in plain text.

To reach the service from your machine, forward the port, then connect to
`http://127.0.0.1:8000/mcp` with the token:

```bash
kubectl port-forward svc/simplenote-mcp-server 8000:8000
```

The service takes the release name when that name contains
`simplenote-mcp-server`, and `<release>-simplenote-mcp-server` otherwise.

The pod's root filesystem is read-only, so the chart mounts writable volumes at
`/tmp`, the log directory and the home directory, where the server writes at
startup. If you override `volumes` or `volumeMounts`, keep all three entries:
an override replaces the whole list. The chart's
[`values.yaml`](https://github.com/docdyhr/simplenote-mcp-server/blob/main/helm/simplenote-mcp-server/values.yaml)
lists its other settings, with comments.

## Install from source

For development:

```bash
git clone https://github.com/docdyhr/simplenote-mcp-server.git
cd simplenote-mcp-server
python3 -m venv .venv
.venv/bin/pip install -e ".[dev,test,all]"
.venv/bin/pre-commit install
make test-fast
```

To run your checkout from a client, set `command` to the absolute path of
`.venv/bin/simplenote-mcp-server` in the clone. Because the install is
editable, the client picks up your code changes the next time it starts the
server.

The lock files, `requirements-lock.txt` and `requirements-runtime-lock.txt`,
pin versions for Python 3.13, which CI and the Docker image use, and some pins
need Python 3.11 or newer. On Python 3.10 to 3.12, install from
`pyproject.toml` as above. The [contributing guide](contributing.md) covers
the rest of the workflow.

## Settings

The variables you're most likely to set. Only the credentials are required.

| Variable | Default | Effect |
| --- | --- | --- |
| `SIMPLENOTE_EMAIL` (or `SIMPLENOTE_USERNAME`) | – | Account email. Required. |
| `SIMPLENOTE_PASSWORD` | – | Account password. Required. |
| `SIMPLENOTE_TOKEN` | – | API token, used before any other token source. |
| `SIMPLENOTE_WRITE_MODE` | `false` | `true` adds the tools that create, change, publish and delete notes. |
| `SIMPLENOTE_WRITE_BUDGET` | `20` | Writes allowed per window. |
| `SIMPLENOTE_WRITE_BUDGET_WINDOW` | `60` | Length of that window, in seconds. |
| `SIMPLENOTE_OFFLINE_MODE` | `false` | `true` uses an empty in-memory store and never contacts Simplenote. For testing. |
| `CACHE_MAX_SIZE` | `10000` | Notes kept in memory. Above it, the least recently used notes are dropped, so set it to at least your note count. |
| `SYNC_INTERVAL_SECONDS` | `120` | How often the cache syncs with Simplenote. At least 10. |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` or `ERROR`. |
| `LOG_TO_FILE` | `true` | Also write log files (see [Troubleshooting](#troubleshooting)). |
| `MCP_TRANSPORT` | `stdio` | `stdio` or `http`. |
| `MCP_HTTP_HOST`, `MCP_HTTP_PORT`, `MCP_HTTP_PATH` | `127.0.0.1`, `8000`, `/mcp` | Where the HTTP transport listens. |
| `MCP_HTTP_AUTH_TOKEN` | – | Bearer token for the HTTP transport. Required when `MCP_HTTP_HOST` isn't loopback. |
| `MCP_HTTP_ALLOWED_HOSTS` | – | Comma-separated `Host` values to accept, exactly as clients send them: `name:port`, `name:*`, or a bare name for port 80 or 443. Turns on DNS-rebinding protection for a non-loopback bind, and replaces the loopback default. |
| `MCP_HTTP_ALLOWED_ORIGINS` | – | Comma-separated `Origin` values to accept while DNS-rebinding protection is on. Any other `Origin` gets 403. |
| `ENABLE_HTTP_ENDPOINT` | `false` | `true` starts the monitoring server (`/health`, `/ready`, `/metrics`). |
| `HTTP_HOST`, `HTTP_PORT` | `127.0.0.1`, `8080` | Where the monitoring server listens. |
| `HTTP_ENDPOINT_AUTH_TOKEN` | – | Bearer token for the monitoring server. Required when `HTTP_HOST` isn't loopback. |
| `SIMPLENOTE_VAULT_KEY_FILE` | – | Key file for [Vault encryption](security/encryption-design.md), created on first use, instead of the OS keychain. Use it where there's no keychain, as in a container. Keep it on persistent storage and back it up: notes encrypted with a lost key can't be decrypted. Encrypting and decrypting need write mode. |

## Upgrade

| Installed with | Upgrade with |
| --- | --- |
| pipx | `pipx upgrade simplenote-mcp-server` |
| uv | `uv tool upgrade simplenote-mcp-server`. With `uvx`, `uvx simplenote-mcp-server@latest` fetches the newest release. |
| pip | `~/.venvs/simplenote-mcp/bin/pip install --upgrade simplenote-mcp-server` |
| Docker | Change the tag in your config or command to the new release. |
| Docker Compose | In the clone, `git pull`. Change the tag in `docker-compose.override.yml` to the new release, or, if you run `latest`, run `docker compose pull`. Then `docker compose up -d`. |
| Helm | In the clone, `git pull`, then run `helm upgrade` with the release name, chart path and `--set` flags you installed with. Don't add `--reuse-values`: it keeps the defaults of the chart you installed, so changes to them, such as the writable home directory, never arrive. `--reset-then-reuse-values` takes the new defaults and keeps your earlier `--set` values. |

Then restart the client. The
[changelog](https://github.com/docdyhr/simplenote-mcp-server/blob/main/CHANGELOG.md)
lists what changed in each release.

## Uninstall

1. Remove the `simplenote` entry from your client's config. In Claude Code, run
   `claude mcp remove simplenote`.
2. Remove the server:
    - pipx: `pipx uninstall simplenote-mcp-server`
    - uv: `uv tool uninstall simplenote-mcp-server`
    - pip: delete the virtual environment.
    - Docker: remove the image, for example with
      `docker image rm docdyhr/simplenote-mcp-server:X.Y.Z`.
    - Docker Compose: `docker compose down` in the clone.
    - Helm: `helm uninstall simplenote-mcp-server`, then
      `kubectl delete secret simplenote-credentials`.
3. Delete what the server leaves in your home directory:
   `~/.config/simplenote-mcp/`, which holds the cached token, and
   `~/.simplenote_mcp/`, which holds metrics and alert logs. Its debug logs are
   in `simplenote_mcp_<uid>` under the system temp directory.

If you used Vault encryption, decrypt your notes first or keep the key: without
it, encrypted notes can't be read. The key is in your
`SIMPLENOTE_VAULT_KEY_FILE`, or in your keychain as the item
`simplenote-mcp-vault` (account `vault-master-key`).

Older versions cached the Simplenote token in a macOS keychain item named
`simplenote-mcp-server`. Current versions don't use it, so you can delete it in
Keychain Access.

## Troubleshooting

**The client can't start the server.** If Claude Desktop shows the server as
failed or its log says `spawn simplenote-mcp-server ENOENT`, use the command's
absolute path (see [Claude Desktop](#claude-desktop)).

**The server stops at startup.** Look for the `CRITICAL` line in the client's
log. If credentials are missing, it shows the message under
[Signing in](#signing-in).

**`Simplenote authentication failed` or
`Simplenote authentication returned no token`.** Check the email and password.
If they're right, password sign-in itself may be failing. On a Mac, sign in to
the Simplenote app so the server can use its token. Elsewhere, set
`SIMPLENOTE_TOKEN`.

**Tools find no notes, and the log shows
`Login to Simplenote API failed! Check Token.`** Simplenote rejected the token,
and the server keeps running with an empty cache. If you set `SIMPLENOTE_TOKEN`,
replace it. Otherwise clear the cached token and restart:

- Python package: delete `~/.config/simplenote-mcp/<email>.token` and restart
  the client.
- Docker Compose: `docker compose restart`. The cache is on a temporary mount,
  so a restart clears it.
- Helm: `kubectl rollout restart deployment/simplenote-mcp-server`, which
  replaces the pods and their volumes.
- A container started with `docker run -d`: remove it and run it again.

**Tools that create or change notes are missing.** Write mode is off. Set
`SIMPLENOTE_WRITE_MODE=true` and restart the client.

**Search misses notes in a large account.** Raise `CACHE_MAX_SIZE` to at least
your note count.

**With the Docker image, the client's log shows a JSON parse error at every
start.** The image's entrypoint prints `Using console script: simplenote-mcp-server`
to stdout before the server starts, and the client reads that line as a
protocol message. The session works anyway.

**Where are the logs?** The server always logs to stderr, which clients
usually capture. Claude Desktop writes it to `mcp-server-simplenote.log`. With
`LOG_TO_FILE=true`, the default, the server also writes `server.log` in the
`logs` directory of the installed package, next to the `server` directory
named in its `Running from:` log line. It also writes `simplenote_mcp_debug.log`
in `simplenote_mcp_<uid>` under the system temp directory. Set `LOG_LEVEL=DEBUG`
for more detail.
