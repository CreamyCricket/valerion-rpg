import random
import unittest
from pathlib import Path

from engine.game import Game


class ContractBoardTests(unittest.TestCase):
    SAVE_PATH = Path("test_contract_save.json")

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
        for location in game.world.state_locations.values():
            location["world_event_chance"] = 0
            location["state_event_chance"] = 0
            location["world_events"] = []
            location["state_events"] = []
            location["encounters"] = []

    @staticmethod
    def _move_to_market(game: Game) -> None:
        game.process_command("move stonewatch")
        game.process_command("move market")

    @staticmethod
    def _move_to_bandit_camp(game: Game) -> None:
        game.process_command("move gate")
        game.process_command("move village")
        game.process_command("move forest")
        game.process_command("move deeper")
        game.process_command("move camp")

    @staticmethod
    def _return_to_market(game: Game) -> None:
        game.process_command("move forest")
        game.process_command("move path")
        game.process_command("move village")
        game.process_command("move stonewatch")
        game.process_command("move market")

    def test_contract_board_save_load_and_claim_flow(self) -> None:
        game = Game(data_dir="data", player_name="Tester")
        game.save_path = self.SAVE_PATH
        self._disable_dynamic_events(game)

        self._move_to_market(game)
        board_output = game.process_command("board")
        self.assertIn("Stonewatch Contract Board", board_output)
        self.assertIn("Wolfpack Culling", board_output)
        self.assertIn("Merchant Recovery", board_output)

        accept_output = game.process_command("accept merchant recovery")
        self.assertIn("Contract accepted: Merchant Recovery.", accept_output)
        self.assertIn("Recover the Iron Lockbox", accept_output)

        contracts_output = game.process_command("contracts")
        self.assertIn("Merchant Recovery", contracts_output)

        save_output = game.process_command("save")
        self.assertIn("Game saved", save_output)

        reloaded = Game(data_dir="data", player_name="Tester")
        reloaded.save_path = self.SAVE_PATH
        load_output = reloaded.process_command("load")
        self.assertIn("Game loaded", load_output)
        self._disable_dynamic_events(reloaded)

        contracts_output = reloaded.process_command("contracts")
        self.assertIn("Merchant Recovery", contracts_output)

        self._move_to_bandit_camp(reloaded)
        take_output = reloaded.process_command("take iron lockbox")
        self.assertIn("Iron Lockbox", take_output)
        self.assertIn("Contract complete: Merchant Recovery.", take_output)

        self._return_to_market(reloaded)
        starting_gold = reloaded.player.gold
        starting_rep = reloaded.player.reputation_value("merchant_guild")
        starting_trust = reloaded.player.npc_trust("aldric")

        claim_output = reloaded.process_command("claim merchant recovery")
        self.assertIn("Contract claimed: Merchant Recovery.", claim_output)
        self.assertIn("Reputation: Merchant Guild +5", claim_output)
        self.assertIn("Relations: Aldric trust +12", claim_output)
        self.assertEqual(reloaded.player.gold, starting_gold + 65)
        self.assertEqual(reloaded.player.reputation_value("merchant_guild"), starting_rep + 5)
        self.assertEqual(reloaded.player.npc_trust("aldric"), starting_trust + 12)


if __name__ == "__main__":
    unittest.main()
