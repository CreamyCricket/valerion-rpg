from typing import TYPE_CHECKING

from ai.intent_parser import IntentParseResult
from ai.narrator import Narrator

if TYPE_CHECKING:
    from engine.game import Game


class ActionRouter:
    """Validate natural-language action intents before calling deterministic handlers."""

    ACTION_INTENTS = {"move", "fight", "take", "use"}

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

        if not parsed.target:
            return Narrator.action_router_fallback_text(
                raw_text,
                "you are not sure where to go. Try: " + ", ".join(exits.keys()) + ".",
            )

        location_id = game.world.find_connected_location(game.current_location, parsed.target)
        if not location_id:
            return Narrator.action_router_fallback_text(
                raw_text,
                f"'{parsed.target}' is not a reachable path from here. Try: " + ", ".join(exits.keys()) + ".",
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
                "you are not sure what to fight. Try: " + ", ".join(enemy_names) + ".",
            )

        enemy_id = game.world.find_enemy_at_location(game.current_location, parsed.target)
        if not enemy_id:
            return Narrator.action_router_fallback_text(
                raw_text,
                f"'{parsed.target}' is not a nearby enemy. Try: " + ", ".join(enemy_names) + ".",
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
                "you are not sure what to take. Try: " + ", ".join(item_names) + ".",
            )

        item_id = game.world.find_item_at_location(game.current_location, parsed.target)
        if not item_id:
            return Narrator.action_router_fallback_text(
                raw_text,
                f"'{parsed.target}' is not here to pick up. Try: " + ", ".join(item_names) + ".",
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
                "you are not sure what to use. Try: " + ", ".join(item_names) + ".",
            )

        item_id = game.inventory.find_item_in_inventory(game.player, game.world.items, parsed.target)
        if not item_id:
            return Narrator.action_router_fallback_text(
                raw_text,
                f"'{parsed.target}' is not in your backpack. Try: " + ", ".join(item_names) + ".",
            )

        return game._cmd_use(item_id)
