//! The selectable hero roster. Combat kits remain keyed by the legacy
//! HeroClass enum internally, but players select named heroes with fixed
//! positions, avatars, sprite fallbacks and signature weapons.
use crate::{HeroClass, prematch::Role};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum HeroArchetype {
    Warrior,
    Mage,
    Ranged,
    Jungler,
    Healer,
    Tank,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct HeroRosterEntry {
    pub class: HeroClass,
    pub archetype: HeroArchetype,
    pub display_name: &'static str,
    pub position: Role,
    pub avatar: &'static str,
    pub sprite_character: &'static str,
    /// `None` means the weapon is authored directly into the hero model.
    pub weapon: Option<&'static str>,
}

/// First playable roster: two warriors, two mages, two ranged heroes,
/// two junglers, two healers and two tanks. The weapon is part of the hero
/// profile; there is no player-selectable weapon slot.
pub const STARTER_ROSTER: [HeroRosterEntry; 12] = [
    HeroRosterEntry {
        class: HeroClass::Warrior,
        archetype: HeroArchetype::Warrior,
        display_name: "Zargat",
        position: Role::Solo,
        avatar: "crowley",
        sprite_character: "mossback-teapot",
        weapon: None,
    },
    HeroRosterEntry {
        class: HeroClass::Edgeweaver,
        archetype: HeroArchetype::Warrior,
        display_name: "Edgeweaver",
        position: Role::Solo,
        avatar: "good-knight",
        sprite_character: "origami-storm-heron",
        weapon: Some("dagger"),
    },
    HeroRosterEntry {
        class: HeroClass::Mage,
        archetype: HeroArchetype::Mage,
        display_name: "Mage",
        position: Role::Mid,
        avatar: "anna",
        sprite_character: "clockwork-turnip-oracle",
        weapon: Some("dawn-scepter"),
    },
    HeroRosterEntry {
        class: HeroClass::Dawnweaver,
        archetype: HeroArchetype::Mage,
        display_name: "Dawnweaver",
        position: Role::Mid,
        avatar: "mega-angel",
        sprite_character: "void-jelly-astronaut",
        weapon: Some("dawn-scepter"),
    },
    HeroRosterEntry {
        class: HeroClass::Ranger,
        archetype: HeroArchetype::Ranged,
        display_name: "Ranger",
        position: Role::Carry,
        avatar: "megan-the-fox",
        sprite_character: "neon-axolotl-courier",
        weapon: Some("verdant-bow"),
    },
    HeroRosterEntry {
        class: HeroClass::Riftshot,
        archetype: HeroArchetype::Ranged,
        display_name: "Riftshot",
        position: Role::Carry,
        avatar: "lady-koi",
        sprite_character: "tidal-typewriter-crab",
        weapon: Some("verdant-bow"),
    },
    HeroRosterEntry {
        class: HeroClass::Warden,
        archetype: HeroArchetype::Jungler,
        display_name: "Warden",
        position: Role::Jungle,
        avatar: "sport-mecha",
        sprite_character: "cathedral-moth-bellringer",
        weapon: Some("forge-hammer"),
    },
    HeroRosterEntry {
        class: HeroClass::Adventurer,
        archetype: HeroArchetype::Jungler,
        display_name: "Adventurer",
        position: Role::Jungle,
        avatar: "pirate-bot",
        sprite_character: "lunar-marionette-giraffe",
        weapon: Some("dagger"),
    },
    HeroRosterEntry {
        class: HeroClass::Cleric,
        archetype: HeroArchetype::Healer,
        display_name: "Cleric",
        position: Role::Support,
        avatar: "agnes",
        sprite_character: "aurora-magnet-ram",
        weapon: Some("dawn-scepter"),
    },
    HeroRosterEntry {
        class: HeroClass::Chainkeeper,
        archetype: HeroArchetype::Healer,
        display_name: "Chainkeeper",
        position: Role::Support,
        avatar: "orion",
        sprite_character: "aurora-magnet-ram",
        weapon: Some("dawn-scepter"),
    },
    HeroRosterEntry {
        class: HeroClass::Cinderforge,
        archetype: HeroArchetype::Tank,
        display_name: "Cinderforge",
        position: Role::Solo,
        avatar: "cool-tiger",
        sprite_character: "origami-storm-heron",
        weapon: Some("forge-hammer"),
    },
    HeroRosterEntry {
        class: HeroClass::Frostguard,
        archetype: HeroArchetype::Tank,
        display_name: "Frostguard",
        position: Role::Support,
        avatar: "stitch-witch",
        sprite_character: "cathedral-moth-bellringer",
        weapon: Some("forge-hammer"),
    },
];

pub fn profile(class: HeroClass) -> Option<&'static HeroRosterEntry> {
    STARTER_ROSTER.iter().find(|entry| entry.class == class)
}

pub fn is_selectable(class: HeroClass) -> bool {
    profile(class).is_some()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn starter_roster_has_twelve_unique_heroes_and_bundled_identity_assets() {
        assert_eq!(STARTER_ROSTER.len(), 12);
        for (index, entry) in STARTER_ROSTER.iter().enumerate() {
            assert!(STARTER_ROSTER[..index].iter().all(|other| other.class != entry.class));
            assert!(!entry.avatar.is_empty());
            assert!(!entry.sprite_character.is_empty());
            assert!(entry.weapon.is_some() || entry.class == HeroClass::Warrior);
            assert_eq!(profile(entry.class), Some(entry));
        }
    }

    #[test]
    fn roster_covers_the_five_positions_and_the_requested_combat_archetype_counts() {
        for position in Role::ALL {
            assert!(STARTER_ROSTER.iter().any(|entry| entry.position == position));
        }
        assert_eq!(STARTER_ROSTER.iter().filter(|e| e.position == Role::Solo).count(), 3);
        assert_eq!(STARTER_ROSTER.iter().filter(|e| e.position == Role::Mid).count(), 2);
        assert_eq!(STARTER_ROSTER.iter().filter(|e| e.position == Role::Carry).count(), 2);
        assert_eq!(STARTER_ROSTER.iter().filter(|e| e.position == Role::Jungle).count(), 2);
        assert_eq!(STARTER_ROSTER.iter().filter(|e| e.position == Role::Support).count(), 3);
        for archetype in [
            HeroArchetype::Warrior,
            HeroArchetype::Mage,
            HeroArchetype::Ranged,
            HeroArchetype::Jungler,
            HeroArchetype::Healer,
            HeroArchetype::Tank,
        ] {
            assert_eq!(
                STARTER_ROSTER.iter().filter(|entry| entry.archetype == archetype).count(),
                2,
                "{archetype:?}"
            );
        }
    }
}
