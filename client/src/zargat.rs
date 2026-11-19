//! Zargat, the Hell Sovereign: a demon-themed 3D overlay on the shipped
//! CC0 Crowley humanoid rig. The base rig supplies locomotion; these authored
//! armor, horn, wing and blade meshes are attached to the replicated hero root.

use bevy::camera::visibility::RenderLayers;
use bevy::prelude::*;
use std::collections::HashMap;

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

/// Rest pose for the authored body pieces. These are animated as one coherent
/// silhouette until a dedicated skinned Zaragat model is integrated.
#[derive(Component)]
pub(crate) struct ZargatBodyPart {
    rest: Transform,
}

/// Procedural locomotion layer for Zaragat's authored body silhouette.
#[derive(Resource, Default)]
pub(crate) struct ZargatMotionHistory(HashMap<u64, Vec3>);

/// Marks original source-model mesh nodes after they are hidden for Zaragat.
#[derive(Component)]
pub(crate) struct ZargatBaseHidden;

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
