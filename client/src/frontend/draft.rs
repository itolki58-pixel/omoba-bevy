//! Shared pre-match choices. The server owns accepted selections and lock state.
//!
//! Text comes from the `draft` dictionary (hero and position names through
//! `i18n::data`); the render key includes the locale generation. Server-authored
//! draft errors stay English.
// i18n-strict
use bevy::{prelude::*, window::PrimaryWindow};
use shared::{
    HeroClass,
    prematch::{DraftPlayer, PrematchAction, PrematchPhase, PrematchRequest, Role},
};

use super::{AppScreen, widgets};

pub(super) mod stage;
use crate::{
    i18n::{Locale, data, tr, trf},
    net::{ClientSession, GameStateSnapshot, NetworkCommand, SessionUiCommand},
    passport,
    team::{AvatarThumbnails, CharacterChoice},
    ui::{
        Activated, TestId, UiAction, UiActionAppExt, UiSet,
        action::UiActionT,
        theme::{self, ButtonKind},
        widgets::ButtonStyle,
    },
};

#[derive(SystemSet, Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub(super) enum DraftSet {
    Sync,
    Input,
    Send,
    Draw,
}

pub struct DraftScreenPlugin;
impl Plugin for DraftScreenPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<DraftClient>()
            .init_resource::<DraftScrollMemory>()
            .add_ui_action::<DraftAction>()
            .configure_sets(
                Update,
                (
                    DraftSet::Sync,
                    DraftSet::Input,
                    DraftSet::Send,
                    DraftSet::Draw,
                )
                    .chain()
                    .after(crate::net::ClientNetPipeline::ApplySnapshot),
            )
            // Draft and loading handle their typed presses in `Input`.
            .configure_sets(Update, DraftSet::Input.after(UiSet::Dispatch))
            .add_systems(Update, sync_draft.in_set(DraftSet::Sync))
            .add_systems(
                Update,
                draft_actions
                    .in_set(DraftSet::Input)
                    .run_if(in_state(AppScreen::Draft)),
            )
            .add_systems(Update, send_requests.in_set(DraftSet::Send))
            .add_systems(
                Update,
                (render_draft, update_selection_clock)
                    .chain()
                    .in_set(DraftSet::Draw)
                    .run_if(in_state(AppScreen::Draft)),
            )
            .add_systems(
                Update,
                remember_scroll
                    .after(DraftSet::Draw)
                    .after(crate::ui::UiSet::Scroll),
            );
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct Choice {
    handheld: shared::handheld::HandheldSelection,
    character: CharacterChoice,
    hero_class: HeroClass,
    avatar: Option<String>,
    sprite_character: Option<String>,
    role: Role,
}
impl Choice {
    /// A hero owns its position, avatar and signature weapon. None of these
    /// are independently selectable in the revised draft.
    fn pick_hero(&mut self, class: HeroClass) {
        let Some(hero) = shared::hero_roster::profile(class) else {
            return;
        };
        self.hero_class = class;
        self.role = hero.position;
        self.handheld = shared::handheld::HandheldSelection::ClassDefault;
        self.avatar = Some(hero.avatar.to_owned());
        self.sprite_character = Some(hero.sprite_character.to_owned());
    }
}
fn player_has_fixed_hero_identity(player: &DraftPlayer) -> bool {
    let Some(hero) = shared::hero_roster::profile(player.hero_class) else {
        return false;
    };
    player.handheld.is_default()
        && player.avatar.as_deref() == Some(hero.avatar)
        && player.sprite_character.as_deref() == Some(hero.sprite_character)
        && player.role == hero.position
}

impl From<&DraftPlayer> for Choice {
    fn from(player: &DraftPlayer) -> Self {
        let hero = shared::hero_roster::profile(player.hero_class)
            .or_else(|| shared::hero_roster::profile(HeroClass::Warrior))
            .expect("starter roster contains Zargat");
        Self {
            handheld: shared::handheld::HandheldSelection::ClassDefault,
            character: player.character,
            hero_class: hero.class,
            avatar: Some(hero.avatar.to_owned()),
            sprite_character: Some(hero.sprite_character.to_owned()),
            role: hero.position,
        }
    }
}

#[derive(Clone)]
struct PendingRequest {
    request: PrematchRequest,
    last_sent: f64,
}

#[derive(Resource, Default)]
pub(super) struct DraftClient {
    namespace: Option<(u64, u64, u64)>,
    next_request_id: u64,
    choice: Option<Choice>,
    filter: HeroFilter,
    pending: Option<PendingRequest>,
    desired_lock: Option<bool>,
    wants_loaded: bool,
    loaded_sent: bool,
    pub(super) notice: Option<String>,
    pub(super) local_assets: String,
}
impl DraftClient {
    pub(super) fn request_loaded(&mut self) {
        if !self.loaded_sent {
            self.wants_loaded = true;
        }
    }
    pub(super) fn reset(&mut self) {
        *self = Self::default();
    }
    fn begin(&mut self, action: PrematchAction, now: f64) -> Option<PrematchRequest> {
        let (server_epoch, match_id, generation) = self.namespace?;
        self.next_request_id = self.next_request_id.saturating_add(1).max(1);
        let request = PrematchRequest {
            server_epoch,
            match_id,
            generation,
            request_id: self.next_request_id,
            action,
        };
        self.pending = Some(PendingRequest {
            request: request.clone(),
            last_sent: now,
        });
        Some(request)
    }
}

fn sync_draft(
    game: Res<GameStateSnapshot>,
    mut state: ResMut<DraftClient>,
    mut selection: Option<ResMut<crate::team::TeamSelection>>,
    mut session: Option<ResMut<ClientSession>>,
) {
    let Some(draft) = &game.prematch else {
        state.reset();
        return;
    };
    let namespace = (game.meta.server_epoch, game.meta.match_id, draft.generation);
    let local = draft.players.iter().find(|p| p.player_id == game.your_id);
    if local.is_some() {
        let fixed_weapon_slot = shared::handheld::HandheldSelection::ClassDefault;
        if let Some(selection) = selection.as_mut() {
            selection.handheld = fixed_weapon_slot.clone();
        }
        if let Some(session) = session.as_mut() {
            session.remember_handheld(&fixed_weapon_slot);
        }
    }
    if state.namespace != Some(namespace) {
        state.reset();
        state.namespace = Some(namespace);
        state.next_request_id = draft.last_request_id;
        state.choice = local.map(Choice::from);
        state.notice = draft.error.clone();
    }
    let acknowledged = state
        .pending
        .as_ref()
        .is_some_and(|pending| draft.last_request_id >= pending.request.request_id);
    if acknowledged {
        state.pending = None;
        if let Some(error) = &draft.error {
            state.choice = local.map(Choice::from);
            state.desired_lock = None;
            state.notice = Some(error.clone());
        }
    }
    state.next_request_id = state.next_request_id.max(draft.last_request_id);
    if state.choice.is_none()
        || draft.phase != PrematchPhase::Draft
        || (local.is_some_and(|player| player.locked) && state.pending.is_none())
    {
        state.choice = local.map(Choice::from);
    }
    if local.is_some_and(|local| Some(local.locked) == state.desired_lock) {
        state.desired_lock = None;
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
enum HeroFilter {
    #[default]
    All,
    Gold,
    Experience,
    Center,
    Jungle,
    Support,
}
impl HeroFilter {
    fn matches(self, role: Role) -> bool {
        match self {
            Self::All => true,
            Self::Gold => role == Role::Carry,
            Self::Experience => role == Role::Solo,
            Self::Center => role == Role::Mid,
            Self::Jungle => role == Role::Jungle,
            Self::Support => role == Role::Support,
        }
    }
    fn label(self) -> &'static str {
        match self {
            Self::All => "draft.filter.all",
            Self::Gold => "draft.filter.gold",
            Self::Experience => "draft.filter.experience",
            Self::Center => "draft.filter.center",
            Self::Jungle => "draft.filter.jungle",
            Self::Support => "draft.filter.support",
        }
    }
}
#[derive(Clone, Debug, PartialEq, Eq)]
enum DraftAction {
    Hero(HeroClass),
    Filter(HeroFilter),
    Lock,
    Leave,
}

fn draft_actions(
    mut activated: MessageReader<Activated<DraftAction>>,
    game: Res<GameStateSnapshot>,
    mut state: ResMut<DraftClient>,
    mut session: MessageWriter<SessionUiCommand>,
) {
    let pressed: Vec<DraftAction> = activated.read().map(|a| a.action.clone()).collect();
    if pressed.contains(&DraftAction::Leave) {
        state.reset();
        session.write(SessionUiCommand::LeaveMatch);
        return;
    }
    let Some(draft) = &game.prematch else {
        return;
    };
    let Some(local) = draft.players.iter().find(|p| p.player_id == game.your_id) else {
        return;
    };
    for action in &pressed {
        match action {
            DraftAction::Leave => {
                state.reset();
                session.write(SessionUiCommand::LeaveMatch);
            }
            DraftAction::Lock if draft.phase == PrematchPhase::Draft => {
                state.notice = None;
                state.desired_lock = Some(!local.locked);
            }
            _ if draft.phase != PrematchPhase::Draft || local.locked => {
                state.notice = Some(tr("draft.notice.unlock_first").into());
            }
            DraftAction::Hero(class) => {
                if let Some(choice) = &mut state.choice {
                    choice.pick_hero(*class);
                }
                state.notice = None;
            }
            DraftAction::Filter(filter) => {
                state.filter = *filter;
            }
            DraftAction::Lock => {}
        }
    }
}

fn send_requests(
    game: Res<GameStateSnapshot>,
    session: Res<ClientSession>,
    time: Res<Time<Real>>,
    mut state: ResMut<DraftClient>,
    mut writer: MessageWriter<NetworkCommand>,
) {
    let Some(draft) = &game.prematch else {
        return;
    };
    if !session.is_connected() || !session.join_confirmed() {
        return;
    }
    let Some(local) = draft.players.iter().find(|p| p.player_id == game.your_id) else {
        return;
    };
    let now = time.elapsed_secs_f64();
    if let Some(pending) = &mut state.pending {
        if now - pending.last_sent >= 0.6 {
            pending.last_sent = now;
            writer.write(NetworkCommand::Prematch(pending.request.clone()));
        }
        return;
    }
    let action = if draft.phase == PrematchPhase::Loading && state.wants_loaded && !local.loaded {
        state.wants_loaded = false;
        state.loaded_sent = true;
        Some(PrematchAction::Loaded)
    } else if draft.phase == PrematchPhase::Draft {
        let choice = state.choice.clone().unwrap_or_else(|| Choice::from(local));
        let needs_select = !player_has_fixed_hero_identity(local) || choice != Choice::from(local);
        if !local.locked && needs_select {
            state.notice = None;
            Some(PrematchAction::Select {
                handheld: shared::handheld::HandheldSelection::ClassDefault,
                character: choice.character,
                hero_class: choice.hero_class,
                avatar: choice.avatar,
                sprite_character: choice.sprite_character,
                role: choice.role,
                passport_ticket: None,
            })
        } else {
            state
                .desired_lock
                .filter(|locked| *locked != local.locked)
                .map(|locked| PrematchAction::Lock { locked })
        }
    } else {
        None
    };
    if let Some(action) = action
        && let Some(request) = state.begin(action, now)
    {
        writer.write(NetworkCommand::Prematch(request));
    }
}

pub(super) fn composition_warning(players: &[DraftPlayer], local_id: u64) -> String {
    let Some(local) = players.iter().find(|p| p.player_id == local_id) else {
        return String::new();
    };
    let team: Vec<_> = players.iter().filter(|p| p.team == local.team).collect();
    let duplicate_hero = team
        .iter()
        .any(|player| player.player_id != local_id && player.hero_class == local.hero_class);
    if duplicate_hero {
        return tr("draft.warning.same_hero").into();
    }
    let same_role = team.iter().filter(|p| p.role == local.role).count();
    if same_role > 1 {
        return trf(
            "draft.warning.same_role",
            &[("count", &same_role), ("role", &data::role(local.role))],
        );
    }
    tr("draft.warning.default").into()
}

#[derive(Component)]
struct DraftRoot;
#[derive(Component, Clone, Copy)]
pub(super) struct DraftScroll(pub u8);

/// A draft or loading roster pane: wheel (24 px per notch, any unit) while
/// the cursor is over it, touch drag from the first pixel. The pane ID keys
/// the drag so it survives the pane being rebuilt under the finger.
pub(super) fn draft_pane(pane: u8) -> (DraftScroll, crate::ui::ScrollArea) {
    (
        DraftScroll(pane),
        crate::ui::ScrollArea::wheel(24.0)
            .pixel_step(24.0)
            .hover_only()
            .touch_drag(0.0)
            .keyed(u64::from(pane)),
    )
}
#[derive(Resource, Default)]
pub(super) struct DraftScrollMemory(pub std::collections::HashMap<u8, f32>);

/// A fixed-width 44 px draft/loading button: a selected tile, the primary
/// lock-in or a secondary command, with a gold edge on the first two.
pub(super) fn action_button<T: UiActionT>(
    parent: &mut ChildSpawnerCommands,
    label: &str,
    action: T,
    name: &str,
    width: f32,
    primary: bool,
    selected: bool,
) {
    let style = if selected {
        ButtonStyle {
            kind: ButtonKind::Tile,
            selected: true,
        }
    } else {
        ButtonStyle::new(if primary {
            ButtonKind::Primary
        } else {
            ButtonKind::Secondary
        })
    };
    parent
        .spawn((
            Button,
            Node {
                width: Val::Px(width),
                min_width: Val::Px(width),
                height: Val::Px(44.0),
                min_height: Val::Px(44.0),
                flex_shrink: 0.0,
                justify_content: JustifyContent::Center,
                align_items: AlignItems::Center,
                padding: UiRect::axes(Val::Px(5.0), Val::Px(4.0)),
                border: UiRect::all(Val::Px(1.0)),
                border_radius: BorderRadius::all(Val::Px(6.0)),
                ..default()
            },
            BackgroundColor(style.idle_color()),
            BorderColor::all(if primary || selected {
                theme::GOLD
            } else {
                theme::PANEL_EDGE
            }),
            style,
            UiAction(action),
            TestId::new(name.to_owned()),
        ))
        .with_children(|button| {
            button.spawn(widgets::label(label, if width < 82.0 { 10.0 } else { 13.0 }, theme::IVORY));
        });
}

fn hero_card(
    parent: &mut ChildSpawnerCommands,
    hero: &shared::hero_roster::HeroRosterEntry,
    image: Option<Handle<Image>>,
    width: f32,
    selected: bool,
) {
    parent
        .spawn((
            Button,
            Node {
                width: Val::Px(width),
                min_width: Val::Px(width),
                height: Val::Px(116.0),
                min_height: Val::Px(116.0),
                flex_shrink: 0.0,
                flex_direction: FlexDirection::Column,
                justify_content: JustifyContent::Center,
                align_items: AlignItems::Center,
                row_gap: Val::Px(5.0),
                padding: UiRect::all(Val::Px(5.0)),
                border: UiRect::all(Val::Px(2.0)),
                border_radius: BorderRadius::all(Val::Px(8.0)),
                ..default()
            },
            BackgroundColor(if selected { theme::TILE_SELECTED } else { theme::PANEL_OPAQUE }),
            BorderColor::all(if selected { theme::GOLD } else { theme::PANEL_EDGE }),
            ButtonStyle { kind: ButtonKind::Tile, selected },
            UiAction(DraftAction::Hero(hero.class)),
            TestId::new(format!("DraftHero-{}", hero.class.id())),
            Name::new(format!("HeroCard-{}", hero.class.id())),
        ))
        .with_children(|card| {
            if let Some(image) = image {
                card.spawn((
                    ImageNode::new(image),
                    Node {
                        width: Val::Px(70.0),
                        height: Val::Px(76.0),
                        flex_shrink: 0.0,
                        ..default()
                    },
                ));
            } else {
                card.spawn((
                    Node {
                        width: Val::Px(70.0),
                        height: Val::Px(76.0),
                        flex_shrink: 0.0,
                        border_radius: BorderRadius::all(Val::Px(6.0)),
                        ..default()
                    },
                    BackgroundColor(theme::PANEL_EDGE),
                ));
            }
            card.spawn(widgets::label(data::hero_name(hero.class), 12.0, theme::IVORY));
        });
}

pub(super) fn roster_row(
    parent: &mut ChildSpawnerCommands,
    player: &DraftPlayer,
    your_id: u64,
    thumbnails: &AvatarThumbnails,
    loading: bool,
    compact: bool,
) {
    let mine = player.player_id == your_id;
    parent
        .spawn((
            Node {
                width: Val::Percent(100.0),
                min_height: Val::Px(if compact { 60.0 } else { 72.0 }),
                flex_shrink: 0.0,
                align_items: AlignItems::Center,
                column_gap: Val::Px(8.0),
                padding: UiRect::all(Val::Px(6.0)),
                border: UiRect::all(Val::Px(1.0)),
                border_radius: BorderRadius::all(Val::Px(6.0)),
                ..default()
            },
            BackgroundColor(if mine {
                theme::TILE_SELECTED
            } else {
                theme::PANEL_OPAQUE
            }),
            BorderColor::all(if mine { theme::GOLD } else { theme::PANEL_EDGE }),
            Name::new(format!("DraftPlayer-{}", player.player_id)),
        ))
        .with_children(|row| {
            if let Some(image) = player
                .avatar
                .as_ref()
                .and_then(|slug| thumbnails.0.get(slug))
            {
                row.spawn((
                    ImageNode::new(image.clone()),
                    Node {
                        width: Val::Px(40.0),
                        height: Val::Px(40.0),
                        flex_shrink: 0.0,
                        ..default()
                    },
                ));
            }
            row.spawn(Node {
                flex_direction: FlexDirection::Column,
                flex_grow: 1.0,
                min_width: Val::Px(0.0),
                overflow: Overflow::clip(),
                row_gap: Val::Px(2.0),
                ..default()
            })
            .with_children(|text| {
                let identity = format!(
                    "{}{}{}",
                    player.nickname,
                    if mine { tr("draft.roster.you") } else { "" },
                    if player.is_bot {
                        tr("draft.roster.bot")
                    } else {
                        ""
                    }
                );
                text.spawn((
                    widgets::label(&identity, 13.0, theme::IVORY),
                    TextLayout::justify(Justify::Left).with_linebreak(LineBreak::NoWrap),
                ));
                text.spawn(widgets::label(
                    &trf(
                        "draft.roster.class_role",
                        &[
                            ("hero", &data::hero_name(player.hero_class)),
                            ("role", &data::role(player.role)),
                        ],
                    ),
                    12.0,
                    theme::GOLD,
                ));

            });
            row.spawn(widgets::label(
                if loading {
                    if player.loaded {
                        tr("draft.roster.ready")
                    } else {
                        tr("draft.roster.loading")
                    }
                } else if player.locked {
                    tr("draft.roster.locked")
                } else {
                    tr("draft.roster.picking")
                },
                10.0,
                if player.loaded || (!loading && player.locked) {
                    crate::ui::theme::JADE
                } else {
                    theme::MUTED
                },
            ));
        });
}

fn render_draft(
    mut commands: Commands,
    game: Res<GameStateSnapshot>,
    state: Res<DraftClient>,
    windows: Query<&Window, With<PrimaryWindow>>,
    roots: Query<Entity, With<DraftRoot>>,
    mut thumbnails: ResMut<AvatarThumbnails>,
    assets: Res<AssetServer>,
    scroll: Res<DraftScrollMemory>,
    locale: Option<Res<Locale>>,
    mut party_stage: Option<ResMut<super::party_stage::PartyStage>>,
    mut last: Local<String>,
) {
    let Ok(window) = windows.single() else {
        return;
    };
    let Some(draft) = &game.prematch else {
        return;
    };
    if let Some(stage) = party_stage.as_mut() {
        let mut preview_roster = draft.clone();
        if let (Some(choice), Some(local)) = (
            state.choice.as_ref(),
            preview_roster
                .players
                .iter_mut()
                .find(|p| p.player_id == game.your_id && !p.locked),
        ) {
            local.avatar = choice.avatar.clone();
            local.hero_class = choice.hero_class;
            local.handheld = choice.handheld.clone();
        }
        stage::sync_members(stage, &preview_roster, game.your_id);
    }
    // A ticking server clock must not tear down an active picker/drag.
    let mut render_snapshot = draft.clone();
    render_snapshot.remaining_ms = 0;
    let key = format!(
        "{}:{:?}:{:?}:{:?}:{}:{}:{}",
        serde_json::to_string(&render_snapshot).unwrap_or_default(),
        state.choice,
        state.desired_lock,
        state.notice,
        state.pending.is_some(),
        state.filter,
        window.width(),
        window.height()
    );
    let key = format!(
        "{key}:{}",
        locale.as_ref().map_or(0, |locale| locale.generation())
    );
    if *last == key && !roots.is_empty() {
        return;
    }
    *last = key;
    for root in &roots {
        commands.entity(root).despawn();
    }
    for hero in shared::hero_roster::STARTER_ROSTER {
        if let Some(avatar) = omoba_passport::avatars::avatar_definition(hero.avatar)
            && let Some(path) = crate::passport::thumbnail_asset_path(avatar)
        {
            thumbnails
                .0
                .insert(hero.avatar.to_owned(), assets.load(path));
        }
    }
    let vertical = window.width() < 720.0;
    let compact = window.height() < 500.0 || vertical;
    let side = if compact { 12.0 } else { 28.0 };
    let available = (window.width() - side * 2.0).max(180.0);
    let roster_width = if vertical { available } else {
        (available * if compact { 0.43 } else { 0.48 }).min(740.0)
    };
    let picker_width = if vertical { available } else { available - roster_width - 12.0 };
    let local = draft.players.iter().find(|p| p.player_id == game.your_id);
    let choice = state.choice.as_ref();
    let locked = local.is_some_and(|p| p.locked);
    let message = state
        .notice
        .clone()
        .unwrap_or_else(|| composition_warning(&draft.players, game.your_id));
    commands
        .spawn((
            Node {
                position_type: PositionType::Absolute,
                left: Val::Px(0.0),
                right: Val::Px(0.0),
                top: Val::Px(0.0),
                bottom: Val::Px(0.0),
                flex_direction: FlexDirection::Column,
                padding: UiRect {
                    left: Val::Px(side),
                    right: Val::Px(side),
                    top: Val::Px(if compact { 12.0 } else { 24.0 }),
                    bottom: Val::Px(if compact { 20.0 } else { 24.0 }),
                },
                row_gap: Val::Px(8.0),
                ..default()
            },
            BackgroundColor(theme::BACKDROP),
            ZIndex(theme::SCREEN_Z),
            DespawnOnExit(AppScreen::Draft),
            DraftRoot,
            Name::new("DraftScreen"),
        ))
        .with_children(|root| {
            root.spawn(Node {
                height: Val::Px(44.0),
                min_height: Val::Px(44.0),
                justify_content: JustifyContent::SpaceBetween,
                align_items: AlignItems::Center,
                ..default()
            })
            .with_children(|header| {
                header
                    .spawn(Node {
                        flex_direction: FlexDirection::Column,
                        min_width: Val::Px(0.0),
                        max_width: Val::Px(((available - 180.0) * 0.5).max(120.0)),
                        overflow: Overflow::clip(),
                        ..default()
                    })
                    .with_children(|title| {
                        title.spawn(widgets::heading(
                            tr("draft.title"),
                            if compact { 20.0 } else { 28.0 },
                        ));
                        title.spawn((
                            widgets::label(tr("draft.subtitle"), 12.0, theme::MUTED),
                            TextLayout::justify(Justify::Left).with_linebreak(LineBreak::NoWrap),
                        ));
                    });
                header.spawn((
                    widgets::label("", if compact { 17.0 } else { 23.0 }, theme::GOLD),
                    SelectionClock,
                    Node {
                        position_type: PositionType::Absolute,
                        left: Val::Percent(50.0),
                        width: Val::Px(160.0),
                        margin: UiRect::left(Val::Px(-80.0)),
                        ..default()
                    },
                    TextLayout::justify(Justify::Center).with_linebreak(LineBreak::NoWrap),
                    Name::new("DraftSelectionClock"),
                ));
                action_button(
                    header,
                    tr("common.cancel"),
                    DraftAction::Leave,
                    "DraftCancel",
                    86.0,
                    false,
                    false,
                );
            });
            root.spawn(Node {
                flex_grow: 1.0,
                min_height: Val::Px(0.0),
                flex_direction: if vertical { FlexDirection::Column } else { FlexDirection::Row },
                row_gap: Val::Px(if vertical { 8.0 } else { 0.0 }),
                column_gap: Val::Px(12.0),
                ..default()
            })
            .with_children(|body| {
                body.spawn(Node {
                    width: if vertical { Val::Percent(100.0) } else { Val::Px(roster_width) },
                    min_width: if vertical { Val::Percent(100.0) } else { Val::Px(roster_width) },
                    height: if vertical { Val::Px(142.0) } else { Val::Percent(100.0) },
                    min_height: if vertical { Val::Px(142.0) } else { Val::Px(0.0) },
                    flex_shrink: 0.0,
                    ..default()
                })
                .with_children(|roster| {
                    stage::spawn_team_stage(
                        roster,
                        draft,
                        game.your_id,
                        party_stage.as_deref(),
                        roster_width,
                        if vertical { 132.0 } else {
                            (window.height() - if compact { 136.0 } else { 152.0 }).max(180.0)
                        },
                        false,
                        compact,
                    );
                });
                body.spawn((
                    Node {
                        flex_grow: 1.0,
                        width: if vertical { Val::Percent(100.0) } else { Val::Auto },
                        min_width: Val::Px(0.0),
                        flex_direction: FlexDirection::Column,
                        row_gap: Val::Px(7.0),
                        min_height: Val::Px(0.0),
                        overflow: Overflow::scroll_y(),
                        ..default()
                    },
                    ScrollPosition(Vec2::new(0.0, *scroll.0.get(&3).unwrap_or(&0.0))),
                    draft_pane(3),
                    Name::new("DraftPicker"),
                ))
                .with_children(|picker| {
                    picker.spawn(widgets::label(tr("draft.avatars.included"), 12.0, theme::GOLD));
                    picker
                        .spawn(Node {
                            width: Val::Percent(100.0),
                            flex_direction: FlexDirection::Row,
                            flex_wrap: FlexWrap::Wrap,
                            column_gap: Val::Px(4.0),
                            row_gap: Val::Px(4.0),
                            ..default()
                        })
                        .with_children(|tabs| {
                            let tab_width = if picker_width < 420.0 {
                                ((picker_width - 8.0) / 3.0).max(40.0)
                            } else {
                                ((picker_width - 20.0) / 6.0).max(52.0)
                            };
                            for filter in [
                                HeroFilter::All,
                                HeroFilter::Gold,
                                HeroFilter::Experience,
                                HeroFilter::Center,
                                HeroFilter::Jungle,
                                HeroFilter::Support,
                            ] {
                                action_button(
                                    tabs,
                                    tr(filter.label()),
                                    DraftAction::Filter(filter),
                                    filter.label(),
                                    tab_width,
                                    false,
                                    state.filter == filter,
                                );
                            }
                        });
                    let columns = if picker_width >= 430.0 { 3.0 } else { 2.0 };
                    let gap = 7.0;
                    let card_width = ((picker_width - gap * (columns - 1.0)) / columns).max(58.0);
                    picker
                        .spawn(Node {
                            width: Val::Percent(100.0),
                            flex_direction: FlexDirection::Row,
                            flex_wrap: FlexWrap::Wrap,
                            column_gap: Val::Px(gap),
                            row_gap: Val::Px(gap),
                            align_content: AlignContent::FlexStart,
                            ..default()
                        })
                        .with_children(|heroes| {
                            for hero in shared::hero_roster::STARTER_ROSTER
                                .iter()
                                .filter(|hero| state.filter.matches(hero.position))
                            {
                                let image = thumbnails.0.get(hero.avatar).cloned();
                                hero_card(
                                    heroes,
                                    hero,
                                    image,
                                    card_width,
                                    choice.is_some_and(|selected| selected.hero_class == hero.class),
                                );
                            }
                        });
                });
            });
            root.spawn(Node {
                min_height: Val::Px(44.0),
                height: Val::Px(44.0),
                align_items: AlignItems::Center,
                justify_content: JustifyContent::SpaceBetween,
                column_gap: Val::Px(12.0),
                ..default()
            })
            .with_children(|footer| {
                footer.spawn((
                    widgets::label(
                        &message,
                        12.0,
                        if state.notice.is_some() {
                            theme::GOLD
                        } else {
                            theme::MUTED
                        },
                    ),
                    Node {
                        flex_grow: 1.0,
                        min_width: Val::Px(0.0),
                        max_height: Val::Px(44.0),
                        overflow: Overflow::clip(),
                        ..default()
                    },
                    Name::new("DraftNotice"),
                ));
                action_button(
                    footer,
                    if state.pending.is_some() {
                        tr("draft.button.syncing")
                    } else if locked {
                        tr("draft.button.unlock")
                    } else {
                        tr("draft.button.lock_in")
                    },
                    DraftAction::Lock,
                    "DraftLock",
                    132.0,
                    !locked,
                    false,
                );
            });
        });
}

#[derive(Component)]
struct SelectionClock;

fn update_selection_clock(
    game: Res<GameStateSnapshot>,
    mut clocks: Query<&mut Text, With<SelectionClock>>,
) {
    let Some(draft) = &game.prematch else {
        return;
    };
    let value = if draft.remaining_ms == 0 {
        tr("draft.timer.gathering").to_owned()
    } else {
        trf(
            "draft.timer.remaining",
            &[("seconds", &draft.remaining_ms.div_ceil(1000))],
        )
    };
    for mut text in &mut clocks {
        if text.0 != value {
            text.0.clone_from(&value);
        }
    }
}

/// Rebuilt panes reopen at the offset they had (`render_draft` and the
/// loading screen read the memory); `ui::scroll` moves them.
fn remember_scroll(
    screen: Res<State<AppScreen>>,
    panels: Query<(&DraftScroll, &ComputedNode, &ScrollPosition)>,
    mut memory: ResMut<DraftScrollMemory>,
) {
    if !matches!(screen.get(), AppScreen::Draft | AppScreen::Loading) {
        return;
    }
    for (pane, node, position) in &panels {
        // Rebuilt panels keep their stable pane ID but have no measured size
        // until layout runs; keep the saved offset until then.
        if node.size().min_element() <= 0.0 {
            continue;
        }
        let offset = position.y.clamp(0.0, crate::ui::scroll::max_offset(node));
        if memory.0.get(&pane.0) != Some(&offset) {
            memory.0.insert(pane.0, offset);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::persistence::ClientSessionId;
    use bevy::input::touch::{TouchInput, TouchPhase};

    #[test]
    fn scroll_gesture_survives_panel_replacement_and_unmeasured_rebuild_frame() {
        let mut app = App::new();
        app.insert_resource(State::new(AppScreen::Loading))
            .init_resource::<DraftScrollMemory>()
            .add_message::<TouchInput>()
            .add_systems(
                Update,
                (crate::ui::scroll::scroll_areas, remember_scroll).chain(),
            );
        let window = app
            .world_mut()
            .spawn((Window::default(), PrimaryWindow))
            .id();
        let measured = || ComputedNode {
            size: Vec2::new(200.0, 100.0),
            content_size: Vec2::new(200.0, 600.0),
            inverse_scale_factor: 1.0,
            ..default()
        };
        let old_panel = app
            .world_mut()
            .spawn((
                draft_pane(2),
                measured(),
                UiGlobalTransform::default(),
                ScrollPosition::default(),
            ))
            .id();
        for (phase, y) in [(TouchPhase::Started, 20.0), (TouchPhase::Moved, -10.0)] {
            app.world_mut().write_message(TouchInput {
                id: 5,
                phase,
                position: Vec2::new(0.0, y),
                window,
                force: None,
            });
        }
        app.update();
        assert_eq!(
            app.world().get::<ScrollPosition>(old_panel).unwrap().0.y,
            30.0
        );
        app.world_mut().despawn(old_panel);
        let new_panel = app
            .world_mut()
            .spawn((
                draft_pane(2),
                ComputedNode::default(),
                UiGlobalTransform::default(),
                ScrollPosition(Vec2::new(0.0, 30.0)),
            ))
            .id();
        app.world_mut().write_message(TouchInput {
            id: 5,
            phase: TouchPhase::Moved,
            position: Vec2::new(0.0, -30.0),
            window,
            force: None,
        });
        app.update();
        assert_eq!(app.world().resource::<DraftScrollMemory>().0[&2], 30.0);
        app.world_mut().entity_mut(new_panel).insert(measured());
        app.world_mut().write_message(TouchInput {
            id: 5,
            phase: TouchPhase::Moved,
            position: Vec2::new(0.0, -60.0),
            window,
            force: None,
        });
        app.update();
        assert_eq!(
            app.world().get::<ScrollPosition>(new_panel).unwrap().0.y,
            80.0
        );
        assert_eq!(app.world().resource::<DraftScrollMemory>().0[&2], 80.0);
        app.world_mut().write_message(TouchInput {
            id: 5,
            phase: TouchPhase::Ended,
            position: Vec2::new(0.0, -60.0),
            window,
            force: None,
        });
        app.update();
        app.world_mut().write_message(TouchInput {
            id: 6,
            phase: TouchPhase::Started,
            position: Vec2::new(0.0, 20.0),
            window,
            force: None,
        });
        app.world_mut().write_message(TouchInput {
            id: 6,
            phase: TouchPhase::Moved,
            position: Vec2::new(0.0, 10.0),
            window,
            force: None,
        });
        app.update();
        assert_eq!(
            app.world().get::<ScrollPosition>(new_panel).unwrap().0.y,
            90.0
        );
    }

    fn request_app() -> App {
        let mut app = App::new();
        let mut game = GameStateSnapshot {
            your_id: 7,
            ..default()
        };
        game.meta.server_epoch = 10;
        game.meta.match_id = 3;
        game.prematch = Some(shared::prematch::PrematchSnapshot {
            generation: 4,
            phase: PrematchPhase::Draft,
            remaining_ms: 0,
            needed: 1,
            last_request_id: 0,
            error: None,
            players: vec![DraftPlayer {
                handheld: Default::default(),
                player_id: 7,
                nickname: "Local".into(),
                team: shared::map::Team::Green,
                character: CharacterChoice::default(),
                hero_class: HeroClass::Warrior,
                avatar: None,
                sprite_character: None,
                role: Role::Solo,
                is_bot: false,
                locked: false,
                loaded: false,
            }],
        });
        app.insert_resource(game)
            .insert_resource(ClientSession::admitted_for_test())
            .init_resource::<DraftClient>()
            .init_resource::<ClientSessionId>()
            .init_resource::<Time<Real>>()
            .add_message::<NetworkCommand>()
            .add_systems(Update, (sync_draft, send_requests).chain());
        app.update();
        app
    }

    fn drain_requests(app: &mut App) -> Vec<PrematchRequest> {
        app.world_mut()
            .resource_mut::<Messages<NetworkCommand>>()
            .drain()
            .filter_map(|command| {
                if let NetworkCommand::Prematch(request) = command {
                    Some(request)
                } else {
                    None
                }
            })
            .collect()
    }

    /// Every prematch request the app has sent, in the order it sent them.
    ///
    /// A test that drives several updates must not look for a request in
    /// `Messages<NetworkCommand>` afterwards. With `TimePlugin` in the app Bevy
    /// swaps the message buffers after a fixed-timestep tick, so how many updates
    /// a message survives depends on how long those updates took, and a loaded
    /// machine drops it before the test looks. The game reads the messages every
    /// frame; so does this recorder.
    #[derive(Resource, Default)]
    struct SentRequests(Vec<PrematchRequest>);

    fn record_requests(
        mut commands: MessageReader<NetworkCommand>,
        mut sent: ResMut<SentRequests>,
    ) {
        for command in commands.read() {
            if let NetworkCommand::Prematch(request) = command {
                sent.0.push(request.clone());
            }
        }
    }

    #[test]
    fn phone_hero_picker_has_visible_tiles_and_raw_taps_select_fixed_heroes() {
        use bevy::camera::{ComputedCameraValues, RenderTargetInfo};
        use bevy::input::touch::{TouchInput, TouchPhase};
        let mut app = request_app();
        app.add_plugins((
            MinimalPlugins,
            bevy::asset::AssetPlugin::default(),
            bevy::image::ImagePlugin::default(),
            bevy::text::TextPlugin,
            bevy::transform::TransformPlugin,
            bevy::input::InputPlugin,
            bevy::ui::UiPlugin,
            bevy::camera::visibility::VisibilityPlugin,
            bevy::picking::PickingPlugin,
            bevy::picking::InteractionPlugin,
        ))
        .init_resource::<Assets<bevy::mesh::Mesh>>()
        .init_resource::<Assets<bevy::mesh::skinning::SkinnedMeshInverseBindposes>>()
        .init_resource::<Assets<TextureAtlasLayout>>()
        .init_resource::<DraftScrollMemory>()
        .init_resource::<AvatarThumbnails>()
        .insert_resource(crate::ui::UiPlatform(crate::platform::UiProfile::Mobile))
        .init_resource::<crate::ui::GestureEpoch>()
        .init_resource::<SentRequests>()
        .add_message::<SessionUiCommand>()
        .add_ui_action::<DraftAction>()
        .add_systems(Update, record_requests.after(send_requests))
        .add_systems(
            Update,
            crate::ui::gesture::recognize_presses.before(UiSet::Dispatch),
        )
        .add_systems(
            Update,
            draft_actions
                .after(UiSet::Dispatch)
                .after(sync_draft)
                .before(send_requests),
        )
        .add_systems(
            Update,
            (render_draft, update_selection_clock)
                .chain()
                .after(draft_actions),
        );
        let mut window = Window {
            focused: true,
            ..default()
        };
        window.resolution.set_scale_factor_override(Some(1.0));
        window.resolution.set(852.0, 393.0);
        let window = app.world_mut().spawn((window, PrimaryWindow)).id();
        app.world_mut().spawn((
            Camera2d,
            Camera {
                computed: ComputedCameraValues {
                    target_info: Some(RenderTargetInfo {
                        physical_size: UVec2::new(852, 393),
                        scale_factor: 1.0,
                    }),
                    ..default()
                },
                ..default()
            },
        ));
        app.finish();
        app.cleanup();
        for _ in 0..5 {
            app.update();
        }
        let tap = |app: &mut App, id: &str| {
            let button = crate::ui::test_id::harness::find(app.world_mut(), id).unwrap();
            let node = app.world().get::<ComputedNode>(button).unwrap();
            let transform = app.world().get::<UiGlobalTransform>(button).unwrap();
            let rect = crate::ui::gesture::logical_ui_rect(
                node,
                transform,
                app.world().get::<bevy::ui::CalculatedClip>(button),
                1.0,
            );
            assert!(
                rect.width() >= 40.0 && rect.height() >= 40.0,
                "clipped {id}: {rect:?}"
            );
            assert!(rect.min.y >= 0.0 && rect.max.y <= 393.0);
            let position = rect.center();
            for phase in [TouchPhase::Started, TouchPhase::Ended] {
                app.world_mut().write_message(TouchInput {
                    window,
                    id: 77,
                    phase,
                    position,
                    force: None,
                });
                app.update();
            }
            for _ in 0..3 {
                app.update();
            }
        };
        let clock = app
            .world_mut()
            .query::<(Entity, &Name)>()
            .iter(app.world())
            .find(|(_, name)| name.as_str() == "DraftSelectionClock")
            .unwrap()
            .0;
        let center = app
            .world()
            .get::<UiGlobalTransform>(clock)
            .unwrap()
            .translation
            .x;
        assert!((center - 426.0).abs() <= 0.5, "draft clock at {center}");
        assert!(!app.world().get::<Text>(clock).unwrap().0.is_empty());
        assert!(crate::ui::test_id::harness::find(app.world_mut(), "DraftHero-mage").is_some());
        tap(&mut app, "DraftHero-mage");
        let choice = app.world().resource::<DraftClient>().choice.as_ref().unwrap();
        assert_eq!(choice.hero_class, HeroClass::Mage);
        assert_eq!(choice.avatar.as_deref(), Some("anna"));
        assert_eq!(choice.sprite_character.as_deref(), Some("clockwork-turnip-oracle"));
        assert_eq!(choice.role, Role::Mid);
        assert_eq!(choice.handheld, shared::handheld::HandheldSelection::ClassDefault);
        let sent = &app.world().resource::<SentRequests>().0;
        assert!(
            sent.iter().any(|request| matches!(
                &request.action,
                PrematchAction::Select {
                    hero_class: HeroClass::Mage,
                    avatar: Some(avatar),
                    role: Role::Mid,
                    handheld: shared::handheld::HandheldSelection::ClassDefault,
                    ..
                } if avatar == "anna"
            )),
            "no canonical hero Select request among the {} requests sent",
            sent.len()
        );
    }

    #[test]
    fn picking_a_hero_always_assigns_its_fixed_position_avatar_and_weapon() {
        let mut choice = Choice {
            handheld: Default::default(),
            character: CharacterChoice::default(),
            hero_class: HeroClass::Mage,
            avatar: None,
            sprite_character: None,
            role: Role::Mid,
        };
        choice.pick_hero(HeroClass::Warden);
        assert_eq!(choice.role, Role::Jungle);
        assert_eq!(choice.avatar.as_deref(), Some("sport-mecha"));
        assert_eq!(choice.sprite_character.as_deref(), Some("cathedral-moth-bellringer"));
        assert_eq!(choice.handheld, shared::handheld::HandheldSelection::ClassDefault);

        // A previously selected position or avatar cannot override the hero profile.
        choice.role = Role::Support;
        choice.avatar = Some("not-a-roster-avatar".into());
        choice.pick_hero(HeroClass::Warrior);
        assert_eq!((choice.hero_class, choice.role), (HeroClass::Warrior, Role::Solo));
        assert_eq!(choice.avatar.as_deref(), Some("crowley"));
        assert_eq!(choice.sprite_character.as_deref(), Some("mossback-teapot"));
        assert_eq!(choice.handheld, shared::handheld::HandheldSelection::ClassDefault);
    }

    #[test]
    fn choice_retries_keep_the_same_id_and_rejection_restores_accepted_selection() {
        let mut app = request_app();
        app.world_mut()
            .resource_mut::<DraftClient>()
            .choice
            .as_mut()
            .unwrap()
            .hero_class = HeroClass::Mage;
        app.update();
        let sent = drain_requests(&mut app);
        assert_eq!(sent.len(), 1);
        assert_eq!(
            (sent[0].server_epoch, sent[0].match_id, sent[0].generation),
            (10, 3, 4)
        );
        app.world_mut()
            .resource_mut::<Time<Real>>()
            .advance_by(std::time::Duration::from_millis(650));
        app.update();
        let retried = drain_requests(&mut app);
        assert_eq!(retried.len(), 1);
        assert_eq!(
            serde_json::to_string(&sent[0]).unwrap(),
            serde_json::to_string(&retried[0]).unwrap()
        );
        {
            let mut game = app.world_mut().resource_mut::<GameStateSnapshot>();
            let draft = game.prematch.as_mut().unwrap();
            draft.last_request_id = sent[0].request_id;
            draft.error = Some("Selection unavailable".into());
        }
        app.update();
        let state = app.world().resource::<DraftClient>();
        assert_eq!(
            state.choice.as_ref().unwrap().hero_class,
            HeroClass::Warrior
        );
        assert_eq!(state.notice.as_deref(), Some("Selection unavailable"));
        assert!(state.pending.is_none());
        assert!(drain_requests(&mut app).is_empty());
    }

    #[test]
    fn namespace_change_cancels_inflight_choice_and_loading_ack_waits_for_loading_phase() {
        let mut app = request_app();
        app.world_mut()
            .resource_mut::<DraftClient>()
            .choice
            .as_mut()
            .unwrap()
            .role = Role::Jungle;
        app.update();
        assert_eq!(drain_requests(&mut app).len(), 1);
        app.world_mut()
            .resource_mut::<GameStateSnapshot>()
            .prematch
            .as_mut()
            .unwrap()
            .generation += 1;
        app.update();
        assert!(app.world().resource::<DraftClient>().pending.is_none());
        assert_eq!(
            app.world()
                .resource::<DraftClient>()
                .choice
                .as_ref()
                .unwrap()
                .role,
            Role::Mid
        );
        assert!(drain_requests(&mut app).is_empty());
        app.world_mut()
            .resource_mut::<GameStateSnapshot>()
            .prematch
            .as_mut()
            .unwrap()
            .phase = PrematchPhase::Countdown;
        app.world_mut()
            .resource_mut::<DraftClient>()
            .request_loaded();
        app.update();
        assert!(drain_requests(&mut app).is_empty());
        app.world_mut()
            .resource_mut::<GameStateSnapshot>()
            .prematch
            .as_mut()
            .unwrap()
            .phase = PrematchPhase::Loading;
        app.update();
        let requests = drain_requests(&mut app);
        assert_eq!(requests.len(), 1);
        assert!(matches!(requests[0].action, PrematchAction::Loaded));
    }

    #[test]
    fn repeated_request_keeps_identity_and_new_generation_discards_old_work() {
        let mut state = DraftClient {
            namespace: Some((7, 3, 2)),
            next_request_id: 9,
            ..default()
        };
        let request = state
            .begin(PrematchAction::Lock { locked: true }, 1.0)
            .unwrap();
        assert_eq!(
            (
                request.server_epoch,
                request.match_id,
                request.generation,
                request.request_id
            ),
            (7, 3, 2, 10)
        );
        let retry = state.pending.as_ref().unwrap().request.clone();
        assert_eq!(
            serde_json::to_string(&request).unwrap(),
            serde_json::to_string(&retry).unwrap()
        );
        state.reset();
        assert!(state.pending.is_none() && state.namespace.is_none() && !state.wants_loaded);
    }
    #[test]
    fn composition_warnings_are_advisory_and_do_not_impose_class_uniqueness() {
        let player = |id| DraftPlayer {
            handheld: Default::default(),
            player_id: id,
            nickname: format!("P{id}"),
            team: shared::map::Team::Green,
            character: CharacterChoice::default(),
            hero_class: HeroClass::Warrior,
            avatar: Some("agnes".into()),
            sprite_character: None,
            role: Role::Jungle,
            is_bot: false,
            locked: false,
            loaded: false,
        };
        let mut players = vec![player(1), player(2)];
        assert!(composition_warning(&players, 1).contains("same hero"));
        players[1].hero_class = HeroClass::Mage;
        players[1].avatar = Some("anna".into());
        assert!(composition_warning(&players, 1).contains("Jungle"));
        players[1].role = Role::Support;
        assert!(!composition_warning(&players, 1).contains("Jungle"));
    }

    /// The draft is a render-key screen: a language change redraws it in the
    /// new language, while its TestIds keep their English ids.
    #[test]
    fn a_language_change_redraws_the_draft_and_keeps_its_ids() {
        if crate::i18n::testing::isolated(
            "frontend::draft::tests::a_language_change_redraws_the_draft_and_keeps_its_ids",
        ) {
            return;
        }
        use crate::i18n::{I18nPlugin, LocaleId};
        let mut game = GameStateSnapshot {
            your_id: 7,
            ..default()
        };
        game.prematch = Some(shared::prematch::PrematchSnapshot {
            generation: 1,
            phase: PrematchPhase::Draft,
            remaining_ms: 0,
            needed: 10,
            last_request_id: 0,
            error: None,
            players: vec![DraftPlayer {
                handheld: Default::default(),
                player_id: 7,
                nickname: "Local".into(),
                team: shared::map::Team::Green,
                character: CharacterChoice::default(),
                hero_class: HeroClass::Warrior,
                avatar: None,
                sprite_character: None,
                role: Role::Solo,
                is_bot: false,
                locked: false,
                loaded: false,
            }],
        });
        let mut app = App::new();
        app.add_plugins((
            bevy::app::TaskPoolPlugin::default(),
            bevy::asset::AssetPlugin::default(),
            I18nPlugin::default(),
        ))
        .init_asset::<Image>()
        .insert_resource(game)
        .init_resource::<DraftClient>()
        .init_resource::<DraftScrollMemory>()
        .init_resource::<AvatarThumbnails>()
        .add_systems(Update, render_draft);
        app.world_mut().spawn((Window::default(), PrimaryWindow));
        app.update();
        let label = |app: &mut App, id: &str| {
            let button = crate::ui::test_id::harness::find(app.world_mut(), id)
                .unwrap_or_else(|| panic!("no {id}"));
            let child = app.world().get::<Children>(button).unwrap()[0];
            app.world().get::<Text>(child).unwrap().0.clone()
        };
        let texts = |app: &mut App| -> Vec<String> {
            app.world_mut()
                .query::<&Text>()
                .iter(app.world())
                .map(|text| text.0.clone())
                .collect()
        };
        assert_eq!(label(&mut app, "DraftLock"), "Lock in");
        assert!(
            texts(&mut app)
                .iter()
                .any(|text| text == "Assemble your team")
        );
        let plate_texts = |app: &mut App| -> Vec<String> {
            let plate = app
                .world_mut()
                .query::<(Entity, &Name)>()
                .iter(app.world())
                .find(|(_, name)| name.as_str() == "PrematchStagePlayer-7")
                .map(|(entity, _)| entity)
                .expect("local identity plate");
            app.world()
                .get::<Children>(plate)
                .unwrap()
                .iter()
                .filter_map(|entity| app.world().get::<Text>(entity).map(|text| text.0.clone()))
                .collect()
        };
        assert_eq!(
            plate_texts(&mut app),
            ["Local · YOU", "Zargat", "EXP", "PICKING"]
        );
        app.world_mut()
            .resource_mut::<crate::i18n::Locale>()
            .set(LocaleId::parse("zh-Hans").unwrap());
        app.update();
        assert_eq!(label(&mut app, "DraftLock"), "锁定");
        assert_eq!(label(&mut app, "DraftCancel"), "取消");
        assert_eq!(
            label(&mut app, &format!("DraftHero-{}", HeroClass::Warrior.id())),
            "战士 · 单人路"
        );
        let shown = texts(&mut app);
        assert!(shown.iter().any(|text| text == "组建你的队伍"), "{shown:?}");
        let plate = plate_texts(&mut app);
        assert!(plate[0].starts_with("Local"), "{plate:?}");
        assert_eq!(plate[1], "战士");
        assert_eq!(plate[2], "单人路");
        assert!(!plate.iter().any(|text| text == "Warrior" || text == "Mid"));
        assert!(!shown.iter().any(|text| text == "Assemble your team"));
    }

    #[test]
    fn draft_presses_dispatch_once_and_disabled_buttons_do_nothing() {
        use crate::ui::test_id::harness;
        let mut app = harness::kit_app();
        app.init_resource::<DraftClient>()
            .init_resource::<GameStateSnapshot>()
            .add_message::<SessionUiCommand>()
            .add_ui_action::<DraftAction>()
            .add_systems(Update, draft_actions.after(UiSet::Dispatch));
        harness::spawn_ui(app.world_mut(), |root| {
            action_button(
                root,
                "Cancel",
                DraftAction::Leave,
                "DraftCancel",
                86.0,
                false,
                false,
            );
            action_button(
                root,
                "Lock in",
                DraftAction::Lock,
                "DraftLock",
                132.0,
                true,
                false,
            );
        });
        app.update();
        let lock = harness::find(app.world_mut(), "DraftLock").unwrap();
        assert_eq!(
            app.world().get::<ButtonStyle>(lock).unwrap().kind,
            ButtonKind::Primary
        );
        let leaves = |app: &mut App| {
            app.world_mut()
                .resource_mut::<Messages<SessionUiCommand>>()
                .drain()
                .filter(|command| matches!(command, SessionUiCommand::LeaveMatch))
                .count()
        };
        // Leaving works even without a roster (transport teardown).
        harness::press(app.world_mut(), "DraftCancel");
        app.update();
        assert_eq!(leaves(&mut app), 1);
        app.update();
        assert_eq!(leaves(&mut app), 0);
        harness::set_disabled(app.world_mut(), "DraftCancel", true);
        harness::press(app.world_mut(), "DraftCancel");
        app.update();
        assert_eq!(leaves(&mut app), 0);
        assert!(harness::drain_actions::<DraftAction>(app.world_mut()).is_empty());
        // Without a prematch roster the lock-in has nothing to toggle.
        harness::press(app.world_mut(), "DraftLock");
        app.update();
        assert_eq!(
            harness::drain_actions::<DraftAction>(app.world_mut()),
            [DraftAction::Lock]
        );
        assert_eq!(app.world().resource::<DraftClient>().desired_lock, None);
    }
}
