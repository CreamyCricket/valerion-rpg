import random
import tempfile
import unittest

from engine.game import Game


class DungeonSiteFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(202)

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

    @staticmethod
    def _boost_combat(game: Game) -> None:
        game.player.max_hp = 140
        game.player.hp = 140
        game.player.max_focus = 24
        game.player.focus = 24
        game.player.base_attack = 14
        game.player.stats["strength"] = 18
        game.player.stats["agility"] = 14
        game.player.stats["mind"] = 12

    def test_dungeon_entry_navigation_combat_rewards_and_save_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game = Game(data_dir="data", player_name="Delver", save_root=tmpdir)
            self._disable_dynamic_events(game)
            self._boost_combat(game)

            move_forest = game.process_command("move forest")
            self.assertIn("Forest Path", move_forest)

            enter_dungeon = game.process_command("move ruins")
            self.assertIn("Ashwood Ruins", enter_dungeon)
            self.assertIn("Collapsed Gate", enter_dungeon)
            self.assertEqual(game.current_location, "ashwood_ruins")
            self.assertEqual(game.current_dungeon_room, "collapsed_gate")

            room_search = game.process_command("search area")
            self.assertIn("Visible enemies", room_search)
            self.assertIn("hall", room_search.lower())

            fight_entry = game.process_command("fight ashwood wolf")
            self.assertIn("You defeated", fight_entry)

            move_hall = game.process_command("move hall")
            self.assertIn("Shattered Hall", move_hall)
            self.assertEqual(game.current_dungeon_room, "shattered_hall")

            loot_shard = game.process_command("take relic core shard")
            self.assertIn("You took", loot_shard)
            self.assertIn("Relic Core Shard", game.process_command("inventory"))

            move_reliquary = game.process_command("move reliquary")
            self.assertIn("Sunken Reliquary", move_reliquary)
            self.assertEqual(game.current_dungeon_room, "sunken_reliquary")

            fight_boss = game.process_command("fight ashwood packleader")
            self.assertIn("Ashwood Packleader", fight_boss)
            self.assertIn("You defeated", fight_boss)

            relic_take = game.process_command("take ashbound ring")
            self.assertIn("You took", relic_take)
            self.assertIn("Ashbound Ring", game.process_command("inventory"))

            game.process_command("move hall")
            game.process_command("move gate")
            exit_dungeon = game.process_command("move out")
            self.assertIn("Forest Path", exit_dungeon)
            self.assertEqual(game.current_location, "forest_path")
            self.assertIsNone(game.current_dungeon_room)

            save_output = game.process_command("save 2")
            self.assertIn("Game saved", save_output)

            loaded = Game(data_dir="data", player_name="Loader", save_root=tmpdir)
            self._disable_dynamic_events(loaded)
            load_output = loaded.process_command("load 2")
            self.assertIn("Game loaded", load_output)
            self.assertEqual(loaded.current_location, "forest_path")
            self.assertIsNone(loaded.current_dungeon_room)


if __name__ == "__main__":
    unittest.main()
