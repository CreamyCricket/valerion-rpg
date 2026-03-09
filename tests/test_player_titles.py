import random
import tempfile
import unittest

from engine.game import Game


class PlayerTitleTests(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(17)

    def test_title_unlock_npc_recognition_stats_and_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game = Game(data_dir="data", player_name="TitleHero", save_root=tmpdir)

            game.player.record_event(
                "miniboss_defeated",
                {
                    "enemy_id": "gorgos_the_sundered",
                    "enemy_name": "Gorgos the Sundered",
                    "location_id": "ironridge_pass",
                    "location_name": "Ironridge Pass",
                },
            )
            unlock_lines = game._refresh_titles(source="test boss")
            self.assertIn("gorgos_slayer", game.player.unlocked_titles)
            self.assertTrue(any("Gorgos-Slayer" in line for line in unlock_lines))
            self.assertEqual(game._refresh_titles(source="test boss"), [])

            game.process_command("move stonewatch")
            dialogue = game.process_command("talk gatewarden")
            self.assertIn("Gorgos-Slayer", dialogue)

            stats_output = game.process_command("stats")
            self.assertIn("Titles: Gorgos-Slayer", stats_output)

            history_output = game.process_command("history")
            self.assertIn("Earned the title Gorgos-Slayer", history_output)

            save_output = game.process_command("save")
            self.assertIn("Game saved", save_output)

            loaded = Game(data_dir="data", player_name="TitleHero", save_root=tmpdir)
            load_output = loaded.process_command("load")
            self.assertIn("Game loaded", load_output)
            self.assertIn("gorgos_slayer", loaded.player.unlocked_titles)
            self.assertIn("Titles: Gorgos-Slayer", loaded.process_command("stats"))


if __name__ == "__main__":
    unittest.main()
