import random
import tempfile
import unittest

from engine.game import Game


class NpcReactionPriorityTests(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(31)

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

    def test_rank_boss_and_generic_dialogue_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game = Game(data_dir="data", player_name="Witness", save_root=tmpdir)
            self._disable_dynamic_events(game)

            game.process_command("move stonewatch")
            game.process_command("move gate")
            rank_reaction = game.process_command("talk gatewarden")
            self.assertIn("D-rank and steady work", rank_reaction)

            game.player.record_event(
                "miniboss_defeated",
                {
                    "enemy_id": "gorgos_the_sundered",
                    "enemy_name": "Gorgos the Sundered",
                    "location_id": "ironridge_pass",
                    "location_name": "Ironridge Pass",
                },
            )
            boss_reaction = game.process_command("talk gatewarden")
            self.assertIn("slew Gorgos", boss_reaction)

            game.process_command("move market")
            game.process_command("move blacksmith")
            generic_dialogue = game.process_command("talk blacksmith")
            self.assertIn("The Blacksmith speaks like steel ought to be honest", generic_dialogue)


if __name__ == "__main__":
    unittest.main()
