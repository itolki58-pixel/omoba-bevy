//! Zargat, the Hell Sovereign: a demon-themed 3D overlay on the shipped
//! CC0 Crowley humanoid rig. The base rig supplies locomotion; these authored
//! armor, horn, wing and blade meshes are attached to the replicated hero root.

use bevy::prelude::*;

use crate::{
    net::{NetworkAvatar, NetworkHeroClass},
    player::Player,
    sprite::PlayerVisualMode,
};

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
}

#[derive(Component)]
struct ZargatVisual;

#[derive(Component)]
struct ZargatWing {
    rest: Quat,
    side: f32,
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
    });
}

pub(crate) fn attach_zargat_visuals(
    mut commands: Commands,
    assets: Option<Res<ZargatAssets>>,
    heroes: Query<(Entity, &NetworkAvatar, &NetworkHeroClass), (With<Player>, Without<ZargatVisual>)>,
) {
    let Some(assets) = assets else {
        return;
    };

    for (entity, avatar, hero_class) in &heroes {
        if hero_class.0 != shared::HeroClass::Warrior || avatar.0.as_deref() != Some("crowley") {
            continue;
        }

        commands.entity(entity).insert(ZargatVisual).with_children(|parent| {
            let mut part = |name: &str,
                            mesh: &Handle<Mesh>,
                            material: &Handle<StandardMaterial>,
                            position: Vec3,
                            scale: Vec3,
                            rotation: Quat| {
                parent.spawn((
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
            };

            // Dark infernal cuirass and layered shoulder plates.
            part(
                "Cuirass",
                &assets.block,
                &assets.armor,
                Vec3::new(0.0, 1.02, 0.31),
                Vec3::new(0.78, 0.72, 0.19),
                Quat::IDENTITY,
            );
            for side in [-1.0_f32, 1.0] {
                part(
                    "Pauldron",
                    &assets.sphere,
                    &assets.armor_edge,
                    Vec3::new(side * 0.49, 1.34, 0.04),
                    Vec3::new(0.43, 0.31, 0.38),
                    Quat::from_rotation_z(-side * 0.16),
                );
                part(
                    "PauldronRivet",
                    &assets.sphere,
                    &assets.gold,
                    Vec3::new(side * 0.56, 1.39, 0.34),
                    Vec3::splat(0.095),
                    Quat::IDENTITY,
                );

                // Curved-looking swept horns, built from tapered low-poly cones.
                part(
                    "Horn",
                    &assets.cone,
                    &assets.gold,
                    Vec3::new(side * 0.23, 1.88, 0.025),
                    Vec3::new(0.22, 0.58, 0.22),
                    Quat::from_rotation_z(-side * 0.34),
                );

                // Two broad bat-wing panels with animated shoulder pivots.
                let wing_rotation = Quat::from_rotation_z(side * 0.27);
                parent.spawn((
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
                part(
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
                        "WingFeather",
                        &assets.block,
                        &assets.armor,
                        Vec3::new(x, y, -0.18),
                        Vec3::new(0.30, 0.075, 0.10),
                        Quat::from_rotation_z(side * (0.22 + feather as f32 * 0.12)),
                    );
                }
            }

            // A molten heart shines through the center of the chest.
            part(
                "InfernalHeart",
                &assets.sphere,
                &assets.ember,
                Vec3::new(0.0, 1.04, 0.43),
                Vec3::new(0.19, 0.22, 0.11),
                Quat::IDENTITY,
            );

            // Oversized jagged sword on the right side: dark grip, gold guard,
            // and an emissive blade so it remains legible on a mobile display.
            let sword_rotation = Quat::from_rotation_z(-0.16);
            part(
                "Hellblade",
                &assets.block,
                &assets.ember,
                Vec3::new(0.72, 0.98, 0.36),
                Vec3::new(0.17, 0.96, 0.095),
                sword_rotation,
            );
            part(
                "BladeSpine",
                &assets.cone,
                &assets.armor_edge,
                Vec3::new(0.72, 1.50, 0.36),
                Vec3::new(0.11, 0.24, 0.11),
                Quat::from_rotation_z(std::f32::consts::PI),
            );
            part(
                "SwordGuard",
                &assets.block,
                &assets.gold,
                Vec3::new(0.72, 0.48, 0.36),
                Vec3::new(0.48, 0.10, 0.13),
                sword_rotation,
            );
            part(
                "SwordGrip",
                &assets.block,
                &assets.armor,
                Vec3::new(0.72, 0.27, 0.36),
                Vec3::new(0.13, 0.34, 0.13),
                sword_rotation,
            );

            // Small ember vents along the back suggest the character's fire-blood.
            for side in [-1.0_f32, 1.0] {
                part(
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
) {
    let wave = (time.elapsed_secs() * 2.2).sin() * 0.075;
    for (wing, mut transform) in &mut wings {
        transform.rotation = wing.rest * Quat::from_rotation_z(wing.side * wave);
    }
}
