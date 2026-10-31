# External service adapters

OpenR4d10 keeps account-based integrations outside its main process. A
BrandMeister, Mumble, Discord, Telegram, Spotify or other external adapter must
run as its own unprivileged system service and expose protocol version 1 on a
local Unix stream socket.

Weather is a native, credential-free core service and does not use this
external adapter contract. It is restricted to the official DWD WMS endpoint,
locally re-encodes all frames and exposes only local cache paths to the UI.

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

## Anker SOLIX telemetry contract

`anker_solix` is a known, disabled-by-default external service. Its manifest is
non-secret and follows the normal fixed socket rule:

```toml
[adapter]
protocol = 1
socket = "/run/openr4d10-adapters/anker_solix.sock"
timeout_seconds = 3
```

The preferred adapter is local Modbus TCP for the device models supported by
Anker's official integration. It needs the SOLIX device IP and enabled
third-party Modbus control, but no Anker cloud password. Other models may use
the community `anker-solix-api` only as a separately installed, explicitly
unofficial cloud adapter. In that case account, password and two-letter country
code must be supplied through service-specific `LoadCredential=` files. They
must never be placed in the manifest, database, environment file, web URL,
command line or journal.

The core calls `status`. A ready adapter may return this bounded public payload:

```json
{
  "ok": true,
  "ready": true,
  "status": "connected",
  "metrics": {
    "solar_w": 612,
    "home_w": 281,
    "grid_w": -144,
    "battery_w": 187,
    "battery_percent": 73,
    "energy_today_kwh": 2.8
  }
}
```

Only these six numeric fields and sane ranges reach the dashboard. Negative
`grid_w` or `battery_w` values are permitted because import/export and
charge/discharge direction depend on the adapter's documented convention.
Serial numbers, site IDs, device IDs, account names and all secret-shaped fields
must be omitted. A model that cannot supply a value simply omits that field.

No SOLIX adapter is claimed ready merely because this contract exists. The
dashboard remains `configuration_required` until a real isolated adapter is
installed, its socket responds, and the exact user's device has been tested.
