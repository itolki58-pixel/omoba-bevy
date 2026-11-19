//! Zargat, the Hell Sovereign: a demon-themed 3D overlay on the shipped
//! CC0 Crowley humanoid rig. The base rig supplies locomotion; these authored
//! armor, horn, wing and blade meshes are attached to the replicated hero root.

use bevy::camera::visibility::RenderLayers;
use bevy::prelude::*;

use crate::{net::{NetworkAvatar, RemotePlayer}, player::Player, sprite::PlayerVisualMode};

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
struct ZargatVisual;

/// Marks the isolated avatar-collection preview, which uses render layer 28.
#[derive(Component)]
pub(crate) struct ZargatPreview;

#[derive(Component)]
struct ZargatWing {
    rest: Quat,
    side: f32,
}

#[derive(Component)]
struct ZargatTail { rest: Quat, phase: f32, side: f32 }

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
        (Entity, Option<&NetworkAvatar>, Has<ZargatPreview>),
        (Without<ZargatVisual>, Or<(With<Player>, With<RemotePlayer>, With<ZargatPreview>)>),
    >,
) {
    let Some(assets) = assets else {
        return;
    };

    for (entity, avatar, is_preview) in &heroes {
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
                    Name::new(format!("Zargat-{name}")),
                ));
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
    mut wings: Query<(&ZargatWing, &mut Transform)>,
    mut tails: Query<(&ZargatTail, &mut Transform), Without<ZargatWing>>,
    mut parts: Query<(&Name, &mut Transform), (Without<ZargatTail>, Without<ZargatWing>)>,
) {
    let t = time.elapsed_secs();
    let wave = (t * 2.2).sin() * 0.14;
    for (wing, mut transform) in &mut wings {
        transform.rotation = wing.rest * Quat::from_rotation_z(wing.side * wave);
    }
    for (tail, mut transform) in &mut tails {
        transform.rotation = tail.rest * Quat::from_rotation_y((t * 1.8 + tail.phase).sin() * 0.18 * tail.side);
    }
    for (name, mut transform) in &mut parts {
        let label = name.as_str();
        if label == "Zargat-InfernalHeart" {
            let pulse = 1.0 + (t * 4.4).sin() * 0.10;
            transform.scale = Vec3::new(0.19, 0.22, 0.11) * pulse;
        } else if label == "Zargat-BurningEye" || label == "Zargat-BackEmber" {
            let pulse = 1.0 + (t * 5.2).sin() * 0.12;
            transform.scale = Vec3::splat(0.065 * pulse);
        }
    }
}
