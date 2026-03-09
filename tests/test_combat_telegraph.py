import random
import unittest

from engine.combat import CombatEngine
from player.character import Character


class CombatTelegraphTests(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(17)

    def test_enemy_telegraphs_then_executes_delayed_attack(self) -> None:
        combat = CombatEngine()
        player = Character(name="Telegraph")
        player.max_hp = 120
        player.hp = 120
        player.base_attack = 2

        enemies = {
            "test_brute": {
                "name": "Test Brute",
                "family": "abyss_beasts",
                "class_type": "brute",
                "level": 4,
                "stats": {
                    "strength": 14,
                    "agility": 8,
                    "vitality": 12,
                    "endurance": 12,
                    "mind": 6,
                    "wisdom": 6,
                    "charisma": 2,
                    "luck": 8,
                },
                "skills": {"defense": 3},
                "abilities": [
                    {
                        "id": "crushing_blow",
                        "telegraph": "raises its club for a crushing strike",
                        "delay": 1,
                    }
                ],
                "focus": 10,
                "hp": 24,
                "defense": 9,
                "attack": 4,
                "behavior": "aggressive",
                "xp": 90,
                "loot": [],
            }
        }

        result = combat.fight(player, "test_brute", enemies, {})
        joined_log = "\n".join(result.get("log", []))

        self.assertIn("raises its club for a crushing strike", joined_log)
        self.assertIn("uses Crushing Blow", joined_log)


if __name__ == "__main__":
    unittest.main()
