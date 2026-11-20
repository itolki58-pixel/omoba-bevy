# Server migration: fixed heroes and five positions

This document is the server-side half of PR #5. The client/shared branch already exposes the fixed starter roster through `shared::hero_roster::STARTER_ROSTER`.

The server files are intentionally not edited in this client-owned PR. Apply these changes to the server build before using this client against a live match.

## Position mapping

The wire enum is kept compatible for now; the UI labels are new:

| Player-facing position | Existing wire enum | Physical minion lane |
|---|---|---|
| EXP | `Role::Solo` | `Lane::Top` |
| MID | `Role::Mid` | `Lane::Mid` |
| GOLD | `Role::Carry` | `Lane::Bot` |
| Jungle | `Role::Jungle` | Jungle camps |
| Support | `Role::Support` | Starts beside GOLD |

This keeps the current serialized values (`solo`, `mid`, `carry`, `jungle`, `support`) unchanged.

## 1. Enforce fixed hero identity on join

In `common/src/session.rs::handle_join_request_with_sprite`, resolve the profile before setting the identity:

```rust
let Some(profile) = shared::hero_roster::profile(hero_class) else {
    eprintln!("Rejected non-roster hero {}", hero_class.id());
    return;
};
player.hero.identity.handheld = shared::handheld::HandheldSelection::ClassDefault;
player.hero.identity.avatar = Some(profile.avatar.to_owned());
player.hero.identity.sprite_character = Some(profile.sprite_character.to_owned());
player.draft.role = profile.position;
```

Do not copy a client-supplied avatar or sprite over these values. The join admission path must reject a `hero_class` that is not in `shared::hero_roster` before calling this function.

The 12 selectable heroes use canonical avatar slugs. Zargat uses the user's supplied demon-knight source model at `art/zargat/demon-knight-source.glb`; the Android build generates the rigged `client/assets/avatars/zargat.glb` and `zargat.png` before packaging. This is user-provided content, not a CC0 asset. The server does not load the GLB, but its compiled/runtime avatar manifest must include the `zargat` entry from `client/assets/avatars/manifest.json`, or the join validator will strip/reject that avatar slug. It does not need a Studio ownership ticket.

## 2. Enforce fixed hero identity in prematch

In `server/src/prematch.rs::handle_prematch`, before calling `passport_admissions.begin_loadout`, validate a `PrematchAction::Select` against the roster profile:

```rust
if let PrematchAction::Select {
    hero_class,
    avatar,
    sprite_character,
    handheld,
    role,
    ..
} = &request.action
{
    let Some(profile) = shared::hero_roster::profile(*hero_class) else {
        player.draft.error = Some("This hero is not in the playable roster.".into());
        return;
    };
    let valid = avatar.as_deref() == Some(profile.avatar)
        && sprite_character.as_deref() == Some(profile.sprite_character)
        && handheld.is_default()
        && *role == profile.position;
    if !valid {
        player.draft.error = Some("Hero identity is fixed. Select a hero from the roster.".into());
        return;
    }
}
```

Then in `apply_prematch`, store the canonical values from the profile rather than trusting the request:

```rust
let profile = shared::hero_roster::profile(hero_class)
    .expect("selection was validated before admission");
player.hero.identity.handheld = shared::handheld::HandheldSelection::ClassDefault;
player.hero.identity.avatar = Some(profile.avatar.to_owned());
player.hero.identity.sprite_character = Some(profile.sprite_character.to_owned());
player.draft.role = profile.position;
```

The passport admission check may remain in place as a safety check, but only the fixed bundled avatar and `ClassDefault` equipment should reach it. No player-selected weapon ID is accepted.

## 3. Spawn by position

Currently `common/src/session.rs::reset_player_round` calls `spawn_position_for_team`, so everyone starts at the same base location.

Replace that call with a role-aware spawn resolver in `common/src/world.rs`:

- EXP (`Role::Solo`) starts at the friendly end of `Lane::Top`.
- MID starts at the friendly end of `Lane::Mid`.
- GOLD (`Role::Carry`) starts at the friendly end of `Lane::Bot`.
- Support starts beside the GOLD-lane spawn, with a small lateral offset so the two heroes do not overlap.
- Jungle starts at the friendly jungle entrance nearest the first neutral camp.

Use `build_minion_path(map_layout, lane, team)` to get each lane's friendly-side direction. For Support, offset perpendicular to the first path segment. For Jungle, use the friendly-side camp anchors from `shared::jungle::camp_layout`; do not spawn the jungler on a lane.

Respawns should use the same role-aware resolver so players return to their assigned position.

## 4. Lane-specific minion rewards

`MinionState` already carries its `lane`, so no wire field is needed.

In `common/src/sim/minions.rs`:

1. Capture `target_minion.state.lane` when the minion dies.
2. Pass that lane into `award_minion_kill_rewards(players, attacker_team, lane)`.
3. Keep the existing team-share calculation, but exclude `Role::Jungle` from lane-minion recipients: the jungler earns their farm from neutral camps.
4. Apply a small position bonus to the matching lane role after the normal per-player share:

```rust
if lane == Lane::Top && player.draft.role == Role::Solo {
    xp = (xp as f32 * 1.15).round() as u32;
}
if lane == Lane::Bot && player.draft.role == Role::Carry {
    gold = (gold as f32 * 1.15).round() as u32;
}
```

- EXP-lane minions: +15% XP for the EXP hero.
- MID minions: normal gold and XP.
- GOLD-lane minions: +15% gold for the GOLD hero.
- Jungle heroes receive no lane-minion share; their farm is from neutral camps.
- Support still receives the normal team-shared lane rewards while helping the lane.

If a team has no hero assigned to the matching lane, the lane bonus is not reassigned to another position.

## 5. Jungle and Support behavior

Both starter junglers are `Warden` and `Adventurer`. Both use the Jungle position and can farm neutral camps. Keep Warden's existing passive exactly as it is; this branch does not add or rebalance jungle damage, gold or XP bonuses for Adventurer. Neutral camp rewards continue through the existing authoritative neutral-kill path.

Support has the fixed `Role::Support` position and spawns beside GOLD from match start. It can then rotate to other lanes; no new movement restriction is needed.

## 6. Verification checklist

- [ ] Join rejects hero IDs outside `shared::hero_roster::STARTER_ROSTER`.
- [ ] Join and prematch ignore/reject custom avatar, sprite, role and weapon values.
- [ ] Each of the 12 heroes receives its canonical avatar and position.
- [ ] EXP hero receives the EXP-lane XP bonus only.
- [ ] GOLD hero receives the GOLD-lane gold bonus only.
- [ ] MID receives baseline lane rewards.
- [ ] Jungle receives no lane-minion income and can farm neutral camps.
- [ ] Support starts with GOLD and can leave to help another lane.
- [ ] Reconnect and respawn preserve the hero's assigned position.

If the game server is built from a separate checkout, copy these two updated files into that checkout and rebuild/restart the server:

- `shared/src/hero_roster.rs` — canonical hero-to-avatar mapping (Warrior/Zargat now maps to `zargat`)
- `client/assets/avatars/manifest.json` — allows the server to normalize and retain the `zargat` slug

The server does not need `zargat.glb` or the Blender script; those are client-only assets generated during the Android build.
