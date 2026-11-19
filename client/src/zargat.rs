//! Zargat, the Hell Sovereign: a demon-themed 3D overlay on the shipped
//! CC0 Crowley humanoid rig. The base rig supplies locomotion; these authored
//! armor, horn, wing and blade meshes are attached to the replicated hero root.

use bevy::camera::visibility::RenderLayers;
use bevy::prelude::*;

use crate::{net::{GameStateSnapshot, NetworkAvatar, NetworkPlayerId, PlayerCosmeticAction, RemotePlayer}, player::Player, sprite::PlayerVisualMode};
use shared::loadout::SkillId;

#[derive(Resource)]
pub(crate) struct ZargatAssets {
    block: Handle<Mesh>,
    cone: Handle<Mesh>,
    sphere: Handle<Mesh>,
    armor: Handle<StandardMaterial>,
    armor_edge: Handle<StandardMaterial>,
    ember: Handle<StandardMaterial>,
    wing: Handle<StandardMaterial>,
    gold: Handle<StandardMaterial>,
    skin: Handle<StandardMaterial>,
    hair: Handle<StandardMaterial>,
}

#[derive(Component)]
pub(crate) struct ZargatVisual;

/// Marks original source-model mesh nodes after they are hidden for Zaragat.
#[derive(Component)]
struct ZargatBaseHidden;

/// Hide the source avatar meshes while retaining the replicated movement root.
pub(crate) fn hide_zargat_base_meshes(
    mut commands: Commands,
    roots: Query<&Children, With<ZargatVisual>>,
    nodes: Query<(Option<&Children>, Option<&Mesh3d>, Has<ZargatPart>, Has<ZargatBaseHidden>)>,
) {
    for children in &roots {
        let mut pending: Vec<Entity> = children.iter().collect();
        while let Some(entity) = pending.pop() {
            let Ok((children, mesh, is_zargat_part, already_hidden)) = nodes.get(entity) else {
                continue;
            };
            if let Some(children) = children {
                pending.extend(children.iter());
            }
            if mesh.is_some() && !is_zargat_part && !already_hidden {
                commands.entity(entity).insert((Visibility::Hidden, ZargatBaseHidden));
            }
        }
    }
}

#[derive(Component)]
pub(crate) struct ZargatPart { owner_id: Option<u64>, base_scale: Vec3 }

/// Marks the isolated avatar-collection preview, which uses render layer 28.
#[derive(Component)]
pub(crate) struct ZargatPreview;

#[derive(Component)]
pub(crate) struct ZargatWing {
    rest: Quat,
    side: f32,
}

#[derive(Component)]
pub(crate) struct ZargatTail { rest: Quat, phase: f32, side: f32 }

#[derive(Component)]
pub(crate) struct ZargatSword { rest: Quat, last_sequence: u64, swing_age: f32, slot: u8 }

/// Procedural shoulder and forearm motion layered over the Crowley locomotion rig.
#[derive(Component)]
pub(crate) struct ZargatArm {
    rest: Quat,
    side: f32,
    forearm: bool,
    last_sequence: u64,
    swing_age: f32,
    slot: u8,
}

pub(crate) fn setup_zargat_assets(
    mut commands: Commands,
    mode: Res<PlayerVisualMode>,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
) {
    if *mode != PlayerVisualMode::Models3d {
        return;
    }

    let material = |materials: &mut Assets<StandardMaterial>,
                    color: Color,
                    emissive: LinearRgba,
                    metallic: f32,
                    roughness: f32| {
        materials.add(StandardMaterial {
            base_color: color,
            emissive,
            metallic,
            perceptual_roughness: roughness,
            ..default()
        })
    };

    commands.insert_resource(ZargatAssets {
        block: meshes.add(Cuboid::new(1.0, 1.0, 1.0)),
        cone: meshes.add(Cone::new(0.5, 1.0).mesh().resolution(8)),
        sphere: meshes.add(Sphere::new(0.5).mesh().ico(2).expect("valid icosphere")),
        armor: material(
            &mut materials,
            Color::srgb(0.075, 0.035, 0.055),
            LinearRgba::BLACK,
            0.82,
            0.32,
        ),
        armor_edge: material(
            &mut materials,
            Color::srgb(0.34, 0.045, 0.035),
            LinearRgba::new(0.12, 0.008, 0.002, 1.0),
            0.58,
            0.36,
        ),
        ember: material(
            &mut materials,
            Color::srgb(1.0, 0.16, 0.025),
            LinearRgba::new(2.8, 0.20, 0.012, 1.0),
            0.12,
            0.24,
        ),
        wing: material(
            &mut materials,
            Color::srgb(0.105, 0.018, 0.035),
            LinearRgba::new(0.055, 0.002, 0.003, 1.0),
            0.18,
            0.62,
        ),
        gold: material(
            &mut materials,
            Color::srgb(0.72, 0.39, 0.075),
            LinearRgba::new(0.12, 0.035, 0.003, 1.0),
            0.78,
            0.27,
        ),
        skin: material(
            &mut materials,
            Color::srgb(0.29, 0.105, 0.22),
            LinearRgba::BLACK,
            0.04,
            0.72,
        ),
        hair: material(
            &mut materials,
            Color::srgb(0.78, 0.75, 0.69),
            LinearRgba::BLACK,
            0.08,
            0.48,
        ),
    });
}

pub(crate) fn attach_zargat_visuals(
    mut commands: Commands,
    assets: Option<Res<ZargatAssets>>,
    heroes: Query<
        (Entity, Option<&NetworkAvatar>, Option<&NetworkPlayerId>, Has<ZargatPreview>),
        (Without<ZargatVisual>, Or<(With<Player>, With<RemotePlayer>, With<ZargatPreview>)>),
    >,
) {
    let Some(assets) = assets else {
        return;
    };

    for (entity, avatar, player_id, is_preview) in &heroes {
        let owner_id = player_id.map(|id| id.0);
        if !is_preview && avatar.and_then(|avatar| avatar.0.as_deref()) != Some("zargat") {
            continue;
        }

        commands.entity(entity).insert(ZargatVisual).with_children(|parent| {
            let part = |parent: &mut ChildSpawnerCommands,
                        name: &str,
                        mesh: &Handle<Mesh>,
                        material: &Handle<StandardMaterial>,
                        position: Vec3,
                        scale: Vec3,
                        rotation: Quat| {
                let mut spawned = parent.spawn((
                    Mesh3d(mesh.clone()),
                    MeshMaterial3d(material.clone()),
                    Transform {
                        translation: position,
                        rotation,
                        scale,
                    },
                    Visibility::default(),
                    ZargatPart { owner_id, base_scale: scale },
                    Name::new(format!("Zargat-{name}")),
                ));
                if name == "Hellblade" {
                    spawned.insert(ZargatSword { rest: rotation, last_sequence: 0, swing_age: 1.0, slot: u8::MAX });
                }
                if matches!(name, "Bicep" | "Forearm" | "Bracer") {
                    spawned.insert(ZargatArm {
                        rest: rotation,
                        side: position.x.signum(),
                        forearm: name != "Bicep",
                        last_sequence: 0,
                        swing_age: 1.0,
                        slot: u8::MAX,
                    });
                }
                if is_preview {
                    spawned.insert(RenderLayers::layer(28));
                }
            };

            part(
                parent,
                "Cuirass",
                &assets.block,
                &assets.armor,
                Vec3::new(0.0, 1.02, 0.31),
                Vec3::new(0.78, 0.72, 0.19),
                Quat::IDENTITY,
            );

            // Zaragat's own body silhouette, independent of Crowley's visible mesh.
            part(parent, "DemonTorso", &assets.sphere, &assets.skin, Vec3::new(0.0, 1.02, 0.02), Vec3::new(0.62, 0.73, 0.38), Quat::IDENTITY);
            part(parent, "DemonNeck", &assets.sphere, &assets.skin, Vec3::new(0.0, 1.52, 0.08), Vec3::new(0.25, 0.27, 0.25), Quat::IDENTITY);
            part(parent, "DemonHead", &assets.sphere, &assets.skin, Vec3::new(0.0, 1.72, 0.04), Vec3::new(0.34, 0.39, 0.31), Quat::IDENTITY);
            part(parent, "InfernalMask", &assets.block, &assets.armor, Vec3::new(0.0, 1.61, 0.31), Vec3::new(0.39, 0.24, 0.12), Quat::IDENTITY);
            part(parent, "DemonJaw", &assets.cone, &assets.armor_edge, Vec3::new(0.0, 1.49, 0.30), Vec3::new(0.20, 0.25, 0.17), Quat::from_rotation_x(std::f32::consts::PI));
            part(parent, "InfernalPelvis", &assets.sphere, &assets.armor, Vec3::new(0.0, 0.57, 0.02), Vec3::new(0.43, 0.31, 0.34), Quat::IDENTITY);
            for side in [-1.0_f32, 1.0] {
                part(parent, "DemonThigh", &assets.sphere, &assets.skin, Vec3::new(side * 0.25, 0.39, 0.02), Vec3::new(0.25, 0.43, 0.27), Quat::from_rotation_z(-side * 0.05));
            }

            // Exposed violet musculature and dark bracers make the silhouette
            // read as a powerful demon rather than a fully armored human.
            for side in [-1.0_f32, 1.0] {
                part(
                    parent,
                    "Bicep",
                    &assets.sphere,
                    &assets.skin,
                    Vec3::new(side * 0.66, 1.03, 0.10),
                    Vec3::new(0.29, 0.38, 0.30),
                    Quat::from_rotation_z(-side * 0.12),
                );
                part(
                    parent,
                    "Forearm",
                    &assets.sphere,
                    &assets.skin,
                    Vec3::new(side * 0.72, 0.70, 0.17),
                    Vec3::new(0.23, 0.39, 0.24),
                    Quat::from_rotation_z(side * 0.10),
                );
                part(
                    parent,
                    "Bracer",
                    &assets.block,
                    &assets.armor,
                    Vec3::new(side * 0.72, 0.54, 0.25),
                    Vec3::new(0.30, 0.25, 0.28),
                    Quat::from_rotation_z(side * 0.10),
                );
                part(
                    parent,
                    "Pauldron",
                    &assets.sphere,
                    &assets.armor_edge,
                    Vec3::new(side * 0.49, 1.34, 0.04),
                    Vec3::new(0.43, 0.31, 0.38),
                    Quat::from_rotation_z(-side * 0.16),
                );
                part(
                    parent,
                    "PauldronRivet",
                    &assets.sphere,
                    &assets.gold,
                    Vec3::new(side * 0.56, 1.39, 0.34),
                    Vec3::splat(0.095),
                    Quat::IDENTITY,
                );
                // Layered shoulder spikes and articulated claw tips make the
                // silhouette read as a plated demon rather than a recolored human.
                part(
                    parent,
                    "ShoulderSpike",
                    &assets.cone,
                    &assets.gold,
                    Vec3::new(side * 0.70, 1.48, -0.02),
                    Vec3::new(0.16, 0.42, 0.16),
                    Quat::from_rotation_z(-side * 0.85),
                );
                part(
                    parent,
                    "GauntletClaw",
                    &assets.cone,
                    &assets.armor_edge,
                    Vec3::new(side * 0.76, 0.46, 0.39),
                    Vec3::new(0.075, 0.28, 0.075),
                    Quat::from_rotation_x(std::f32::consts::FRAC_PI_2),
                );
                part(
                    parent,
                    "Horn",
                    &assets.cone,
                    &assets.gold,
                    Vec3::new(side * 0.23, 1.88, 0.025),
                    Vec3::new(0.22, 0.58, 0.22),
                    Quat::from_rotation_z(-side * 0.34),
                );

                let wing_rotation = Quat::from_rotation_z(side * 0.27);
                let mut wing_entity = parent.spawn((
                    Mesh3d(assets.block.clone()),
                    MeshMaterial3d(assets.wing.clone()),
                    Transform {
                        translation: Vec3::new(side * 0.83, 1.47, -0.24),
                        rotation: wing_rotation,
                        scale: Vec3::new(0.92, 0.11, 0.48),
                    },
                    Visibility::default(),
                    ZargatWing {
                        rest: wing_rotation,
                        side,
                    },
                    ZargatPart { owner_id, base_scale: Vec3::new(0.92, 0.11, 0.48) },
                    Name::new("Zargat-BatWing"),
                ));
                if is_preview {
                    wing_entity.insert(RenderLayers::layer(28));
                }
                part(
                    parent,
                    "OuterWingPanel",
                    &assets.block,
                    &assets.wing,
                    Vec3::new(side * 1.27, 1.31, -0.25),
                    Vec3::new(0.66, 0.085, 0.36),
                    Quat::from_rotation_z(side * 0.48),
                );
                part(
                    parent,
                    "WingTip",
                    &assets.cone,
                    &assets.armor_edge,
                    Vec3::new(side * 1.30, 1.31, -0.24),
                    Vec3::new(0.20, 0.58, 0.18),
                    Quat::from_rotation_z(side * 0.58),
                );

                for feather in 0..3 {
                    let x = side * (0.68 + feather as f32 * 0.19);
                    let y = 1.25 - feather as f32 * 0.075;
                    part(
                        parent,
                        "WingFeather",
                        &assets.block,
                        &assets.armor,
                        Vec3::new(x, y, -0.18),
                        Vec3::new(0.30, 0.075, 0.10),
                        Quat::from_rotation_z(side * (0.22 + feather as f32 * 0.12)),
                    );
                }
            }

            // Heavy infernal greaves and knee plates give the silhouette a tank-like base.
            for side in [-1.0_f32, 1.0] {
                part(parent, "Greave", &assets.block, &assets.armor, Vec3::new(side * 0.25, 0.25, 0.12), Vec3::new(0.30, 0.48, 0.34), Quat::from_rotation_z(-side * 0.05));
                part(parent, "KneeGuard", &assets.sphere, &assets.armor_edge, Vec3::new(side * 0.25, 0.47, 0.30), Vec3::new(0.24, 0.20, 0.16), Quat::IDENTITY);
                part(parent, "BootSpur", &assets.cone, &assets.gold, Vec3::new(side * 0.25, 0.10, 0.34), Vec3::new(0.10, 0.28, 0.10), Quat::from_rotation_x(std::f32::consts::FRAC_PI_2));
            }

            // Segmented tail: it follows the moving hero and sways independently.
            for segment in 0..4 {
                let index = segment as f32;
                let rest = Quat::from_rotation_x(0.18 + index * 0.08);
                let mut tail = parent.spawn((
                    Mesh3d(if segment == 3 { assets.cone.clone() } else { assets.sphere.clone() }),
                    MeshMaterial3d(if segment == 3 { assets.armor_edge.clone() } else { assets.wing.clone() }),
                    Transform { translation: Vec3::new(0.0, 0.48 - index * 0.10, -0.42 - index * 0.19), rotation: rest, scale: if segment == 3 { Vec3::new(0.13, 0.34, 0.13) } else { Vec3::splat(0.16 - index * 0.018) } },
                    Visibility::default(),
                    ZargatTail { rest, phase: index * 0.65, side: if segment % 2 == 0 { 1.0 } else { -1.0 } },
                    ZargatPart { owner_id, base_scale: if segment == 3 { Vec3::new(0.13, 0.34, 0.13) } else { Vec3::splat(0.16 - index * 0.018) } },
                    Name::new(format!("Zargat-Tail-{segment}")),
                ));
                if is_preview { tail.insert(RenderLayers::layer(28)); }
            }

            // A crown of short back-spines makes the wing roots read as part of the armor.
            for spine in 0..3 {
                part(parent, "BackSpine", &assets.cone, &assets.gold, Vec3::new(0.0, 1.42 - spine as f32 * 0.22, -0.48), Vec3::new(0.12, 0.34, 0.12), Quat::from_rotation_x(-0.8));
            }

            // Long pale hair, swept backward in separate low-poly locks.
            for (side, length) in [(-1.0_f32, 0.56), (1.0_f32, 0.62), (0.0_f32, 0.72)] {
                part(
                    parent,
                    "SilverHair",
                    &assets.block,
                    &assets.hair,
                    Vec3::new(side * 0.18, 1.70, -0.18),
                    Vec3::new(0.16, length, 0.18),
                    Quat::from_rotation_z(-side * 0.24),
                );
            }
            for side in [-1.0_f32, 1.0] {
                part(
                    parent,
                    "BurningEye",
                    &assets.sphere,
                    &assets.ember,
                    Vec3::new(side * 0.12, 1.63, 0.43),
                    Vec3::splat(0.065),
                    Quat::IDENTITY,
                );
            }

            part(
                parent,
                "InfernalHeart",
                &assets.sphere,
                &assets.ember,
                Vec3::new(0.0, 1.04, 0.43),
                Vec3::new(0.19, 0.22, 0.11),
                Quat::IDENTITY,
            );
            // Three raised molten seams run down the breastplate.
            for rib in 0..3 {
                let y = 1.24 - rib as f32 * 0.17;
                for side in [-1.0_f32, 1.0] {
                    part(
                        parent,
                        "MoltenCuirassSeam",
                        &assets.block,
                        &assets.gold,
                        Vec3::new(side * (0.12 + rib as f32 * 0.025), y, 0.425),
                        Vec3::new(0.035, 0.13, 0.025),
                        Quat::from_rotation_z(side * 0.18),
                    );
                }
            }
            // Gold skull clasp at the waist, echoing the reference armor.
            part(
                parent,
                "SkullBelt",
                &assets.sphere,
                &assets.gold,
                Vec3::new(0.0, 0.61, 0.31),
                Vec3::new(0.25, 0.22, 0.12),
                Quat::IDENTITY,
            );
            for side in [-1.0_f32, 1.0] {
                part(
                    parent,
                    "BeltHorn",
                    &assets.cone,
                    &assets.gold,
                    Vec3::new(side * 0.15, 0.72, 0.36),
                    Vec3::new(0.08, 0.23, 0.08),
                    Quat::from_rotation_z(-side * 0.45),
                );
            }

            let sword_rotation = Quat::from_rotation_z(-0.16);
            part(
                parent,
                "Hellblade",
                &assets.block,
                &assets.ember,
                Vec3::new(0.72, 0.98, 0.36),
                Vec3::new(0.25, 0.96, 0.095),
                sword_rotation,
            );
            part(
                parent,
                "BladeSpine",
                &assets.cone,
                &assets.armor_edge,
                Vec3::new(0.72, 1.50, 0.36),
                Vec3::new(0.11, 0.24, 0.11),
                Quat::from_rotation_z(std::f32::consts::PI),
            );
            part(
                parent,
                "SwordGuard",
                &assets.block,
                &assets.gold,
                Vec3::new(0.72, 0.48, 0.36),
                Vec3::new(0.48, 0.10, 0.13),
                sword_rotation,
            );
            part(
                parent,
                "SwordGrip",
                &assets.block,
                &assets.armor,
                Vec3::new(0.72, 0.27, 0.36),
                Vec3::new(0.13, 0.34, 0.13),
                sword_rotation,
            );

            for side in [-1.0_f32, 1.0] {
                part(
                    parent,
                    "BackEmber",
                    &assets.sphere,
                    &assets.ember,
                    Vec3::new(side * 0.22, 1.12, -0.38),
                    Vec3::splat(0.105),
                    Quat::IDENTITY,
                );
            }
        });
    }
}

pub(crate) fn animate_zargat_wings(
    time: Res<Time>,
    snapshot: Res<GameStateSnapshot>,
    mut wings: Query<(&ZargatWing, &ZargatPart, &mut Transform)>,
    mut tails: Query<(&ZargatTail, &ZargatPart, &mut Transform), (Without<ZargatWing>, Without<ZargatSword>, Without<ZargatArm>)>,
    mut parts: Query<(&Name, &ZargatPart, &mut Transform), (Without<ZargatTail>, Without<ZargatWing>, Without<ZargatSword>, Without<ZargatArm>)>,
    mut swords: Query<(&mut ZargatSword, &ZargatPart, &mut Transform), (Without<ZargatWing>, Without<ZargatTail>, Without<ZargatArm>)>,
    mut arms: Query<(&mut ZargatArm, &ZargatPart, &mut Transform), (Without<ZargatWing>, Without<ZargatTail>, Without<ZargatSword>)>,
    actions: Query<(&NetworkPlayerId, &PlayerCosmeticAction)>,
) {
    let t = time.elapsed_secs();
    let sovereign = |part: &ZargatPart| part.owner_id.is_some_and(|owner| {
        snapshot.skill_effects.iter().any(|effect| {
            effect.owner_id == owner
                && effect.skill == SkillId::ZargatHellSovereign
                && effect.remaining_secs > 0.0
        })
    });
    for (wing, part, mut transform) in &mut wings {
        let factor = if sovereign(part) { 1.42 } else { 1.0 };
        let wave = (t * 2.2).sin() * if factor > 1.0 { 0.24 } else { 0.14 };
        transform.scale = part.base_scale * factor;
        transform.rotation = wing.rest * Quat::from_rotation_z(wing.side * wave);
    }
    for (tail, part, mut transform) in &mut tails {
        let factor = if sovereign(part) { 1.25 } else { 1.0 };
        transform.scale = part.base_scale * factor;
        transform.rotation = tail.rest * Quat::from_rotation_y((t * 1.8 + tail.phase).sin() * 0.18 * tail.side);
    }
    for (mut arm, part, mut transform) in &mut arms {
        if let Some((_, action)) = part.owner_id.and_then(|owner| actions.iter().find(|(id, _)| id.0 == owner)) {
            if action.sequence != arm.last_sequence {
                arm.last_sequence = action.sequence;
                arm.slot = action.slot;
                arm.swing_age = 0.0;
            }
        }
        arm.swing_age += time.delta_secs();
        let progress = (arm.swing_age / 0.62).clamp(0.0, 1.0);
        let envelope = if progress < 1.0 { (progress * std::f32::consts::PI).sin() } else { 0.0 };
        let pose = match arm.slot {
            0 => if arm.forearm { 1.05 } else { 0.72 }, // Rift Cleave
            1 => if arm.forearm { -0.82 } else { -0.56 }, // Hellblood
            2 => if arm.forearm { 0.72 } else { 0.48 }, // Infernal Charge
            3 => if arm.forearm { -0.62 } else { -0.42 }, // Hell Sovereign
            _ => if arm.forearm { 0.62 } else { 0.38 }, // basic attack
        };
        let idle = (t * 1.9 + arm.side * 0.7).sin() * 0.025;
        transform.rotation = arm.rest * Quat::from_rotation_z(arm.side * (idle + pose * envelope));
        transform.scale = part.base_scale * if sovereign(part) { 1.24 } else { 1.0 };
    }
    for (mut sword, part, mut transform) in &mut swords {
        if let Some((_, action)) = part.owner_id.and_then(|owner| actions.iter().find(|(id, _)| id.0 == owner)) {
            if action.sequence != sword.last_sequence {
                sword.last_sequence = action.sequence;
                sword.slot = action.slot;
                sword.swing_age = 0.0;
            }
        }
        sword.swing_age += time.delta_secs();
        let progress = (sword.swing_age / 0.42).clamp(0.0, 1.0);
        let envelope = if progress < 1.0 { (progress * std::f32::consts::PI).sin() } else { 0.0 };
        let swing = match sword.slot {
            0 => -1.12 * envelope,
            2 => 0.55 * envelope,
            3 => -0.72 * envelope,
            _ => -0.90 * envelope, // basic attack
        };
        transform.rotation = sword.rest * Quat::from_rotation_x(swing);
        transform.scale = part.base_scale * if sovereign(part) { 1.24 } else { 1.0 };
    }
    for (name, part, mut transform) in &mut parts {
        let factor = if sovereign(part) { 1.24 } else { 1.0 };
        transform.scale = part.base_scale * factor;
        let pulse = if name.as_str() == "Zargat-InfernalHeart" {
            1.0 + (t * 4.4).sin() * if factor > 1.0 { 0.20 } else { 0.10 }
        } else if name.as_str() == "Zargat-BurningEye" || name.as_str() == "Zargat-BackEmber" {
            1.0 + (t * 5.2).sin() * if factor > 1.0 { 0.25 } else { 0.12 }
        } else { 1.0 };
        transform.scale *= pulse;
    }
}
