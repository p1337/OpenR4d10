# External service adapters

OpenR4d10 keeps account-based integrations outside its main process. A
BrandMeister, Mumble, Discord, Telegram, Spotify or other external adapter must
run as its own unprivileged system service and expose protocol version 1 on a
local Unix stream socket.

This is an integration boundary, not a claim that an account has already been
configured. The dashboard reports an external service as ready only after its
manifest exists, its socket accepts a connection and its `status` response
contains `{"ok": true, "ready": true}`.

## Non-secret manifest

Create `/etc/openr4d10/services.d/<service-id>.toml`. The filename must match a
known external service and the socket has one exact permitted location:

```toml
[adapter]
protocol = 1
socket = "/run/openr4d10-adapters/mumble.sock"
timeout_seconds = 2
```

The manifest contains no executable arguments, environment values, account
names, tokens or passwords. The adapter's own systemd unit should run as a
dedicated service-specific user and use a service-specific
`LoadCredential=`/`LoadCredentialEncrypted=` entry when credentials are
required. Do not grant the main `openr4d10` user access to those credential
files.

## Wire protocol

One connection carries one request and one response. Both are UTF-8 JSON
objects terminated by a newline. The core limits requests to 16 KiB, responses
to 64 KiB and timeouts to at most ten seconds.

Status request:

```json
{"protocol":1,"service_id":"mumble","operation":"status","parameters":{}}
```

Minimum successful response:

```json
{"ok":true,"ready":true,"status":"connected"}
```

Other operations use the same envelope. The local `/api/control` action is
`adapter_call` with `service_id`, `operation` and an optional `parameters`
object. Secret-shaped fields (`password`, `token`, `cookie`, `session`, API
keys and similar names) are rejected before any socket connection. URLs are
stripped of query and fragment components in public responses.

An adapter must never return credentials. The core also rejects secret-shaped
response keys, excessive nesting, large collections and unsupported JSON
types. A failed handshake leaves the service visibly in `adapter_error`; a
missing manifest leaves it in `configuration_required`.

## Isolation requirements

Each account-bearing adapter needs its own Unix user and its own systemd unit.
Its socket should be created below `/run/openr4d10-adapters` with a group that
allows the `openr4d10` process to connect. Its credential directory must not be
readable by that group or by other adapter users. Add only the devices and
network access that the one adapter actually needs.

Do not place an account-bearing adapter directly in the OpenR4d10 process and
do not store its credentials in `openr4d10.sqlite3`, a manifest, Git, a command
line or the journal.
