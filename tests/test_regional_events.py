import random
import tempfile
import unittest

from engine.game import Game


class RegionalEventSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(77)

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
    def _only_stonewatch_regional_triggers(game: Game) -> None:
        for region_id, region_data in game.world.regional_event_zones.items():
            if not isinstance(region_data, dict):
                continue
            region_data["activation_chance"] = 0
            for entry in region_data.get("events", []):
                if isinstance(entry, dict):
                    entry["weight"] = 0
            if region_id == "stonewatch_frontier":
                region_data["activation_chance"] = 100
                for entry in region_data.get("events", []):
                    if not isinstance(entry, dict):
                        continue
                    event_id = str(entry.get("event_id", "")).strip().lower()
                    if event_id == "stonewatch_wolf_sightings":
                        entry["weight"] = 100

    def test_regional_event_appears_escalates_affects_board_and_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game = Game(data_dir="data", player_name="Regional", save_root=tmpdir)
            self._disable_location_dynamic_events(game)
            self._only_stonewatch_regional_triggers(game)

            move_output = game.process_command("move stonewatch")
            self.assertIn("World event: Wolf Sightings", move_output)
            active_after_start = {event.get("event_id", "") for event in game.world.active_regional_events()}
            self.assertIn("stonewatch_wolf_sightings", active_after_start)

            market_move_output = game.process_command("move market")
            self.assertIn("World event: Livestock Kills", market_move_output)
            active_after_escalation = {event.get("event_id", "") for event in game.world.active_regional_events()}
            self.assertIn("stonewatch_livestock_kills", active_after_escalation)

            board_output = game.process_command("board")
            self.assertIn("Crisis Priority", board_output)
            self.assertIn("Wolfpack Culling", board_output)

            game.world.active_regional_events_by_region = {}
            game.world.activate_regional_event("stonewatch_guard_lockdown", "town_gate")
            game.world.enemies["bandit_tollmaster"]["hp"] = 1
            game.world.enemies["bandit_tollmaster"]["attack"] = 0
            game.player.hp = game.player.max_hp

            game.process_command("move gate")
            game.process_command("move barracks")
            fight_output = game.process_command("fight bandit_tollmaster")
            self.assertIn("World event: Guard Lockdown", fight_output)
            active_after_resolution = {event.get("event_id", "") for event in game.world.active_regional_events()}
            self.assertNotIn("stonewatch_guard_lockdown", active_after_resolution)
            self.assertNotIn("bandit_tollmaster", game.world.get_enemies_at("watch_barracks"))

    def test_regional_event_persists_through_save_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game = Game(data_dir="data", player_name="RegionalSave", save_root=tmpdir)
            self._disable_location_dynamic_events(game)
            game.world.activate_regional_event("stormbreak_ferry_strikes", "stormbreak")

            save_output = game.process_command("save")
            self.assertIn("Game saved", save_output)

            reloaded = Game(data_dir="data", player_name="RegionalSave", save_root=tmpdir)
            self._disable_location_dynamic_events(reloaded)
            load_output = reloaded.process_command("load")
            self.assertIn("Game loaded", load_output)

            active_after_load = {event.get("event_id", "") for event in reloaded.world.active_regional_events()}
            self.assertIn("stormbreak_ferry_strikes", active_after_load)


if __name__ == "__main__":
    unittest.main()
