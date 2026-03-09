import random
import tempfile
import unittest

from engine.game import Game


class RoadEncounterTests(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(101)

    @staticmethod
    def _disable_location_dynamic_events(game: Game) -> None:
        for location in game.world.locations.values():
            location["world_event_chance"] = 0
            location["state_event_chance"] = 0
            location["world_events"] = []
            location["state_events"] = []
            location["encounters"] = []
        for location in game.world.state_locations.values():
            location["world_event_chance"] = 0
            location["state_event_chance"] = 0
            location["world_events"] = []
            location["state_events"] = []
            location["encounters"] = []

    @staticmethod
    def _force_road_encounter(game: Game, encounter_id: str) -> None:
        encounter = None
        for entry in game.world.road_encounters.get("encounters", []):
            if str(entry.get("encounter_id", "")).strip().lower() == encounter_id:
                encounter = dict(entry)
                break
        if encounter is None:
            raise AssertionError(f"Missing road encounter fixture: {encounter_id}")
        encounter["weight"] = 100
        game.world.road_encounters = {
            "meta": {"travel_chance": 100},
            "encounters": [encounter],
        }

    def test_travel_can_trigger_combat_road_encounter(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game = Game(data_dir="data", player_name="RoadCombat", save_root=tmpdir)
            self._disable_location_dynamic_events(game)
            self._force_road_encounter(game, "road_bandit_ambush")
            game.player.gold = 30
            game.world.enemies["bandit_raider"]["hp"] = 1
            game.world.enemies["bandit_raider"]["attack"] = 0

            game.process_command("move stonewatch")
            game.process_command("move market")
            travel_output = game.process_command("travel stormbreak")

            self.assertIn("Road encounter: Bandit Ambush.", travel_output)
            self.assertIn("Stormbreak", travel_output)
            self.assertIn("bandit_raider", game.world.get_enemies_at("stormbreak"))

            fight_output = game.process_command("fight bandit raider")
            self.assertIn("You defeated Bandit Raider.", fight_output)
            self.assertNotIn("bandit_raider", game.world.get_enemies_at("stormbreak"))

    def test_travel_can_trigger_noncombat_road_encounter(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game = Game(data_dir="data", player_name="RoadSocial", save_root=tmpdir)
            self._disable_location_dynamic_events(game)
            self._force_road_encounter(game, "road_traveling_merchant")
            game.player.gold = 30

            starting_gold = game.player.gold
            game.process_command("move stonewatch")
            game.process_command("move market")
            travel_output = game.process_command("travel stormbreak")

            self.assertIn("Traveling Merchant", travel_output)
            self.assertIn("Rumor learned:", travel_output)
            self.assertEqual(game.player.gold, starting_gold - 6)
            self.assertGreaterEqual(game.player.reputation_value("merchant_guild"), 2)
            self.assertEqual(game.world.get_enemies_at("stormbreak"), [])


if __name__ == "__main__":
    unittest.main()
