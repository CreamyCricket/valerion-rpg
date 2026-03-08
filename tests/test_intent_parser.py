import unittest
import random

from ai.intent_parser import IntentParser
from engine.game import Game


class IntentParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = IntentParser()

    def test_read_only_examples_parse_into_structured_results(self) -> None:
        cases = {
            "look around": {"intent": "observe", "target": "area", "topic": "", "safe": True},
            "inspect the shrine altar": {"intent": "inspect", "target": "shrine altar", "topic": "", "safe": True},
            "ask the elder about the forest": {"intent": "ask", "target": "elder", "topic": "forest", "safe": True},
            "listen for movement": {"intent": "listen", "target": "movement", "topic": "", "safe": True},
        }

        for text, expected in cases.items():
            with self.subTest(text=text):
                parsed = self.parser.parse(text)
                self.assertEqual(parsed.intent, expected["intent"])
                self.assertEqual(parsed.target, expected["target"])
                self.assertEqual(parsed.topic, expected["topic"])
                self.assertEqual(parsed.safe, expected["safe"])

    def test_action_examples_parse_into_validated_action_intents(self) -> None:
        cases = {
            "go to the forest": {"intent": "move", "target": "forest"},
            "attack the slime": {"intent": "fight", "target": "slime"},
            "pick up the herb": {"intent": "take", "target": "herb"},
            "drink the potion": {"intent": "use", "target": "potion"},
        }

        for text, expected in cases.items():
            with self.subTest(text=text):
                parsed = self.parser.parse(text)
                self.assertEqual(parsed.intent, expected["intent"])
                self.assertEqual(parsed.target, expected["target"])
                self.assertFalse(parsed.safe)

    def test_action_parser_cleans_extra_natural_language_fillers(self) -> None:
        cases = {
            "go toward the forest please": ("move", "forest"),
            "engage the green slime": ("fight", "green slime"),
            "pick the herb up": ("take", "herb"),
            "drink my potion": ("use", "potion"),
        }

        for text, expected in cases.items():
            with self.subTest(text=text):
                parsed = self.parser.parse(text)
                self.assertEqual((parsed.intent, parsed.target), expected)

    def test_ask_about_topic_does_not_treat_topic_as_npc(self) -> None:
        parsed = self.parser.parse("ask about the forest")
        self.assertEqual(parsed.intent, "ask")
        self.assertEqual(parsed.target, "")
        self.assertEqual(parsed.topic, "forest")

    def test_watch_scan_and_survey_for_phrases_stay_observe(self) -> None:
        cases = {
            "watch for movement": "movement",
            "scan for tracks": "tracks",
            "survey for threats": "threats",
        }

        for text, target in cases.items():
            with self.subTest(text=text):
                parsed = self.parser.parse(text)
                self.assertEqual(parsed.intent, "observe")
                self.assertEqual(parsed.target, target)

    def test_greeting_fillers_do_not_create_fake_targets(self) -> None:
        parsed = self.parser.parse("hello there")
        self.assertEqual(parsed.intent, "greet")
        self.assertEqual(parsed.target, "")


class GameIntentRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(1)

    def _snapshot(self, game: Game) -> dict:
        return {
            "location": game.current_location,
            "hp": game.player.hp,
            "gold": game.player.gold,
            "inventory": tuple(game.player.inventory),
            "events": len(game.player.event_log),
            "running": game.running,
            "world": {
                location_id: {
                    "items": tuple(game.world.get_items_at(location_id)),
                    "enemies": tuple(game.world.get_enemies_at(location_id)),
                }
                for location_id in game.world.locations
            },
        }

    def test_safe_free_text_does_not_mutate_state(self) -> None:
        game = Game(data_dir="data", player_name="Tester")
        before = self._snapshot(game)

        outputs = [
            game.process_command("look around"),
            game.process_command("ask the elder about the forest"),
            game.process_command("greet the elder"),
            game.process_command("listen for movement"),
            game.process_command("inspect the village elder"),
            game.process_command("attack the slime"),
            game.process_command("pick up the herb"),
            game.process_command("drink the potion"),
            game.process_command("go to the mountain"),
        ]

        after = self._snapshot(game)
        self.assertEqual(before, after)
        self.assertTrue(any('You try to "' in output for output in outputs))

    def test_validated_natural_language_actions_route_to_existing_handlers(self) -> None:
        game = Game(data_dir="data", player_name="Tester")

        move_output = game.process_command("go to the forest")
        take_output = game.process_command("pick up the herb")
        fight_output = game.process_command("attack the slime")

        game.player.inventory.append("potion")
        use_output = game.process_command("drink the potion")

        self.assertIn("You travel to Forest Path.", move_output)
        self.assertIn("You took Herb.", take_output)
        self.assertIn("You engage Green Slime in battle.", fight_output)
        self.assertIn("You used Potion", use_output)
        self.assertEqual(game.current_location, "forest_path")
        self.assertNotIn("slime", game.world.get_enemies_at("forest_path"))
        self.assertIn("herb", game.player.inventory)
        self.assertNotIn("potion", game.player.inventory)

    def test_ambiguous_or_invalid_natural_language_actions_do_not_change_state(self) -> None:
        game = Game(data_dir="data", player_name="Tester")
        game.process_command("go to the forest")
        game.player.inventory.extend(["potion", "greater_potion"])
        before = self._snapshot(game)

        invalid_move = game.process_command("go to the sea")
        ambiguous_use = game.process_command("drink pot")

        after = self._snapshot(game)
        self.assertEqual(before, after)
        self.assertIn("Nothing changes yet.", invalid_move)
        self.assertIn("Nothing changes yet.", ambiguous_use)

    def test_single_word_classic_commands_keep_existing_behavior(self) -> None:
        game = Game(data_dir="data", player_name="Tester")
        self.assertIn("Move where?", game.process_command("move"))
        self.assertIn("Use what?", game.process_command("use"))

    def test_npc_aliases_route_to_existing_npcs(self) -> None:
        game = Game(data_dir="data", player_name="Tester")

        elder_output = game.process_command("inspect the village elder")
        merchant_output = game.process_command("talk to the shopkeeper")

        self.assertIn("You inspect Elder in Village Square.", elder_output)
        self.assertIn("The Merchant", merchant_output)

    def test_lore_aliases_work_for_watchtower_objects(self) -> None:
        game = Game(data_dir="data", player_name="Tester")
        game.process_command("move forest")
        game.process_command("move tower")

        journal_output = game.process_command("read the captain's log")
        memorial_output = game.process_command("study the memorial")

        self.assertIn("You inspect the watchtower journal.", journal_output)
        self.assertIn("You inspect the memorial plaque.", memorial_output)


if __name__ == "__main__":
    unittest.main()
