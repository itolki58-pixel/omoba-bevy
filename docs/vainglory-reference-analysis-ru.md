# Vainglory reference analysis for OMOBA

Date: 2026-11-21  
Purpose: design reference only. This document does not copy Vainglory source code, models, textures, animations, sounds, characters, map art or other proprietary assets.

## Executive summary

Vainglory is a useful reference for OMOBA for three reasons:
1. It was designed around precise touch controls and responsiveness.
2. Its original 3v3 Halcyon Fold has a distinct, readable lane-jungle-objective loop; later 5v5 introduced broader lanes, ranged/melee zones and split-push decisions.
3. Its hero presentation and animation language make silhouettes, attack tells and skill readability central to combat.

Official materials describe 3v3 matches, laning, ganking/objective-taking and teamfight phases, 60 FPS ambitions and sub-30ms control responsiveness. Later official material describes 5v5 with a three-lane map. These are design targets, not a guarantee that OMOBA can match the same performance on all phones.

## 1. Game loop and map

### Original 3v3: Halcyon Fold
- One primary lane connecting the bases.
- Jungle below the lane with neutral camps and routes for ambushes.
- Jungle shop to buy without returning to base.
- Gold Mine as a shared team reward objective.
- Minion Mines that strengthen future lane waves.
- Kraken replacing the Gold Miner later as a major siege threat.
- Turrets protect the base in a cascading unlock order; the Vain crystal is protected until required turrets fall.
- Sanctuary/base provides healing, protection, shop access and a channelled return/recall.

Design lesson for OMOBA: each neutral object should create a clear team decision and alter the next few minutes of play, not simply award generic gold.

### Later 5v5: Sovereign's Rise
Official developer notes describe three important design goals:
- First-mover advantage: taking initiative should create a window that the team can exploit.
- Ranged/melee zones: open areas and terrain should create safer firing positions and vulnerable approach routes.
- Split-pushing: teams should be able to threaten multiple locations, forcing defenders to choose.

Design lesson for OMOBA: our existing three lanes and 18 towers provide the foundation. Improve map readability, alternate routes, brush/vision, objective timing and meaningful split-push opportunities rather than rebuilding the map blindly.

## 2. Hero design and combat readability

Vainglory's heroes should be studied as functional design examples, not copied:
- Silhouette: recognizable at phone-screen size and from the isometric camera.
- Idle / move / turn: establishes weight, facing and personality.
- Basic attack: clear anticipation, hit frame and recovery.
- Skill wind-up: readable warning before a dangerous effect.
- Hit reaction / death / respawn: communicates state without relying only on UI.
- Locomotion transitions: start, stop, turn-in-place, strafe if supported, run and attack-move.
- VFX hierarchy: distinguish self, ally, enemy, neutral objective and ground-targeted effects.
- Sound cues: confirm casts, hits, cooldown readiness and objective events.

For each OMOBA hero define a combat animation sheet:
1. Idle
2. Walk/run forward
3. Start/stop and turn
4. Basic attack (melee or ranged)
5. Skill 1 / 2 / ultimate
6. Hit reaction
7. Death
8. Recall / teleport
9. Spawn / victory (optional polish)

## 3. Character model skeletons (rigs)

A model skeleton is a hierarchy of bones used to deform a mesh and attach equipment/effects. The exact Vainglory rig files are not required to reproduce the useful technical ideas. Do not extract or redistribute proprietary rigs, meshes, textures or animation clips from game packages without an explicit license.

Recommended OMOBA rig standard:
- Root: world placement and global facing.
- Hips/pelvis: body motion and weight shift.
- Spine_01 / Spine_02 / Chest: torso bend and attack anticipation.
- Neck / Head: look direction and hit reactions.
- Clavicle_L/R, UpperArm_L/R, Forearm_L/R, Hand_L/R: weapon and casting motion.
- Thigh_L/R, Calf_L/R, Foot_L/R, Toe_L/R: locomotion and foot planting.
- Optional weapon socket(s), back socket, hand socket(s), VFX socket(s).
- Optional facial bones, hair, cloth, tail, wings and secondary motion for specific heroes.

Naming should be consistent across the roster. A shared humanoid base rig allows retargeting common locomotion and hit reactions. Hero-specific bones should be optional extensions, not required for every animation.

### Rig quality rules
- Apply consistent forward axis and scale; document which local axis is forward.
- Keep root motion policy consistent (in-place locomotion is simpler for network-authoritative movement).
- Use stable bind pose and bone naming.
- Avoid excessive bone counts on mobile; use only deform bones that visibly improve silhouette or animation.
- Keep weapons and VFX attached to sockets, not hard-coded world offsets.
- Test retargeting on short, tall, bulky and non-human characters.
- Verify attack hit frame against server-authoritative damage timing; visuals must not decide hit results.
- Use LODs and reduced skinning cost on lower-end Android devices.

## 4. Model and animation pipeline for OMOBA

Preferred pipeline:
1. Create original concept and silhouette.
2. Model original mesh in Blender or another DCC tool.
3. Retopologize and create mobile-friendly UVs/materials.
4. Rig to the shared OMOBA humanoid skeleton or a documented creature variant.
5. Create original animation clips or use properly licensed animation sources.
6. Export GLB/glTF and validate materials, skeleton hierarchy, animation names and scale.
7. Add model/animation entries to OMOBA's client asset registry.
8. Connect animation state to replicated hero actions and movement state.
9. Test on Android for draw calls, skinning, memory and frame pacing.

Do not replace the server's authoritative combat rules with animation events. The server decides movement, cooldown, range, damage, hit result and death. Client animation is presentation synchronized to those results.

## 5. What to borrow as design patterns

| Vainglory reference | OMOBA adaptation |
|---|---|
| Precise touch control | Compact joystick, deliberate aim controls, responsive skill casting |
| Lane + jungle tension | Three lanes with meaningful jungle routes and gank paths |
| Gold Mine | Team objective with shared reward and clear contest window |
| Minion Mines | A distinct objective that changes later minion waves, if it adds strategic depth |
| Kraken siege threat | Late-game boss that helps push a lane, with clear counterplay |
| Cascading turret defense | Preserve OMOBA's existing tier unlock and base protection |
| Ranged/melee zones | Terrain and brush that create readable engagement spaces |
| Split-pushing | Multiple simultaneous threats and map decisions |
| Hero-specific builds | Keep existing shop but add understandable recommended builds per role |

Not every mechanic should be copied. For example, the original 3v3 single-lane economy/objectives need rebalancing for a three-lane 5v5 game.

## 6. Priority implementation plan

### A. First: audit existing OMOBA assets and animation states
- List every current hero model, GLB, skeleton, animation clip and material.
- Record missing locomotion, attack, cast, hit and death states.
- Identify duplicate rigs and incompatible forward axes.
- Verify Zaragat's forward axis and animation facing before adding more content.

### B. Standardize one shared rig
- Choose one existing compatible humanoid model as the reference rig.
- Document bone names, root orientation, scale and weapon sockets.
- Retarget a small test set: idle, run, attack, cast, hit, death.
- Validate on Android before applying to the whole roster.

### C. Build one vertical-slice hero
- Use an original OMOBA hero design (Zaragat can be the first if its model source is available).
- Add a complete model, shared rig, animation state machine, VFX sockets and three skills.
- Confirm server/client timing and Android performance.
- Only then expand the pipeline to the rest of the roster.

### D. Map and objectives
- Prototype a Vainglory-inspired team objective in OMOBA's current map.
- Test objective spawn timing, contest routes, shared reward, comeback potential and siege impact.
- Do not add multiple new objectives at once.

## 7. Asset/legal boundary

Official Vainglory pages and videos can be used as references for gameplay analysis and visual study. They do not grant permission to copy or redistribute the game's proprietary character meshes, rigs, animation clips, textures, sounds, map assets or source code. The official support FAQ says the game is no longer in active development; that does not make its assets public domain.

For production, use:
- original OMOBA-created models and rigs;
- assets with a license that permits modification and commercial use as needed;
- user-provided assets where the user has the rights to use them.

If the user provides a legally obtained model/rig or a permitted sample asset, inspect its structure and use it as a technical reference within its license. Do not publish extracted Vainglory assets in OMOBA.

## 8. References

- Official Vainglory game overview: https://en.vainglorygame.com/game/
- Official Vainglory Academy: https://en.vainglorygame.com/academy/
- Official 5v5 design notes: https://www.vainglorygame.com/vainglorylive/update-2-3-notes-charms-passes-streamlined-experiences/
- Official Vainglory Community Edition status (2020): https://www.vainglorygame.com/news/vainglory-community-edition-update-edtheshred
- Official support FAQ (2024): https://superevil.zendesk.com/hc/en-us/articles/27836259401243-Frequently-Asked-Questions-Vainglory
- Official Vainglory YouTube channel, including hero spotlights and map tutorials: https://www.youtube.com/@vainglory

---
This is a design and asset-pipeline analysis, not a claim that OMOBA has implemented these changes. The first concrete engineering task is a local inventory of existing OMOBA models, rigs and animation clips, followed by a one-hero vertical slice.
