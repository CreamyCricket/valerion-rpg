import random
import tempfile
import unittest

from engine.game import Game


class HubEconomyIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(89)

    @staticmethod
    def _disable_dynamic_events(game: Game) -> None:
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

    def test_two_hubs_show_distinct_services(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game = Game(data_dir="data", player_name="HubTest", save_root=tmpdir)
            self._disable_dynamic_events(game)

            game.process_command("move stonewatch")
            game.process_command("move market")
            stonewatch_look = game.process_command("look")
            self.assertIn("contract board", stonewatch_look)
            self.assertIn("guard services", stonewatch_look)
            self.assertIn("basic gear", stonewatch_look)

            game.process_command("move gate")
            game.process_command("move village")
            game.process_command("move river")
            game.process_command("move coast")
            game.process_command("move harbor")
            stormbreak_look = game.process_command("look")
            self.assertIn("trade hub", stormbreak_look)
            self.assertIn("rare imports", stormbreak_look)
            self.assertIn("ferry routes", stormbreak_look)
            self.assertNotIn("contract board", stormbreak_look)


if __name__ == "__main__":
    unittest.main()
