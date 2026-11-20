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

    /// Every hero has a fixed signature weapon. These are visual equipment
    /// defaults only: they do not alter combat stats, abilities, or item shop.
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
                crate::HeroClass::Chainkeeper => "forge-hammer",
                crate::HeroClass::Frostguard => "forge-hammer",
                crate::HeroClass::Adventurer => "dagger",
            }),
            Self::Unequipped => None,
            Self::Item(id) => Some(id),
        }
    }

    /// Only the Wildspark default follows its selected ranged weapon mode.
    /// Other heroes keep their signature weapon regardless of that setting.
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
    use crate::{HeroClass, loadout::WeaponMode};

    #[test]
    fn every_hero_has_a_signature_weapon() {
        for class in HeroClass::ALL {
            assert!(
                HandheldSelection::ClassDefault.resolve(class).is_some(),
                "{} has no signature weapon",
                class.id()
            );
        }
        assert_eq!(
            HandheldSelection::ClassDefault.resolve(HeroClass::Warrior),
            Some("forge-sword")
        );
        assert_eq!(
            HandheldSelection::ClassDefault.resolve(HeroClass::Ranger),
            Some("verdant-bow")
        );
        assert_eq!(
            HandheldSelection::ClassDefault.resolve(HeroClass::Mage),
            Some("dawn-scepter")
        );
        assert_eq!(
            HandheldSelection::ClassDefault.resolve(HeroClass::Adventurer),
            Some("dagger")
        );
    }

    #[test]
    fn only_wildspark_switches_its_signature_weapon_with_weapon_mode() {
        assert_eq!(
            HandheldSelection::ClassDefault.resolve_mode(HeroClass::Wildspark, WeaponMode::Repeater),
            Some("wild-repeater")
        );
        assert_eq!(
            HandheldSelection::ClassDefault.resolve_mode(HeroClass::Wildspark, WeaponMode::Rockets),
            Some("wild-launcher")
        );
        assert_eq!(
            HandheldSelection::ClassDefault.resolve_mode(HeroClass::Warrior, WeaponMode::Rockets),
            Some("forge-sword")
        );
        assert_eq!(
            HandheldSelection::Unequipped.resolve(HeroClass::Wildspark),
            None
        );
        let equipped = HandheldSelection::Item("sdk-skin".into());
        for class in HeroClass::ALL {
            assert_eq!(equipped.resolve(class), Some("sdk-skin"));
        }
    }
}
