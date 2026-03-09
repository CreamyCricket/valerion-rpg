import random
import tempfile
import unittest

from engine.game import Game


class NumberedMenuChoiceTests(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(29)

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

    def test_numbered_structured_choices_with_alias_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game = Game(data_dir="data", player_name="Menus", save_root=tmpdir)
            self._disable_dynamic_events(game)
            game.player.gold = 40

            buy_menu = game.process_command("buy")
            self.assertIn("Buy Menu", buy_menu)
            self.assertIn("1.", buy_menu)
            buy_by_number = game.process_command("buy 1")
            self.assertIn("Sold 1", buy_by_number)

            game.process_command("move stonewatch")
            game.process_command("move market")

            board = game.process_command("board")
            self.assertIn("Accept Menu", board)
            self.assertIn("1.", board)
            accept_by_number = game.process_command("accept 1")
            self.assertIn("Contract accepted", accept_by_number)

            routes = game.process_command("routes")
            self.assertIn("1.", routes)
            travel_by_name = game.process_command("travel stormbreak")
            self.assertIn("Stormbreak", travel_by_name)

            game.process_command("move stonewatch")
            game.process_command("move market")
            game.process_command("move shrine")
            if "field_bandage" not in game.player.known_recipes:
                game.player.known_recipes.append("field_bandage")

            craft_menu = game.process_command("craft")
            self.assertIn("Craft Menu", craft_menu)
            self.assertIn("1.", craft_menu)
            craft_by_number = game.process_command("craft 1")
            self.assertNotIn("do not know a recipe", craft_by_number.lower())


if __name__ == "__main__":
    unittest.main()
