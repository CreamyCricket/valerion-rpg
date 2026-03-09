import random
import tempfile
import unittest
from pathlib import Path

from engine.game import Game


class BossProgressionTests(unittest.TestCase):
    SAVE_PATH = Path("test_boss_save.json")

    def setUp(self) -> None:
        random.seed(1)
        if self.SAVE_PATH.exists():
            self.SAVE_PATH.unlink()

    def tearDown(self) -> None:
        if self.SAVE_PATH.exists():
            self.SAVE_PATH.unlink()

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
    def _move_to_market(game: Game) -> None:
        game.process_command("move stonewatch")
        game.process_command("move market")

    @staticmethod
    def _move_to_ironridge(game: Game) -> None:
        game.process_command("move barracks")
        game.process_command("move ridge")

    @staticmethod
    def _return_to_market(game: Game) -> None:
        game.process_command("move stonewatch")
        game.process_command("move square")

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

    def test_boss_contract_fight_and_persistence(self) -> None:
        game = Game(data_dir="data", player_name="Tester")
        game.save_path = self.SAVE_PATH
        self._disable_dynamic_events(game)
        self._prepare_gorgos_access(game)

        self._move_to_market(game)
        board_output = game.process_command("board")
        self.assertIn("Break Gorgos's Toll", board_output)

        accept_output = game.process_command("accept break gorgos")
        self.assertIn("Contract accepted: Break Gorgos's Toll.", accept_output)
        self.assertIn("Ironridge Pass", accept_output)

        self._move_to_ironridge(game)
        self._tune_player_for_boss_test(game)

        elite_output = game.process_command("fight bulwark")
        self.assertIn("[ELITE] Ironpass Bulwark", elite_output)
        self.assertIn("Contract updated: Break Gorgos's Toll.", elite_output)

        game.player.hp = game.player.max_hp
        game.player.focus = game.player.max_focus
        fight_output = game.process_command("fight gorgos")
        self.assertIn("Heavy Shield Bash", fight_output)
        self.assertIn("Desperate Rally", fight_output)
        self.assertIn("You defeated Gorgos the Sundered.", fight_output)
        self.assertIn("Sundered Crest", fight_output)
        self.assertIn("Contract complete: Break Gorgos's Toll.", fight_output)

        self._return_to_market(game)
        claim_output = game.process_command("claim break gorgos")
        self.assertIn("Contract claimed: Break Gorgos's Toll.", claim_output)
        self.assertIn("Raider Sabre", claim_output)

        save_output = game.process_command("save")
        self.assertIn("Game saved", save_output)

        reloaded = Game(data_dir="data", player_name="Tester")
        reloaded.save_path = self.SAVE_PATH
        load_output = reloaded.process_command("load")
        self.assertIn("Game loaded", load_output)
        self._disable_dynamic_events(reloaded)

        board_after_load = reloaded.process_command("board")
        self.assertNotIn("Break Gorgos's Toll", board_after_load)

        self._move_to_ironridge(reloaded)
        fight_after_load = reloaded.process_command("fight gorgos")
        self.assertIn("not a nearby enemy", fight_after_load)

    def test_relic_drop_is_once_per_boss_and_persists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game = Game(data_dir="data", player_name="RelicTester", save_root=tmpdir)
            for relic_id in game.world.relic_ids_for_boss("gorgos_the_sundered"):
                game.world.relics[relic_id]["drop_chance"] = 100
                game.world.items[relic_id]["drop_chance"] = 100

            dropped_relic = game._roll_boss_relic_drop("gorgos_the_sundered", "Gorgos the Sundered")
            self.assertIsNotNone(dropped_relic)
            self.assertTrue(game.player.has_event("boss_relic_dropped", "enemy_id", "gorgos_the_sundered"))

            dropped_again = game._roll_boss_relic_drop("gorgos_the_sundered", "Gorgos the Sundered")
            self.assertIsNone(dropped_again)

            save_output = game.process_command("save")
            self.assertIn("Game saved", save_output)

            reloaded = Game(data_dir="data", player_name="RelicTester", save_root=tmpdir)
            load_output = reloaded.process_command("load")
            self.assertIn("Game loaded", load_output)
            dropped_after_load = reloaded._roll_boss_relic_drop("gorgos_the_sundered", "Gorgos the Sundered")
            self.assertIsNone(dropped_after_load)


if __name__ == "__main__":
    unittest.main()
