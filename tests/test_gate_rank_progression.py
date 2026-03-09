import random
import unittest

from engine.game import Game


class GateRankProgressionTests(unittest.TestCase):
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
        for location in game.world.state_locations.values():
            location["world_event_chance"] = 0
            location["state_event_chance"] = 0
            location["world_events"] = []
            location["state_events"] = []
            location["encounters"] = []

    @staticmethod
    def _tune_player_for_elite_test(game: Game) -> None:
        for item_id in ("guardian_plate", "iron_sword"):
            if item_id not in game.player.inventory:
                game.player.inventory.append(item_id)
        game.player.equipped_weapon = "iron_sword"
        game.player.equipped_armor = "guardian_plate"
        game.player.max_hp = 90
        game.player.hp = 90
        game.player.max_focus = 10
        game.player.focus = 10
        game.player.base_attack = 4
        game.player.stats["strength"] = 14
        game.player.stats["vitality"] = 14
        game.player.stats["endurance"] = 14
        game.player.skills["swordsmanship"] = 4
        game.player.skills["defense"] = 4

    def test_e_rank_location_shows_rank_in_move_map_and_search(self) -> None:
        game = Game(data_dir="data", player_name="Tester")
        self._disable_dynamic_events(game)

        game.process_command("move forest")
        output = game.process_command("move tower")
        self.assertIn("Gate rank: E-Rank", output)

        search_output = game.process_command("search area")
        self.assertIn("Gate rank: E-Rank", search_output)

        map_output = game.process_command("map")
        self.assertIn("Old Watchtower [YOU] | rank: E-Rank - beginner danger", map_output)

    def test_c_rank_location_warns_on_entry(self) -> None:
        game = Game(data_dir="data", player_name="Tester")
        self._disable_dynamic_events(game)

        game.process_command("move forest")
        output = game.process_command("move deeper")

        self.assertIn("Danger Warning: This region is rated C-Rank.", output)
        self.assertIn("Gate rank: C-Rank", output)

    def test_ranked_zone_elite_fight(self) -> None:
        game = Game(data_dir="data", player_name="Tester")
        self._disable_dynamic_events(game)
        self._tune_player_for_elite_test(game)

        game.process_command("move forest")
        game.process_command("move deeper")
        game.world.add_enemy("deep_forest", "elite_ashwood_fanglord")

        output = game.process_command("fight fanglord")
        self.assertIn("[ELITE] Ashwood Fanglord", output)
        self.assertIn("You defeated [ELITE] Ashwood Fanglord.", output)
        self.assertIn("Rank payout:", output)

    def test_rank_based_contract_board_and_acceptance(self) -> None:
        game = Game(data_dir="data", player_name="Tester")
        self._disable_dynamic_events(game)

        game.process_command("move stonewatch")
        game.process_command("move market")
        board_output = game.process_command("board")

        self.assertIn("[E-Rank] Wolfpack Culling", board_output)
        self.assertIn("[D-Rank] Bandit Road Tax", board_output)

        accept_output = game.process_command("accept wolfpack culling")
        self.assertIn("Contract accepted: Wolfpack Culling.", accept_output)
        self.assertIn("Defeat 3 Ashwood Wolves", accept_output)


if __name__ == "__main__":
    unittest.main()
