import random
import unittest

from engine.game import Game


class QuestChainTests(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(1)

    def _move_to_market_square(self, game: Game) -> None:
        game.process_command("move stonewatch")
        game.process_command("move market")

    def test_quest_chains_and_ux(self) -> None:
        game = Game(data_dir="data", player_name="Tester")

        self._move_to_market_square(game)
        quests_output = game.process_command("quests")
        self.assertIn("Quest Log", quests_output)
        self.assertIn("Offered quests:", quests_output)
        self.assertIn("Active quests:", quests_output)
        self.assertIn("Completed quests:", quests_output)

        journal_output = game.process_command("journal")
        self.assertIn("No completed quests recorded yet.", journal_output)

        # Arc + faction gate met, skill gate not yet met.
        game.player.faction_reputation["merchant_guild"] = 6
        broker_output = game.process_command("talk market broker")
        self.assertNotIn("Roadside Losses", broker_output)

        game.player.skills["persuasion"] = 1
        broker_output = game.process_command("talk market broker")
        self.assertIn("Roadside Losses", broker_output)

        accept_output = game.process_command("accept roadside")
        self.assertIn("Quest accepted: Roadside Losses.", accept_output)

        game.process_command("move gate")
        game.process_command("move village")
        game.process_command("move river")
        inspect_output = game.process_command("inspect ledger")
        self.assertIn("Quest progress: Roadside Losses", inspect_output)
        self.assertIn("Market Square (Market Broker)", inspect_output)

        save_output = game.process_command("save")
        self.assertIn("Game saved", save_output)

        reloaded = Game(data_dir="data", player_name="Tester")
        load_output = reloaded.process_command("load")
        self.assertIn("Game loaded", load_output)

        quests_output = reloaded.process_command("quests")
        self.assertIn("Roadside Losses", quests_output)
        self.assertIn("Ready to turn in", quests_output)

        reloaded.process_command("move village")
        reloaded.process_command("move stonewatch")
        reloaded.process_command("move market")
        turn_in_output = reloaded.process_command("talk market broker")
        self.assertIn("Quest updated: Roadside Losses - Recover the Stolen Satchel.", turn_in_output)

        reloaded.player.inventory.append("stolen_satchel")
        reloaded.process_command("move gate")
        reloaded.process_command("move market")
        quests_output = reloaded.process_command("quests")
        self.assertIn("Ready to turn in", quests_output)

        complete_output = reloaded.process_command("talk market broker")
        self.assertIn("Quest completed: Roadside Losses.", complete_output)

        journal_output = reloaded.process_command("journal")
        self.assertIn("Roadside Losses", journal_output)

        reloaded.process_command("move shrine")
        shrine_offer = reloaded.process_command("talk town caretaker")
        self.assertIn("Ashes for Stonewatch", shrine_offer)

        accept_shrine = reloaded.process_command("accept ashes")
        self.assertIn("Quest accepted: Ashes for Stonewatch.", accept_shrine)

        step_one = reloaded.process_command("talk town caretaker")
        self.assertIn("Quest progress: Ashes for Stonewatch", step_one)

        quests_output = reloaded.process_command("quests")
        self.assertIn("Ashes for Stonewatch", quests_output)
        self.assertIn("Awaiting requirements", quests_output)

        reloaded.player.adjust_npc_trust("shrine_caretaker", 2)
        reloaded.world.activate_location_state("ruined_shrine", "shrine_corruption")

        quests_output = reloaded.process_command("quests")
        self.assertIn("Ashes for Stonewatch", quests_output)
        self.assertIn("In progress", quests_output)


if __name__ == "__main__":
    unittest.main()
