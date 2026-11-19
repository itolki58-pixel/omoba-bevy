# Windows public lobby deployment

The default server role is `standalone`. It is intended for direct LAN/practice
matches and does not provide the public matchmaking service required by the
Home screen's normal **Play** button. Setting `OMOBA_MATCH_MODE=dev` changes
match start rules; it does not turn a standalone server into a public lobby.

A database-backed public lobby requires:

- PostgreSQL schema migrated before starting the server.
- A game-runtime PostgreSQL role with the grants in `account-api/ops/grants.sql`.
- `OMOBA_SERVER_ROLE=lobby` and a non-empty `OMOBA_DATABASE_URL`.
- A reachable public host and UDP access to the coordinator and worker ports.

## Database preparation

Follow `account-api/README.md` to create a database, migration-owner role,
`omoba_game` and `omoba_portal` runtime roles. Do not use the migration-owner
credentials as the game server's runtime credentials.

From the repository root, set the migration-owner DSN and apply the migrations:

```powershell
$env:OMOBA_DATABASE_URL = $env:OMOBA_MIGRATION_DATABASE_URL
cargo run --locked -p omoba-account-api -- migrate
psql $env:OMOBA_MIGRATION_DATABASE_URL -v portal_role=omoba_portal -v game_role=omoba_game -f account-api/ops/grants.sql
```

Set `OMOBA_GAME_DATABASE_URL` to the restricted game-runtime DSN. The launcher
copies it to `OMOBA_DATABASE_URL` for the server and its match-worker child
processes. Keep both DSNs in local environment variables or a secret manager;
never commit them or paste passwords into chat.

## Start the public lobby

Run PowerShell from the repository checkout. For a LAN test, pass the host IP
that the phone can reach. For Internet play, pass the public DNS name or public
IP and configure NAT/firewall forwarding to this machine.

```powershell
$env:OMOBA_DATABASE_URL = $env:OMOBA_GAME_DATABASE_URL
.\deploy\windows\start-lobby.ps1 -PublicHost YOUR_REACHABLE_HOST
```

The launcher sets:

- Lobby coordinator: UDP `0.0.0.0:4000` by default.
- Match workers: UDP `41000-41015` by default.
- Worker bind address: `0.0.0.0`.
- Public worker endpoint host: the `-PublicHost` argument.

Open/forward UDP 4000 and the configured worker-port range. The worker ports
must be reachable by every client; opening only UDP 4000 is not sufficient.
Adjust `-GamePort`, `-FirstMatchPort`, `-MatchCapacity`, or `-BindIp` when
the deployment needs a different range.

## Account API and Google sign-in

The game currently creates/uses device-key identities and supports browser
pairing/device enrollment through the Account API. That is not Google OAuth.
Google sign-in is not implemented in this repository yet; it needs a trusted
Google ID-token verification flow in the Account API and a client/portal sign-in
surface. Never put a Google client secret in the APK.
