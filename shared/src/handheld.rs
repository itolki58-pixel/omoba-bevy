//! Legacy wire-compatible handheld slot.
//!
//! The UI no longer exposes equipment. For selectable heroes this value is
//! always ClassDefault, which resolves to the hero's fixed signature weapon.
//! The Item variant remains only to decode older stored/session data.
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "mode", content = "id", rename_all = "snake_case")]
pub enum HandheldSelection {
    #[default]
    ClassDefault,
    Unequipped,
    Item(String),
}

impl HandheldSelection {
    pub fn is_default(&self) -> bool {
        *self == Self::ClassDefault
    }

    pub fn resolve(&self, class: crate::HeroClass) -> Option<&str> {
        match self {
            Self::ClassDefault => crate::hero_roster::profile(class)
                .and_then(|hero| hero.weapon)
                .or_else(|| match class {
                    // Non-selectable legacy kits keep a single visual fallback.
                    crate::HeroClass::Wildspark => Some("wild-repeater"),
                    crate::HeroClass::Riftshot => Some("verdant-bow"),
                    crate::HeroClass::Dawnweaver => Some("dawn-scepter"),
                    _ => None,
                }),
            Self::Unequipped => None,
            Self::Item(id) => Some(id),
        }
    }

    /// Weapon mode is retained in old loadout packets but never swaps a
    /// hero's signature weapon.
    pub fn resolve_mode(
        &self,
        class: crate::HeroClass,
        _mode: crate::loadout::WeaponMode,
    ) -> Option<&str> {
        self.resolve(class)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{HeroClass, hero_roster::STARTER_ROSTER, loadout::WeaponMode};

    #[test]
    fn every_selectable_hero_has_one_fixed_signature_weapon() {
        for hero in STARTER_ROSTER {
            assert_eq!(
                HandheldSelection::ClassDefault.resolve(hero.class),
                hero.weapon,
                "{}",
                hero.display_name
            );
            assert_eq!(
                HandheldSelection::ClassDefault.resolve_mode(hero.class, WeaponMode::Rockets),
                hero.weapon,
                "{} must not switch weapons with a loadout mode",
                hero.display_name
            );
        }
        // Zargat's Hellblade is authored into his character model/visual,
        // rather than supplied by the detachable handheld asset catalogue.
        assert_eq!(
            HandheldSelection::ClassDefault.resolve(HeroClass::Warrior),
            None
        );
        assert_eq!(
            HandheldSelection::ClassDefault.resolve(HeroClass::Ranger),
            Some("verdant-bow")
        );
        assert_eq!(
            HandheldSelection::ClassDefault.resolve(HeroClass::Mage),
            Some("dawn-scepter")
        );
    }

    #[test]
    fn legacy_custom_equipment_is_decodable_but_not_required_by_new_hero_profiles() {
        assert_eq!(HandheldSelection::Unequipped.resolve(HeroClass::Warrior), None);
        let equipped = HandheldSelection::Item("legacy-skin".into());
        assert_eq!(equipped.resolve(HeroClass::Warrior), Some("legacy-skin"));
    }
}
