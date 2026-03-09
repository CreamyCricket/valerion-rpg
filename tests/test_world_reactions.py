import random
import tempfile
import unittest

from engine.game import Game


class WorldReactionRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(23)

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

    def test_world_reactions_rumors_and_recurring_figures(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game = Game(data_dir="data", player_name="Watcher", save_root=tmpdir)
            self._disable_dynamic_events(game)
            game.player.gold = 40

            stonewatch_output = game.process_command("move stonewatch")
            self.assertIn("World note", stonewatch_output)
            self.assertIn("board clerks now know your rank", stonewatch_output)
            game.process_command("move market")

            square_dain = game.process_command("talk master dain")
            self.assertIn("Master Dain", square_dain)

            rumor_output = game.process_command("ask market broker about rumors")
            self.assertIn("Wolfpack Culling", rumor_output)

            game.contracts.unlocked_ranks.add("C")
            gate_output = game.process_command("move gate")
            self.assertIn("Town Gate", gate_output)

            rank_reaction = game.process_command("talk ves")
            self.assertIn("working company", rank_reaction)

            recap_output = game.process_command("recap")
            self.assertIn("World acknowledgement", recap_output)
            self.assertIn("Stonewatch's ledgers now mark you as C-rank", recap_output)

            story_output = game.process_command("story")
            self.assertIn("World acknowledgement", story_output)
            self.assertIn("Stonewatch's ledgers now mark you as C-rank", story_output)

            history_output = game.process_command("history")
            self.assertIn("Stonewatch's board clerks now know your rank", history_output)

            game.process_command("move market")
            travel_output = game.process_command("travel ironridge")
            self.assertIn("Ironridge Hold", travel_output)

            ridge_dain = game.process_command("talk master dain")
            self.assertIn("Master Dain", ridge_dain)


if __name__ == "__main__":
    unittest.main()
