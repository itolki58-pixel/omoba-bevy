# Server integration contract: tactical pings and objective timers

This is a server-owner handoff. The client changes in PR #18 are intentionally local-only; do not describe them as team communication until the server relay exists. No server code is changed by that PR.

## Confirmed current protocol/server behavior

- `shared/src/protocol/wire.rs`: `ClientPacket::Ping` is an empty keepalive packet. Keep it unchanged; it must not be repurposed as a tactical ping.
- `shared/src/protocol/wire.rs`: `ServerPacket::Snapshot` currently has no tactical-ping collection or boss respawn timer collection.
- `shared/src/protocol/wire.rs`: `NeutralState` contains identity, position, HP and AI state, but no respawn deadline/remaining time.
- `server/src/snapshot.rs`: the current neutral snapshot filters to `dead_until.is_none() && hp > 0`. Dead bosses therefore disappear from client snapshots.
- `common/src/entities.rs`: server neutral runtime state already has `dead_until: Option<Instant>`.
- `common/src/neutrals.rs`: boss first-spawn and respawn schedules already use `dead_until`; no new timer simulation is required.

## Tactical ping relay

Add a separate packet; preserve the existing heartbeat:

```rust
enum TacticalPingKind { Attack, Retreat, OnMyWay, Missing }

ClientPacket::TacticalPing {
    x: f32,
    z: f32,
    kind: TacticalPingKind,
    server_epoch: u64,
    match_id: u64,
    request_id: u64,
}

struct TacticalPingState {
    id: u64,
    player_id: u64,
    team: Team,
    x: f32,
    z: f32,
    kind: TacticalPingKind,
    remaining_secs: f32,
}
```

Add `tactical_pings: Vec<TacticalPingState>` to the snapshot with `#[serde(default, skip_serializing_if = "Vec::is_empty")]`.

Server requirements:

1. Accept only from a joined player in the matching `server_epoch` and `match_id`; never accept pings from an unjoined endpoint.
2. Reject NaN/infinite coordinates, clamp valid coordinates to shared map bounds, and validate the ping kind.
3. Rate-limit per player (suggested: one ping every 0.8 seconds) and cap active pings per match/team (suggested: 8).
4. Expire each ping after 3 seconds; replicate only to teammates of the sender. Do not reveal pings to the opposing team.
5. Treat pings as presentation only: they must not move units, grant vision, reveal hidden enemies, or alter combat state.
6. Deduplicate/reject replayed request IDs where practical. Keep the existing empty `ClientPacket::Ping` heartbeat behavior untouched.

Likely integration points are `shared/src/protocol/wire.rs`, the gameplay packet match in `server/src/runtime/dispatch.rs`, and per-recipient snapshot assembly in `server/src/snapshot.rs`. Add serde golden tests, rate-limit tests, team-isolation tests, expiry tests and payload-size tests.

## Boss objective timers

A client cannot display an authoritative respawn countdown from the current snapshot: dead neutrals are filtered out and `NeutralState` has no timer field.

Preferred additive contract: add a separate `boss_objectives` collection to `ServerPacket::Snapshot`, rather than putting respawn data on every ordinary jungle neutral:

```rust
struct BossObjectiveState {
    camp_type: NeutralCampType,
    alive: bool,
    hp: Option<f32>,             // Some only when the boss is visible to this recipient
    max_hp: f32,
    respawn_remaining_secs: Option<f32>,
}
```

Build it from the existing boss entries in `world.neutrals`:

- `alive = neutral.dead_until.is_none() && neutral.state.hp > 0.0`.
- When `dead_until = Some(deadline)`, compute `deadline.saturating_duration_since(now).as_secs_f32()`.
- Include dormant bosses waiting for their first scheduled spawn as well as killed bosses waiting to respawn.
- Keep HP hidden when the boss is outside this recipient's team vision. The known objective timer may be replicated to both teams, but never use it to reveal hidden combatants or boss HP.
- Keep ordinary jungle-camp snapshot behavior unchanged.

The client can then show a real countdown and objective state; it must not invent a timer from a fixed duration or start a local countdown at an unconfirmed kill event.

## Compatibility and rollout

- All new snapshot fields must be additive, defaulted on deserialize, and omitted when empty/absent.
- Old clients must continue to ignore the new fields; old servers must continue to work with the client showing no team ping/respawn countdown.
- Ship the server change and client send/render path together before enabling multiplayer pings or claiming objective-timer parity.
