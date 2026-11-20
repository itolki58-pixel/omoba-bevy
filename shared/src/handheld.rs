//! Cosmetic equipment is independent of avatar, class and combat inventory.
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
            Self::ClassDefault => Some(match class {
                crate::HeroClass::Warrior => "forge-sword",
                crate::HeroClass::Mage => "dawn-scepter",
                crate::HeroClass::Ranger => "verdant-bow",
                crate::HeroClass::Cleric => "dawn-scepter",
                crate::HeroClass::Warden => "forge-hammer",
                crate::HeroClass::Dawnweaver => "dawn-scepter",
                crate::HeroClass::Wildspark => "wild-repeater",
                crate::HeroClass::Cinderforge => "forge-hammer",
                crate::HeroClass::Edgeweaver => "dagger",
                crate::HeroClass::Stormfist => "forge-hammer",
                crate::HeroClass::Veilstalker => "dagger",
                crate::HeroClass::Emberveil => "dawn-scepter",
                crate::HeroClass::Orbitwright => "dawn-scepter",
                crate::HeroClass::Riftshot => "wild-repeater",
                crate::HeroClass::Chainkeeper => "dawn-scepter",
                crate::HeroClass::Frostguard => "forge-hammer",
                crate::HeroClass::Adventurer => "dagger",
            }),
            Self::Unequipped => None,
            Self::Item(id) => Some(id),
        }
    }

    /// Only the class default follows the equipped gun mode. An explicitly
    /// selected SDK or packaged skin remains the user's choice in either mode.
    pub fn resolve_mode(
        &self,
        class: crate::HeroClass,
        mode: crate::loadout::WeaponMode,
    ) -> Option<&str> {
        if *self == Self::ClassDefault
            && class == crate::HeroClass::Wildspark
            && mode == crate::loadout::WeaponMode::Rockets
        {
            Some("wild-launcher")
        } else {
            self.resolve(class)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::HeroClass;

    #[test]
    fn adventurer_defaults_to_dagger_and_any_class_can_equip_it() {
        assert_eq!(
            HandheldSelection::ClassDefault.resolve(HeroClass::Adventurer),
            Some("dagger")
        );
        let equipped = HandheldSelection::Item("dagger".into());
        for class in HeroClass::ALL {
            assert_eq!(equipped.resolve(class), Some("dagger"));
            assert_eq!(HandheldSelection::Unequipped.resolve(class), None);
        }
    }

    #[test]
    fn class_default_weapon_is_fixed_for_every_hero() {
        let expected = [
            (HeroClass::Warrior, Some("forge-sword")),
            (HeroClass::Mage, Some("dawn-scepter")),
            (HeroClass::Ranger, Some("verdant-bow")),
            (HeroClass::Cleric, Some("dawn-scepter")),
            (HeroClass::Warden, Some("forge-hammer")),
            (HeroClass::Dawnweaver, Some("dawn-scepter")),
            (HeroClass::Wildspark, Some("wild-repeater")),
            (HeroClass::Cinderforge, Some("forge-hammer")),
            (HeroClass::Edgeweaver, Some("dagger")),
            (HeroClass::Stormfist, Some("forge-hammer")),
            (HeroClass::Veilstalker, Some("dagger")),
            (HeroClass::Emberveil, Some("dawn-scepter")),
            (HeroClass::Orbitwright, Some("dawn-scepter")),
            (HeroClass::Riftshot, Some("wild-repeater")),
            (HeroClass::Chainkeeper, Some("dawn-scepter")),
            (HeroClass::Frostguard, Some("forge-hammer")),
            (HeroClass::Adventurer, Some("dagger")),
        ];
        for (class, weapon) in expected {
            assert_eq!(
                HandheldSelection::ClassDefault.resolve(class),
                weapon,
                "{}",
                class.id()
            );
        }
    }
}

#[cfg(test)]
mod ranged_tests {
    use super::*;
    use crate::{HeroClass, loadout::WeaponMode};
    #[test]
    fn ranged_defaults_change_gun_mode_but_preserve_explicit_sdk_skins_and_unequip() {
        assert_eq!(
            HandheldSelection::ClassDefault.resolve(HeroClass::Ranger),
            Some("verdant-bow")
        );
        assert_eq!(
            HandheldSelection::ClassDefault
                .resolve_mode(HeroClass::Wildspark, WeaponMode::Repeater),
            Some("wild-repeater")
        );
        assert_eq!(
            HandheldSelection::ClassDefault.resolve_mode(HeroClass::Wildspark, WeaponMode::Rockets),
            Some("wild-launcher")
        );
        for mode in [WeaponMode::Repeater, WeaponMode::Rockets] {
            assert_eq!(
                HandheldSelection::Unequipped.resolve_mode(HeroClass::Wildspark, mode),
                None
            );
            assert_eq!(
                HandheldSelection::Item("sdk-skin".into()).resolve_mode(HeroClass::Wildspark, mode),
                Some("sdk-skin")
            );
        }
    }
}
