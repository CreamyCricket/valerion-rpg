import random
import tempfile
import unittest

from engine.game import Game


class RaceUnlockAndTravelTests(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(19)

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

    def test_race_unlocks_persist_and_travel_routes_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game = Game(data_dir="data", player_name="Wayfarer", save_root=tmpdir)
            self._disable_dynamic_events(game)

            starter_races = {option["id"] for option in game.available_creation_options("race")}
            starter_classes = {option["id"] for option in game.available_creation_options("class")}

            self.assertIn("human", starter_races)
            self.assertIn("elf", starter_races)
            self.assertIn("dwarf", starter_races)
            self.assertNotIn("tideborn", starter_races)
            self.assertNotIn("hollowborn", starter_races)

            self.assertIn("warrior", starter_classes)
            self.assertIn("ranger", starter_classes)
            self.assertIn("mage", starter_classes)
            self.assertIn("rogue", starter_classes)
            self.assertNotIn("templar", starter_classes)

            game.player.gold = 30
            game.player.faction_reputation["merchant_guild"] = 8

            game.process_command("move stonewatch")
            game.process_command("move market")

            routes_output = game.process_command("routes")
            self.assertIn("Waycarter Network", routes_output)
            self.assertIn("Stormbreak", routes_output)
            self.assertIn("Ironridge Hold", routes_output)
            self.assertNotIn("Vaultreach", routes_output)

            skills_output = game.process_command("skills")
            self.assertIn("Tracking", skills_output)
            self.assertIn("Arcana", skills_output)

            travel_output = game.process_command("travel stormbreak")
            self.assertIn("book ferry passage", travel_output)
            self.assertIn("Stormbreak", travel_output)
            self.assertIn("Tideborn is now available for future characters.", travel_output)
            self.assertEqual(game.current_location, "stormbreak")
            self.assertEqual(game.player.gold, 20)

            fresh_game = Game(data_dir="data", player_name="Fresh", save_root=tmpdir)
            self._disable_dynamic_events(fresh_game)
            unlocked_races = {option["id"] for option in fresh_game.available_creation_options("race")}
            self.assertIn("tideborn", unlocked_races)
            self.assertNotIn("hollowborn", unlocked_races)


if __name__ == "__main__":
    unittest.main()
