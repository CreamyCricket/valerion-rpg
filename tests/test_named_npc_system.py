import random
import tempfile
import unittest

from engine.game import Game


class NamedNpcSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(41)

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

    def test_named_npcs_share_rumors_and_recognize_boss_kills(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game = Game(data_dir="data", player_name="Watcher", save_root=tmpdir)
            self._disable_dynamic_events(game)

            game.process_command("move stonewatch")
            game.process_command("move market")

            default_dialogue = game.process_command("talk celene")
            self.assertIn("Factor Celene (Merchant Guild factor)", default_dialogue)
            self.assertIn("every shipment has two prices", default_dialogue)
            self.assertNotIn("World reaction:", default_dialogue)

            rumor_dialogue = game.process_command("ask celene about rumors")
            self.assertIn("What they pass on:", rumor_dialogue)
            self.assertIn("Stormbreak Harbor looks loud and ordinary", rumor_dialogue)

            game.player.record_event(
                "miniboss_defeated",
                {
                    "enemy_id": "gorgos_the_sundered",
                    "enemy_name": "Gorgos the Sundered",
                    "location_id": "ironridge_pass",
                    "location_name": "Ironridge Pass",
                },
            )
            boss_reaction = game.process_command("talk kellan")
            self.assertIn("Kellan Grey (Traveling bard)", boss_reaction)
            self.assertIn("it was you at Ironridge", boss_reaction)
            self.assertIn("Word of your deeds has clearly spread through Stonewatch.", boss_reaction)


if __name__ == "__main__":
    unittest.main()
