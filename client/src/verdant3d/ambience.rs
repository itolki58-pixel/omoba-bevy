//! Lightweight ambient fireflies make the authored jungle feel alive.
//! These are presentation-only: no collision, vision, gameplay or network state.
use bevy::{
    light::{NotShadowCaster, NotShadowReceiver},
    prelude::*,
};

use crate::maps::MapLayout;

#[cfg(target_os = "android")]
const FIREFLY_COUNT: usize = 14;
#[cfg(not(target_os = "android"))]
const FIREFLY_COUNT: usize = 24;

#[derive(Component, Clone, Copy)]
struct Firefly {
    origin: Vec3,
    phase: f32,
    orbit_radius: f32,
    orbit_speed: f32,
    bob_speed: f32,
    bob_height: f32,
}

/// Spawn one shared mesh and two shared materials; instances remain cheap on
/// mobile and are kept away from the three lane centerlines by using the
/// authored jungle block anchors.
pub(super) fn spawn(
    mut commands: Commands,
    layout: Res<MapLayout>,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
) {
    let mesh = meshes.add(Sphere::new(0.105));
    let jade = materials.add(StandardMaterial {
        base_color: Color::srgb(0.64, 0.94, 0.42),
        emissive: Color::srgb(0.78, 1.0, 0.42).into(),
        unlit: true,
        ..default()
    });
    let gold = materials.add(StandardMaterial {
        base_color: Color::srgb(1.0, 0.76, 0.34),
        emissive: Color::srgb(1.0, 0.72, 0.28).into(),
        unlit: true,
        ..default()
    });
    let blocks = layout.jungle_block_centers();

    for index in 0..FIREFLY_COUNT {
        let block = blocks[index % blocks.len()];
        let angle = index as f32 * 2.399_963_1;
        let radius = 2.8 + (index % 4) as f32 * 0.72;
        let origin = Vec3::new(
            block.x + angle.cos() * radius,
            2.1 + (index % 5) as f32 * 0.42,
            block.y + angle.sin() * radius,
        );
        commands.spawn((
            Mesh3d(mesh.clone()),
            MeshMaterial3d(if index % 4 == 0 { gold.clone() } else { jade.clone() }),
            Transform::from_translation(origin),
            Firefly {
                origin,
                phase: angle,
                orbit_radius: 0.35 + (index % 3) as f32 * 0.12,
                orbit_speed: 0.22 + (index % 5) as f32 * 0.035,
                bob_speed: 0.7 + (index % 4) as f32 * 0.11,
                bob_height: 0.16 + (index % 3) as f32 * 0.035,
            },
            NotShadowCaster,
            NotShadowReceiver,
            Name::new(format!("Verdant / firefly {index:02}")),
        ));
    }
}

/// Small deterministic orbits avoid per-frame allocations and random state.
pub(super) fn animate(time: Res<Time>, mut fireflies: Query<(&Firefly, &mut Transform)>) {
    let elapsed = time.elapsed_secs();
    for (firefly, mut transform) in &mut fireflies {
        let angle = firefly.phase + elapsed * firefly.orbit_speed;
        transform.translation = firefly.origin
            + Vec3::new(
                angle.cos() * firefly.orbit_radius,
                (elapsed * firefly.bob_speed + firefly.phase).sin() * firefly.bob_height,
                angle.sin() * firefly.orbit_radius,
            );
        let pulse = 0.82 + 0.18 * (elapsed * 1.7 + firefly.phase).sin().abs();
        transform.scale = Vec3::splat(pulse);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn app() -> App {
        let mut app = App::new();
        app.add_plugins(MinimalPlugins)
            .init_resource::<Assets<Mesh>>()
            .init_resource::<Assets<StandardMaterial>>()
            .init_resource::<MapLayout>()
            .add_systems(Startup, spawn)
            .add_systems(Update, animate);
        app
    }

    #[test]
    fn jungle_ambience_uses_a_bounded_shared_asset_budget() {
        let mut app = app();
        app.update();
        let count = app.world_mut().query::<&Firefly>().iter(app.world()).count();
        assert_eq!(count, FIREFLY_COUNT);
        assert_eq!(app.world().resource::<Assets<Mesh>>().len(), 1);
        assert_eq!(app.world().resource::<Assets<StandardMaterial>>().len(), 2);
        for transform in app.world_mut().query::<&Transform>().iter(app.world()) {
            assert!(transform.translation.is_finite());
        }
    }

    #[test]
    fn fireflies_drift_and_pulse_without_creating_new_assets() {
        let mut app = app();
        app.update();
        let entity = app.world_mut().query_filtered::<Entity, With<Firefly>>()
            .iter(app.world()).next().unwrap();
        let before = *app.world().get::<Transform>(entity).unwrap();
        app.world_mut().resource_mut::<Time>().advance_by(std::time::Duration::from_secs(2));
        app.update();
        let after = *app.world().get::<Transform>(entity).unwrap();
        assert_ne!(before.translation, after.translation);
        assert_ne!(before.scale, after.scale);
        assert_eq!(app.world().resource::<Assets<Mesh>>().len(), 1);
        assert_eq!(app.world().resource::<Assets<StandardMaterial>>().len(), 2);
    }
}
