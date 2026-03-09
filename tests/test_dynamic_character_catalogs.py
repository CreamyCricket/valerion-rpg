import unittest

from player.character import Character


class DynamicCharacterCatalogTests(unittest.TestCase):
    def test_race_and_class_options_load_from_json(self) -> None:
        race_ids = {option["id"] for option in Character.creation_options("race")}
        class_ids = {option["id"] for option in Character.creation_options("class")}

        self.assertIn("stonekin", race_ids)
        self.assertIn("sunforged", race_ids)
        self.assertIn("templar", class_ids)
        self.assertIn("mystic", class_ids)

        race_details = Character.creation_option_details("race", "stonekin")
        class_details = Character.creation_option_details("class", "mystic")

        self.assertEqual(race_details["passive"]["name"], "Granite Poise")
        self.assertEqual(class_details["attack_stat"], "mind")
        self.assertIn("spellcasting", class_details["level_skill_growth"])

    def test_character_creation_uses_dynamic_race_and_class_templates(self) -> None:
        character = Character.create_from_profile(
            name="Seren",
            gender="woman",
            race="tideborn",
            player_class="spellblade",
            background="watcher",
            bio="A shore duelist.",
        )

        self.assertEqual(character.race, "Tideborn")
        self.assertEqual(character.player_class, "Spellblade")
        self.assertIn("apprentice_staff", character.inventory)
        self.assertIn("road_knife", character.inventory)
        self.assertIn("firebolt", character.abilities)
        self.assertIn("power_strike", character.abilities)
        self.assertEqual(character.attack_stat_name({}), "mind")
        self.assertEqual(character.weapon_skill_name({}), "spellcasting")

    def test_creation_preview_exposes_json_backed_details(self) -> None:
        preview = Character.creation_preview(
            {
                "name": "Vale",
                "gender": "nonbinary",
                "race": "hollowborn",
                "player_class": "hunter",
                "background": "wanderer",
            }
        )

        self.assertEqual(preview["race_details"]["passive"]["name"], "Grave-Sense")
        self.assertEqual(preview["class_details"]["attack_stat"], "agility")
        self.assertIn("track_prey", preview["class_details"]["abilities"])


if __name__ == "__main__":
    unittest.main()
