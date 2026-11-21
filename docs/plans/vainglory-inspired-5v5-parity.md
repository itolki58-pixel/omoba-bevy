# Vainglory-inspired 5v5 feature parity plan

## Non-negotiable project constraints

- Keep OMOBA's 5v5 match format and three lanes (Top, Mid, Bot).
- Keep Bevy/Rust as the client/runtime architecture; adapt systems rather than transplanting another engine.
- Keep the existing OMOBA server protocol stable unless a feature explicitly requires a coordinated server change. Server-side changes are delivered as a separate patch/instructions for the server owner.
- Do not import proprietary Vainglory source, extracted game data, models, textures, animation clips, audio, maps, UI artwork, or other protected files. Use gameplay research as design reference and create original or properly licensed content.
- Mobile-first HUD: compact controls, readable combat information, no unnecessary obstruction of the battlefield.
- Russian localization is required; do not ship Chinese glyphs as accidental fallback text.

## Existing OMOBA foundations verified in source

| Area | Existing implementation | Port/adaptation direction |
|---|---|---|
| Arena | Three lanes, shared lane geometry, towers, bases and navigation | Preserve three lanes; improve readability, route clarity and objective pacing |
| Team size / roles | Five role slots: Carry, Solo, Mid, Jungle, Support | Preserve 5-player teams; refine draft recommendations and role clarity |
| Vision | Team vision sources, brush concealment and client fog presentation | Improve reveal feedback, brush readability, minimap and vision tools |
| Jungle | Ten mirrored camps and Warden camp bonuses | Add objective timing, camp-state feedback, invade/contest affordances and distinct reward presentation |
| Bosses | Boss assets and boss systems exist | Audit spawn cadence, team buffs, contest windows and map announcements |
| Minions | Lane minion simulation and client presentation exist | Improve wave composition, last-hit feedback, lane pressure and siege readability |
| Combat | Basic attacks, abilities, targeting, cooldowns, status effects and combat HUD exist | Improve hit confirmation, cast previews, crowd-control feedback and readable threat cues |
| Progression | Shared level/XP/skill-rank rules exist (current cap is 10) | Evaluate a Vainglory-inspired ability progression/overdrive model without breaking server compatibility |
| Items | Shared item catalog, six-slot inventory and recommendations exist | Add clearer build paths, shop recommendations, component trees and situational item hints |
| Match feedback | Live scoreboard, kill feed and tactical HUD exist | Add objective notices, streak/assist feedback, tactical pings and post-match insights |
| Mobile input | Joystick, attack and skill controls exist | Refine tap/hold/drag targeting, camera behavior and compact layout |
| Presentation | 3D avatar, animation, VFX and map asset pipelines exist | Improve hero readability, animation timing, silhouette and performance budgets |

## Delivery sequence

### Phase 0 — Stabilize the current client
- [ ] Verify the Android build and hero-preview fixes from PR #11 on a real device.
- [ ] Confirm Zaragat's forward-facing locomotion in all four movement directions.
- [ ] Confirm hero models render in draft, party stage and collection preview.
- [ ] Confirm the compact hero grid remains below the "Герои" heading on narrow screens.

### Phase 1 — Match readability and tactical communication
- [ ] Add a client-side tactical ping wheel and map/world ping visuals.
- [ ] Define a versioned, bounded ping message for server relay; provide the server patch separately before enabling multiplayer relay.
- [ ] Add objective spawn/respawn timers and neutral-objective announcements using authoritative server timestamps.
- [ ] Improve minimap layers for lanes, towers, camps, bosses, brush and allied/enemy visibility.

### Phase 2 — Lane and jungle gameplay
- [ ] Audit minion wave cadence, composition, siege pressure and last-hit rewards.
- [ ] Audit jungle camp respawn, leash/reset, reward and invade rules.
- [ ] Audit major boss objectives and team buffs; tune their impact for 5v5.
- [ ] Add readable sanctuary/shop/river interactions using original OMOBA assets and rules.

### Phase 3 — Hero mastery and combat
- [ ] Audit each selectable hero's passive, basic attack, Q/W/E/R kit, cast type and crowd-control rules.
- [ ] Evaluate skill overdrive/mastery progression; coordinate any authoritative rank/level protocol change with the server owner.
- [ ] Improve animation-state transitions, attack wind-up, hit-stop, impact VFX and damage feedback.
- [ ] Add role-specific build recommendations and counter-item guidance.

### Phase 4 — Mobile polish and competitive quality
- [ ] Tune camera follow, camera bounds, target selection and aim assist.
- [ ] Tune mobile joystick, skill drag, attack targeting and quick-buy ergonomics.
- [ ] Profile CPU/GPU, draw calls, asset sizes, memory and frame pacing on Android.
- [ ] Run full 5v5 QA from draft through base destruction, reconnect and post-match.

## Compatibility policy

Any change to authoritative combat, rewards, timers, objectives, matchmaking, player state or wire messages must be treated as a coordinated client/server feature. The client PR must identify the exact server-side files, schema changes, defaults and migration steps. Do not silently change the protocol or claim multiplayer parity from a client-only mock.
