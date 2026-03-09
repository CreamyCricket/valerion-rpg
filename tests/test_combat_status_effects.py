import random
import unittest

from engine.combat import CombatEngine
from player.character import Character


class CombatStatusEffectTests(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(31)

    def test_enemy_ability_applies_and_resolves_dot_status(self) -> None:
        combat = CombatEngine()
        player = Character(name="Status")
        player.max_hp = 120
        player.hp = 120
        player.base_attack = 2

        enemies = {
            "test_venom": {
                "name": "Venom Raider",
                "family": "bandits",
                "class_type": "ambusher",
                "level": 3,
                "stats": {
                    "strength": 10,
                    "agility": 12,
                    "vitality": 10,
                    "endurance": 10,
                    "mind": 6,
                    "wisdom": 6,
                    "charisma": 2,
                    "luck": 8,
                },
                "skills": {"stealth": 3, "defense": 1},
                "abilities": [
                    {
                        "id": "venom_bite",
                        "apply_status": {"id": "poison", "duration": 2},
                    }
                ],
                "focus": 10,
                "hp": 18,
                "defense": 8,
                "attack": 3,
                "behavior": "aggressive",
                "xp": 40,
                "loot": [],
            }
        }

        result = combat.fight(player, "test_venom", enemies, {})
        joined = "\n".join(result.get("log", []))

        self.assertIn("inflicts Poison", joined)
        self.assertIn("suffers Poison", joined)


if __name__ == "__main__":
    unittest.main()
