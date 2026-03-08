import random
import unittest
from pathlib import Path

from engine.game import Game


class ScriptedPlaythroughRegression(unittest.TestCase):
    SAVE_PATH = Path("test_playthrough_save.json")

    def setUp(self) -> None:
        random.seed(42)
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
        for state_location in game.world.state_locations.values():
            state_location["world_event_chance"] = 0
            state_location["state_event_chance"] = 0
            state_location["world_events"] = []
            state_location["state_events"] = []
            state_location["encounters"] = []

    def test_scripted_regression_playthrough(self) -> None:
        profile = {
            "name": "TestHero",
            "gender": "woman",
            "race": "elf",
            "player_class": "mage",
            "background": "shrine_touched",
            "bio": "Running a regression playthrough.",
        }
        game = Game(data_dir="data", player_name="TestHero", character_profile=profile)
        game.save_path = self.SAVE_PATH
        self._disable_dynamic_events(game)

        help_output = game.process_command("help")
        self.assertTrue(help_output.startswith("Valerion Commands"))
        map_output = game.process_command("map")
        self.assertIn("Village Square", map_output)
        search_output = game.process_command("search area")
        self.assertIn("Visible items", search_output)
        stats_output = game.process_command("stats")
        self.assertIn("Player Stats", stats_output)
        skills_output = game.process_command("skills")
        self.assertIn("Swordsmanship", skills_output)
        abilities_output = game.process_command("abilities")
        self.assertIn("Firebolt", abilities_output)
        inventory_output = game.process_command("inventory")
        self.assertIn("Backpack", inventory_output)
        gear_output = game.process_command("gear")
        self.assertIn("Gear", gear_output)
        story_output = game.process_command("story")
        self.assertIn("Arc", story_output)
        recap_output = game.process_command("recap")
        self.assertIn("Active", recap_output)
        history_output = game.process_command("history")
        self.assertIn("History", history_output)
        world_output = game.process_command("world")
        self.assertIn("World State", world_output)
        events_output = game.process_command("events")
        self.assertIn("World", events_output)
        hint_output = game.process_command("hint")
        self.assertIn("Hint", hint_output)
        reputation_output = game.process_command("reputation")
        self.assertIn("Forest Clans", reputation_output)
        factions_output = game.process_command("factions")
        self.assertIn("Forest Clans", factions_output)

        quest_accept = game.process_command("accept clear the forest path")
        self.assertIn("Quest accepted: Clear the Forest Path", quest_accept)
        quests_output = game.process_command("quests")
        self.assertIn("Clear the Forest Path", quests_output)

        natural_move = game.process_command("go to stonewatch")
        self.assertIn("Town Gate", natural_move)
        contract_move = game.process_command("move market")
        self.assertIn("Market Square", contract_move)

        board_output = game.process_command("board")
        self.assertIn("Wolfpack Culling", board_output)
        contract_accept = game.process_command("accept wolfpack culling")
        self.assertIn("Contract accepted: Wolfpack Culling", contract_accept)
        contracts_output = game.process_command("contracts")
        self.assertIn("Active contracts", contracts_output)
        invalid_accept = game.process_command("accept ghost contract")
        self.assertIn("No quests are being offered here right now", invalid_accept)

        game.process_command("move gate")
        game.process_command("move village")
        forest_move = game.process_command("go forest")
        self.assertIn("Forest Path", forest_move)

        cast_result = game.process_command("cast firebolt slime")
        self.assertIn("Firebolt", cast_result)
        self.assertIn("Quest progress", cast_result)
        invalid_fight = game.process_command("fight unicorn")
        self.assertIn("not a nearby enemy", invalid_fight)
        take_output = game.process_command("take herb")
        self.assertIn("You took", take_output)

        contract_targets = [
            ("ashwood_wolf", "ashwood wolf"),
            ("ashwood_stalker", "ashwood stalker"),
            ("ashwood_packleader", "ashwood packleader"),
        ]
        for enemy_id, query in contract_targets:
            game.world.add_enemy("forest_path", enemy_id)
            fight_output = game.process_command(f"fight {query}")
            self.assertIn("Contract progress", fight_output)
        game.process_command("move village")
        game.process_command("move stonewatch")
        game.process_command("move market")
        claim_output = game.process_command("claim wolfpack culling")
        self.assertIn("Contract claimed", claim_output)
        claim_again = game.process_command("claim wolfpack culling")
        self.assertIn("No completed contracts", claim_again)
        game.process_command("move gate")
        game.process_command("move village")
        forest_return = game.process_command("go forest")
        self.assertIn("Forest Path", forest_return)
        elite_move = game.process_command("move deeper")
        self.assertIn("Deep Forest", elite_move)
        game.world.add_enemy("deep_forest", "elite_ashwood_fanglord")
        elite_output = game.process_command("fight elite ashwood fanglord")
        self.assertIn("[ELITE] Ashwood Fanglord", elite_output)

        game.process_command("move path")
        game.process_command("move village")
        craft_output = game.process_command("craft field bandage")
        self.assertIn("Bandage Kit", craft_output)
        inventory_after_craft = game.process_command("inventory")
        self.assertIn("Bandage Kit", inventory_after_craft)
        use_output = game.process_command("use bandage kit")
        self.assertIn("Bandage Kit", use_output)

        talk_output = game.process_command("talk elder")
        self.assertIn("Elder", talk_output)
        ask_output = game.process_command("ask elder about forest")
        self.assertIn("Elder", ask_output)
        journal_output = game.process_command("journal")
        self.assertIn("Clear the Forest Path", journal_output)
        story_recent = game.process_command("story")
        self.assertIn("Arc", story_recent)
        recap_now = game.process_command("recap")
        self.assertIn("Active", recap_now)
        history_now = game.process_command("history")
        self.assertIn("History", history_now)
        hint_now = game.process_command("hint")
        self.assertIn("Hint", hint_now)
        world_now = game.process_command("world")
        self.assertIn("World State", world_now)

        invalid_move = game.process_command("move moon")
        self.assertIn("You cannot go there from here", invalid_move)
        natural_fail = game.process_command("go moon")
        self.assertIn("not a reachable path", natural_fail)

        game.player.max_hp = 70
        game.player.hp = 70
        game.player.max_focus = 20
        game.player.focus = 20
        game.player.base_attack = 6
        game.player.stats["strength"] = 14
        game.world.add_enemy("ironridge_pass", "gorgos_the_sundered")
        game.process_command("move stonewatch")
        game.process_command("move barracks")
        gorgos_travel = game.process_command("move ridge")
        self.assertIn("Ironridge Pass", gorgos_travel)
        boss_output = game.process_command("fight gorgos")
        self.assertIn("Gorgos the Sundered", boss_output)
        self.assertIn("Sundered Crest", boss_output)

        game.process_command("move barracks")
        game.process_command("move gate")
        game.process_command("move market")
        save_output = game.process_command("save")
        self.assertIn("Game saved", save_output)

        loaded = Game(data_dir="data", player_name="TestHero")
        loaded.save_path = self.SAVE_PATH
        self._disable_dynamic_events(loaded)
        load_output = loaded.process_command("load")
        self.assertIn("Game loaded", load_output)
        self._disable_dynamic_events(loaded)
        quests_after_load = loaded.process_command("quests")
        self.assertIn("Clear the Forest Path", quests_after_load)
        self.assertEqual(loaded.contracts.completed_counts.get("c001_wolfpack_culling", 0), 1)
        loaded.process_command("move stonewatch")
        loaded.process_command("move gate")
        loaded.process_command("move village")
        forest_return = loaded.process_command("go forest")
        self.assertIn("Forest Path", forest_return)
        slime_missing = loaded.process_command("fight slime")
        self.assertIn("nothing hostile", slime_missing.lower())
        loaded.process_command("move village")
        loaded.process_command("move stonewatch")
        loaded.process_command("move barracks")
        loaded.process_command("move ridge")
        boss_missing = loaded.process_command("fight gorgos")
        self.assertIn("not a nearby enemy", boss_missing.lower())
        loaded.process_command("move stonewatch")
        loaded.process_command("move gate")
        loaded.process_command("move market")
        claim_missing = loaded.process_command("claim wolfpack culling")
        self.assertIn("No completed contracts", claim_missing)
