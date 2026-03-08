from player.character import Character


class CraftingEngine:
    """Small deterministic recipe helper layered over the existing inventory system."""

    STATION_LABELS = {
        "field": "field work",
        "forge": "forge",
        "alchemy": "alchemy bench",
    }

    @staticmethod
    def _normalize(value: str) -> str:
        return str(value).strip().lower().replace("-", "_").replace(" ", "_")

    @staticmethod
    def _fallback_name(entity_id: str) -> str:
        return entity_id.replace("_", " ").title()

    def recipe_name(self, recipe_id: str, recipes_data: dict, items_data: dict) -> str:
        recipe = recipes_data.get(recipe_id, {})
        name = str(recipe.get("name", "")).strip()
        if name:
            return name
        output_id = self._normalize(recipe.get("output", ""))
        if output_id:
            return items_data.get(output_id, {}).get("name", self._fallback_name(output_id))
        return self._fallback_name(recipe_id)

    def recipe_station(self, recipe: dict) -> str:
        station = self._normalize(recipe.get("station", "field"))
        return station if station in self.STATION_LABELS else "field"

    def station_name(self, station_id: str) -> str:
        return self.STATION_LABELS.get(self._normalize(station_id), "workbench")

    def known_recipe_ids(self, player: Character, recipes_data: dict) -> list[str]:
        known = []
        for recipe_id in player.known_recipes:
            normalized = self._normalize(recipe_id)
            if normalized in recipes_data and normalized not in known:
                known.append(normalized)
        return known

    def learn_recipes_for_stations(self, player: Character, recipes_data: dict, stations: set[str]) -> list[str]:
        learned = []
        known = set(self.known_recipe_ids(player, recipes_data))
        normalized_stations = {self._normalize(station) for station in stations}
        for recipe_id, recipe in recipes_data.items():
            learn_at = recipe.get("learn_at", [])
            if isinstance(learn_at, str):
                learn_at = [learn_at]
            if not isinstance(learn_at, list):
                continue
            learn_stations = {self._normalize(station) for station in learn_at if self._normalize(station)}
            if not learn_stations or not (learn_stations & normalized_stations):
                continue
            if recipe_id in known:
                continue
            player.known_recipes.append(recipe_id)
            known.add(recipe_id)
            learned.append(recipe_id)
        player.known_recipes = Character._normalized_known_recipes(player.known_recipes)
        return learned

    def resolve_recipe(self, player: Character, query: str, recipes_data: dict, items_data: dict) -> str | None:
        normalized_query = self._normalize(query)
        if not normalized_query:
            return None

        candidates = []
        for recipe_id in self.known_recipe_ids(player, recipes_data):
            recipe = recipes_data.get(recipe_id, {})
            output_id = self._normalize(recipe.get("output", ""))
            output_name = str(items_data.get(output_id, {}).get("name", "")).strip().lower()
            recipe_name = str(recipe.get("name", "")).strip().lower()
            if normalized_query in {
                recipe_id,
                output_id,
                recipe_name.replace("-", " ").replace("_", " "),
                output_name,
            }:
                return recipe_id
            query_text = normalized_query.replace("_", " ")
            if query_text and (
                query_text in recipe_id.replace("_", " ")
                or query_text in recipe_name
                or query_text in output_name
            ):
                candidates.append(recipe_id)

        if len(candidates) == 1:
            return candidates[0]
        return None

    def recipe_cost_parts(self, recipe: dict, items_data: dict) -> list[str]:
        parts = []
        materials = recipe.get("materials", {})
        if isinstance(materials, dict):
            for item_id, amount in materials.items():
                normalized_item = self._normalize(item_id)
                count = max(1, int(amount))
                item_name = items_data.get(normalized_item, {}).get("name", self._fallback_name(normalized_item))
                parts.append(f"{count} {item_name}")
        gold_cost = max(0, int(recipe.get("gold", 0)))
        if gold_cost:
            parts.append(f"{gold_cost} gold")
        return parts

    def recipe_status(self, player: Character, recipe_id: str, recipes_data: dict, items_data: dict, stations: set[str]) -> dict:
        recipe = recipes_data.get(recipe_id, {})
        station = self.recipe_station(recipe)
        normalized_stations = {self._normalize(value) for value in stations}
        in_station = station == "field" or station in normalized_stations
        missing = []
        materials = recipe.get("materials", {})
        if isinstance(materials, dict):
            for item_id, amount in materials.items():
                normalized_item = self._normalize(item_id)
                need = max(1, int(amount))
                have = player.inventory.count(normalized_item)
                if have < need:
                    item_name = items_data.get(normalized_item, {}).get("name", self._fallback_name(normalized_item))
                    missing.append(f"{item_name} {have}/{need}")
        gold_cost = max(0, int(recipe.get("gold", 0)))
        if player.gold < gold_cost:
            missing.append(f"Gold {player.gold}/{gold_cost}")
        craftable = in_station and not missing
        return {
            "station": station,
            "in_station": in_station,
            "missing": missing,
            "craftable": craftable,
        }

    def recipes_lines(self, player: Character, recipes_data: dict, items_data: dict, stations: set[str]) -> list[str]:
        known_recipe_ids = self.known_recipe_ids(player, recipes_data)
        if not known_recipe_ids:
            return ["You do not know any recipes yet."]

        lines = ["Known Recipes"]
        for recipe_id in known_recipe_ids:
            recipe = recipes_data.get(recipe_id, {})
            output_id = self._normalize(recipe.get("output", ""))
            output_name = items_data.get(output_id, {}).get("name", self._fallback_name(output_id))
            output_count = max(1, int(recipe.get("output_count", 1)))
            output_text = f"{output_count}x {output_name}" if output_count > 1 else output_name
            cost_text = ", ".join(self.recipe_cost_parts(recipe, items_data)) or "no cost"
            station = self.recipe_station(recipe)
            status = self.recipe_status(player, recipe_id, recipes_data, items_data, stations)
            if status["craftable"]:
                status_text = "ready"
            elif not status["in_station"]:
                status_text = f"needs {self.station_name(station)}"
            else:
                status_text = "missing " + ", ".join(status["missing"])
            lines.append(f"- {output_text}: {cost_text} | {status_text}")
        lines.append("Use 'craft <item>' when you have the materials and the right workspace.")
        return lines

    def craft(self, player: Character, recipe_id: str, recipes_data: dict, items_data: dict, stations: set[str]) -> tuple[bool, str, str | None]:
        recipe = recipes_data.get(recipe_id, {})
        if not recipe:
            return False, "That recipe does not exist.", None

        status = self.recipe_status(player, recipe_id, recipes_data, items_data, stations)
        station = self.recipe_station(recipe)
        if not status["in_station"]:
            return False, f"You need a {self.station_name(station)} to craft that.", None
        if status["missing"]:
            return False, "You lack the materials: " + ", ".join(status["missing"]) + ".", None

        materials = recipe.get("materials", {})
        if isinstance(materials, dict):
            for item_id, amount in materials.items():
                normalized_item = self._normalize(item_id)
                for _ in range(max(1, int(amount))):
                    player.inventory.remove(normalized_item)

        gold_cost = max(0, int(recipe.get("gold", 0)))
        if gold_cost:
            player.gold -= gold_cost

        output_id = self._normalize(recipe.get("output", ""))
        output_count = max(1, int(recipe.get("output_count", 1)))
        for _ in range(output_count):
            player.inventory.append(output_id)

        output_name = items_data.get(output_id, {}).get("name", self._fallback_name(output_id))
        created_text = f"{output_count} {output_name}" if output_count > 1 else output_name
        return True, f"Crafted {created_text}. Gold left: {player.gold}.", output_id
