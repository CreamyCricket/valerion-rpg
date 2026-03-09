import random
import tempfile
import unittest

from engine.game import Game


class ClassUnlockTests(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(7)

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

    @staticmethod
    def _prepare_gorgos_access(game: Game) -> None:
        game.player.faction_reputation["kingdom_guard"] = 10
        game.contracts.completed_counts["c003_bandit_road_tax"] = 1

    @staticmethod
    def _tune_player_for_boss_test(game: Game) -> None:
        for item_id in ("guardian_plate", "iron_sword"):
            if item_id not in game.player.inventory:
                game.player.inventory.append(item_id)
        game.player.equipped_weapon = "iron_sword"
        game.player.equipped_armor = "guardian_plate"
        game.player.max_hp = 90
        game.player.hp = 90
        game.player.max_focus = 10
        game.player.focus = 10
        game.player.base_attack = 3
        game.player.stats["strength"] = 12
        game.player.stats["vitality"] = 13
        game.player.stats["endurance"] = 14
        game.player.skills["swordsmanship"] = 3
        game.player.skills["defense"] = 4

    def test_boss_defeat_unlocks_class_for_future_characters(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game = Game(data_dir="data", player_name="Unlocker", save_root=tmpdir)
            self._disable_dynamic_events(game)

            initial_classes = {entry["id"] for entry in game.available_creation_options("class")}
            self.assertNotIn("templar", initial_classes)

            self._prepare_gorgos_access(game)
            game.process_command("move stonewatch")
            game.process_command("move market")
            game.process_command("accept break gorgos")
            game.process_command("move barracks")
            game.process_command("move ridge")
            self._tune_player_for_boss_test(game)
            game.process_command("fight bulwark")

            fight_output = game.process_command("fight gorgos")
            self.assertIn("You defeated Gorgos the Sundered.", fight_output)
            self.assertIn("Templar is now available for future characters.", fight_output)

            fresh_game = Game(data_dir="data", player_name="Fresh", save_root=tmpdir)
            self._disable_dynamic_events(fresh_game)
            unlocked_classes = {entry["id"] for entry in fresh_game.available_creation_options("class")}
            self.assertIn("templar", unlocked_classes)


if __name__ == "__main__":
    unittest.main()
