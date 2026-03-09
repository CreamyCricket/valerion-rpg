import json
import random
import tempfile
import unittest
from pathlib import Path

from engine.game import Game


class SaveSlotTests(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(11)

    @staticmethod
    def _disable_dynamic_events(game: Game) -> None:
        for location in game.world.locations.values():
            location["world_event_chance"] = 0
            location["state_event_chance"] = 0
            location["world_events"] = []
            location["state_events"] = []
            location["encounters"] = []
            if isinstance(location.get("dungeon"), dict):
                location["dungeon"] = {}
        for location in game.world.state_locations.values():
            location["world_event_chance"] = 0
            location["state_event_chance"] = 0
            location["world_events"] = []
            location["state_events"] = []
            location["encounters"] = []
            if isinstance(location.get("dungeon"), dict):
                location["dungeon"] = {}

    def test_multiple_characters_save_and_load_in_isolated_slots(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            hero_one = {
                "name": "Aria",
                "gender": "woman",
                "race": "elf",
                "player_class": "mage",
                "background": "shrine_touched",
                "bio": "First slot hero.",
            }
            hero_two = {
                "name": "Borin",
                "gender": "man",
                "race": "dwarf",
                "player_class": "warrior",
                "background": "watcher",
                "bio": "Second slot hero.",
            }

            first = Game(data_dir="data", player_name="Aria", character_profile=hero_one, save_root=tmpdir)
            self._disable_dynamic_events(first)
            first.process_command("accept clear the forest path")
            first.process_command("move forest")
            first.world.activate_location_state("river_crossing", "bandit_raid")
            save_one = first.process_command("save 1")
            self.assertIn("slot_1.json", save_one)

            second = Game(data_dir="data", player_name="Borin", character_profile=hero_two, save_root=tmpdir)
            self._disable_dynamic_events(second)
            second.process_command("move stonewatch")
            second.process_command("move market")
            second.process_command("accept wolfpack culling")
            second.player.gold += 17
            save_two = second.process_command("save 2")
            self.assertIn("slot_2.json", save_two)

            slots_output = second.process_command("slots")
            self.assertIn("Slot 1", slots_output)
            self.assertIn("Aria", slots_output)
            self.assertIn("Slot 2", slots_output)
            self.assertIn("Borin", slots_output)

            loaded_one = Game(data_dir="data", player_name="Loader", save_root=tmpdir)
            self._disable_dynamic_events(loaded_one)
            load_one = loaded_one.process_command("load 1")
            self.assertIn("Game loaded", load_one)
            self.assertEqual(loaded_one.player.name, "Aria")
            self.assertEqual(loaded_one.player.race, "Elf")
            self.assertEqual(loaded_one.player.player_class, "Mage")
            self.assertEqual(loaded_one.current_location, "forest_path")
            self.assertIn("q001_clear_forest_path", loaded_one.quests.accepted)
            self.assertTrue(loaded_one.world.has_location_state("river_crossing", "bandit_raid"))
            self.assertNotIn("c001_wolfpack_culling", loaded_one.contracts.accepted)

            loaded_two = Game(data_dir="data", player_name="Loader", save_root=tmpdir)
            self._disable_dynamic_events(loaded_two)
            load_two = loaded_two.process_command("load 2")
            self.assertIn("Game loaded", load_two)
            self.assertEqual(loaded_two.player.name, "Borin")
            self.assertEqual(loaded_two.player.race, "Dwarf")
            self.assertEqual(loaded_two.player.player_class, "Warrior")
            self.assertEqual(loaded_two.current_location, "market_square")
            self.assertIn("c001_wolfpack_culling", loaded_two.contracts.accepted)
            self.assertFalse(loaded_two.world.has_location_state("river_crossing", "bandit_raid"))
            self.assertGreater(loaded_two.player.gold, loaded_one.player.gold)

    def test_legacy_save_migrates_to_slot_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            legacy_path = Path(tmpdir) / "savegame.json"

            game = Game(data_dir="data", player_name="LegacyHero", save_root=tmpdir)
            self._disable_dynamic_events(game)
            game.save_path = legacy_path
            save_output = game.process_command("save")
            self.assertIn("savegame.json", save_output)

            migrated = Game(data_dir="data", player_name="Loader", save_root=tmpdir)
            self._disable_dynamic_events(migrated)

            self.assertFalse(legacy_path.exists())
            self.assertTrue((Path(tmpdir) / "saves" / "slot_1.json").exists())

            slots_output = migrated.process_command("slots")
            self.assertIn("Slot 1", slots_output)
            self.assertIn("LegacyHero", slots_output)

            migrated_data = json.loads((Path(tmpdir) / "saves" / "slot_1.json").read_text())
            self.assertIn("slot_meta", migrated_data)


if __name__ == "__main__":
    unittest.main()
