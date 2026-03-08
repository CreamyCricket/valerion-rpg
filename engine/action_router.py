from typing import TYPE_CHECKING

from ai.intent_parser import IntentParseResult
from ai.narrator import Narrator

if TYPE_CHECKING:
    from engine.game import Game


class ActionRouter:
    """Validate natural-language action intents before calling deterministic handlers."""

    ACTION_INTENTS = {"move", "fight", "take", "use"}

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(str(text).strip().lower().split())

    def _resolve_target(self, query: str, choices: list[dict]) -> tuple[str | None, str | None]:
        normalized_query = self._normalize(query)
        if not normalized_query:
            return None, None

        exact_matches = []
        partial_matches = []
        for choice in choices:
            candidate_id = self._normalize(choice.get("id", ""))
            if not candidate_id:
                continue

            aliases = {candidate_id}
            aliases.update(self._normalize(alias) for alias in choice.get("aliases", []))

            if normalized_query in aliases:
                exact_matches.append(candidate_id)
                continue

            if any(normalized_query in alias or alias in normalized_query for alias in aliases):
                partial_matches.append(candidate_id)

        unique_exact = self._unique_matches(exact_matches)
        if len(unique_exact) == 1:
            return unique_exact[0], None
        if len(unique_exact) > 1:
            return None, "ambiguous"

        unique_partial = self._unique_matches(partial_matches)
        if len(unique_partial) == 1:
            return unique_partial[0], None
        if len(unique_partial) > 1:
            return None, "ambiguous"
        return None, "missing"

    @staticmethod
    def _unique_matches(matches: list[str]) -> list[str]:
        unique = []
        for match in matches:
            if match not in unique:
                unique.append(match)
        return unique

    @staticmethod
    def _format_options(options: list[str]) -> str:
        return ", ".join(options)

    def route(self, game: "Game", parsed: IntentParseResult, raw_text: str) -> str | None:
        if parsed.intent == "move":
            return self._route_move(game, parsed, raw_text)
        if parsed.intent == "fight":
            return self._route_fight(game, parsed, raw_text)
        if parsed.intent == "take":
            return self._route_take(game, parsed, raw_text)
        if parsed.intent == "use":
            return self._route_use(game, parsed, raw_text)
        return None

    def _route_move(self, game: "Game", parsed: IntentParseResult, raw_text: str) -> str:
        exits = game.world.get_location(game.current_location).get("connected_locations", {})
        if not exits:
            return Narrator.action_router_fallback_text(raw_text, "there is nowhere to go from here.")

        exit_options = list(exits.keys())
        location_options = []
        for direction, target_id in exits.items():
            location_name = game.world.get_location(target_id).get("name", target_id)
            location_options.append(
                {
                    "id": target_id,
                    "aliases": [direction, location_name],
                }
            )

        if not parsed.target:
            return Narrator.action_router_fallback_text(
                raw_text,
                "you are not sure where to go. Try: " + self._format_options(exit_options) + ".",
            )

        location_id, status = self._resolve_target(parsed.target, location_options)
        if status == "ambiguous":
            return Narrator.action_router_fallback_text(
                raw_text,
                "more than one path fits that. Try: " + self._format_options(exit_options) + ".",
            )
        if not location_id:
            return Narrator.action_router_fallback_text(
                raw_text,
                f"'{parsed.target}' is not a reachable path from here. Try: " + self._format_options(exit_options) + ".",
            )

        return game._cmd_move(location_id)

    def _route_fight(self, game: "Game", parsed: IntentParseResult, raw_text: str) -> str:
        enemies_here = game.world.get_enemies_at(game.current_location)
        if not enemies_here:
            return Narrator.action_router_fallback_text(raw_text, "there is nothing hostile here to fight.")

        enemy_names = [game.world.enemy_name(enemy_id) for enemy_id in enemies_here]
        if not parsed.target:
            return Narrator.action_router_fallback_text(
                raw_text,
                "you are not sure what to fight. Try: " + self._format_options(enemy_names) + ".",
            )

        enemy_options = [
            {
                "id": enemy_id,
                "aliases": [game.world.enemy_name(enemy_id)],
            }
            for enemy_id in enemies_here
        ]
        enemy_id, status = self._resolve_target(parsed.target, enemy_options)
        if status == "ambiguous":
            return Narrator.action_router_fallback_text(
                raw_text,
                "more than one nearby threat fits that. Try: " + self._format_options(enemy_names) + ".",
            )
        if not enemy_id:
            return Narrator.action_router_fallback_text(
                raw_text,
                f"'{parsed.target}' is not a nearby enemy. Try: " + self._format_options(enemy_names) + ".",
            )

        return game._cmd_fight(enemy_id)

    def _route_take(self, game: "Game", parsed: IntentParseResult, raw_text: str) -> str:
        items_here = game.world.get_items_at(game.current_location)
        if not items_here:
            return Narrator.action_router_fallback_text(raw_text, "there is nothing here to take.")

        item_names = [game.world.item_name(item_id) for item_id in items_here]
        if not parsed.target:
            return Narrator.action_router_fallback_text(
                raw_text,
                "you are not sure what to take. Try: " + self._format_options(item_names) + ".",
            )

        item_options = [
            {
                "id": item_id,
                "aliases": [game.world.item_name(item_id)],
            }
            for item_id in items_here
        ]
        item_id, status = self._resolve_target(parsed.target, item_options)
        if status == "ambiguous":
            return Narrator.action_router_fallback_text(
                raw_text,
                "more than one item fits that. Try: " + self._format_options(item_names) + ".",
            )
        if not item_id:
            return Narrator.action_router_fallback_text(
                raw_text,
                f"'{parsed.target}' is not here to pick up. Try: " + self._format_options(item_names) + ".",
            )

        return game._cmd_take(item_id)

    def _route_use(self, game: "Game", parsed: IntentParseResult, raw_text: str) -> str:
        inventory_items = game.player.inventory
        if not inventory_items:
            return Narrator.action_router_fallback_text(raw_text, "your backpack is empty.")

        item_names = [game.world.item_name(item_id) for item_id in inventory_items]
        if not parsed.target:
            return Narrator.action_router_fallback_text(
                raw_text,
                "you are not sure what to use. Try: " + self._format_options(item_names) + ".",
            )

        item_options = [
            {
                "id": item_id,
                "aliases": [game.world.item_name(item_id)],
            }
            for item_id in inventory_items
        ]
        item_id, status = self._resolve_target(parsed.target, item_options)
        if status == "ambiguous":
            return Narrator.action_router_fallback_text(
                raw_text,
                "more than one backpack item fits that. Try: " + self._format_options(item_names) + ".",
            )
        if not item_id:
            return Narrator.action_router_fallback_text(
                raw_text,
                f"'{parsed.target}' is not in your backpack. Try: " + self._format_options(item_names) + ".",
            )

        return game._cmd_use(item_id)
