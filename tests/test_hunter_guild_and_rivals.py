import random
import tempfile
import unittest

from engine.game import Game


class HunterGuildAndRivalsTests(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(131)

    @staticmethod
    def _disable_location_dynamic_events(game: Game) -> None:
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
    def _force_road_encounter(game: Game, encounter_id: str) -> None:
        encounter = None
        for entry in game.world.road_encounters.get("encounters", []):
            if str(entry.get("encounter_id", "")).strip().lower() == encounter_id:
                encounter = dict(entry)
                break
        if encounter is None:
            raise AssertionError(f"Missing road encounter fixture: {encounter_id}")
        encounter["weight"] = 100
        game.world.road_encounters = {"meta": {"travel_chance": 100}, "encounters": [encounter]}

    def test_guild_rank_progression_route_gate_and_rival_reaction(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game = Game(data_dir="data", player_name="Hunter", save_root=tmpdir)
            self._disable_location_dynamic_events(game)
            game.world.road_encounters["meta"]["travel_chance"] = 0
            game.player.gold = 40
            game.player.faction_reputation["merchant_guild"] = 8

            game.process_command("move stonewatch")
            game.process_command("move market")
            base_dialogue = game.process_command("talk dessa")
            self.assertIn("Dessa wears confidence", base_dialogue)

            travel_to_stormbreak = game.process_command("travel stormbreak")
            self.assertIn("Stormbreak", travel_to_stormbreak)
            routes_before = game.process_command("routes")
            self.assertIn("Valewood", routes_before)
            self.assertIn("Locked:", routes_before)

            game.contracts.completed_counts["c001_wolfpack_culling"] = 1
            game.contracts.completed_counts["c005_corrupted_grove"] = 1
            rank_lines = game._refresh_hunter_guild_rank(source="test_progression")
            self.assertTrue(any("Bronze" in line for line in rank_lines))
            self.assertEqual(game.player.hunter_guild_rank, "Bronze")

            routes_after = game.process_command("routes")
            self.assertIn("Valewood", routes_after)
            self.assertNotIn("Locked:", routes_after)

            game.contracts.completed_counts["c008_alpha_on_ashwood_trail"] = 1
            game.player.record_event("quest_completed", {"quest_id": "q005_sigil_for_the_caretaker"})
            game.player.record_event("enemy_defeated", {"enemy_id": "vorgar_ironfang_alpha"})
            game._refresh_hunter_guild_rank(source="test_progression")
            self.assertEqual(game.player.hunter_guild_rank, "Silver")

            game.process_command("travel stonewatch")
            game.process_command("move market")
            rival_reaction = game.process_command("talk dessa")
            self.assertIn("Silver", rival_reaction)
            self.assertTrue(game.player.rival_hunter_flags.get("dessa", {}).get("met"))

            stats_output = game.process_command("stats")
            self.assertIn("Hunter Guild: Silver", stats_output)
            recap_output = game.process_command("recap")
            self.assertIn("Hunter Guild rank: Silver", recap_output)

    def test_save_load_preserves_guild_rank_and_active_road_encounter(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            game = Game(data_dir="data", player_name="HunterSave", save_root=tmpdir)
            self._disable_location_dynamic_events(game)
            self._force_road_encounter(game, "road_bandit_ambush")
            game.player.gold = 40
            game.contracts.completed_counts["c001_wolfpack_culling"] = 1
            game.contracts.completed_counts["c005_corrupted_grove"] = 1
            game._refresh_hunter_guild_rank(source="test_progression")

            game.process_command("move stonewatch")
            game.process_command("move market")
            game.process_command("talk dessa")
            travel_output = game.process_command("travel stormbreak")
            self.assertIn("Road encounter: Bandit Ambush.", travel_output)
            self.assertEqual(game.player.hunter_guild_rank, "Bronze")
            self.assertEqual(game.world.active_road_encounter.get("enemy_id"), "bandit_raider")

            save_output = game.process_command("save")
            self.assertIn("Game saved", save_output)

            reloaded = Game(data_dir="data", player_name="HunterSave", save_root=tmpdir)
            self._disable_location_dynamic_events(reloaded)
            load_output = reloaded.process_command("load")
            self.assertIn("Game loaded", load_output)
            self.assertEqual(reloaded.player.hunter_guild_rank, "Bronze")
            self.assertEqual(reloaded.world.active_road_encounter.get("enemy_id"), "bandit_raider")
            self.assertIn("bandit_raider", reloaded.world.get_enemies_at("stormbreak"))
            self.assertTrue(reloaded.player.rival_hunter_flags.get("dessa", {}).get("met"))


if __name__ == "__main__":
    unittest.main()
