from player.character import Character


class FactionEngine:
    """Deterministic faction reputation and NPC-relation helpers."""

    def __init__(self, factions_data: dict):
        self.factions = factions_data

    @staticmethod
    def _fallback_name(entity_id: str) -> str:
        return str(entity_id).replace("_", " ").title()

    @staticmethod
    def _clamp(value: int) -> int:
        return max(-100, min(100, int(value)))

    def faction_name(self, faction_id: str) -> str:
        normalized = str(faction_id).strip().lower()
        return self.factions.get(normalized, {}).get("name", self._fallback_name(normalized))

    def faction_description(self, faction_id: str) -> str:
        normalized = str(faction_id).strip().lower()
        return self.factions.get(normalized, {}).get("description", "No faction record available.")

    @staticmethod
    def tier_name(score: int) -> str:
        value = int(score)
        if value <= -60:
            return "hostile"
        if value <= -20:
            return "disliked"
        if value < 20:
            return "neutral"
        if value < 60:
            return "friendly"
        return "allied"

    def ensure_player_state(self, player: Character) -> None:
        for faction_id in self.factions:
            if faction_id not in player.faction_reputation:
                player.faction_reputation[faction_id] = 0

    def adjust_reputation(self, player: Character, faction_id: str, amount: int) -> dict | None:
        normalized = str(faction_id).strip().lower()
        if not normalized or normalized not in self.factions:
            return None

        before = player.reputation_value(normalized)
        after = player.adjust_reputation(normalized, amount)
        change = after - before
        if change == 0:
            return None
        return {
            "faction_id": normalized,
            "name": self.faction_name(normalized),
            "before": before,
            "after": after,
            "change": change,
            "tier": self.tier_name(after),
        }

    def reputation_lines(self, player: Character) -> list[str]:
        self.ensure_player_state(player)
        lines = ["Reputation"]
        for faction_id in self.factions:
            score = player.reputation_value(faction_id)
            lines.append(f"- {self.faction_name(faction_id)}: {score} ({self.tier_name(score)})")
        return lines

    def faction_lines(self, player: Character) -> list[str]:
        self.ensure_player_state(player)
        lines = ["Factions"]
        for faction_id in self.factions:
            score = player.reputation_value(faction_id)
            lines.append(
                f"- {self.faction_name(faction_id)}: {score} ({self.tier_name(score)}) | "
                f"{self.faction_description(faction_id)}"
            )
        return lines

    def relations_lines(self, player: Character, npcs_data: dict) -> list[str]:
        lines = ["Relations"]
        visible = False
        for npc_id, npc_data in npcs_data.items():
            if not npc_data.get("important", False):
                continue
            visible = True
            memory = player.ensure_npc_memory(npc_id, faction_id=npc_data.get("faction", ""))
            trust = int(memory.get("trust", 0))
            quests_completed = memory.get("quests_completed", [])
            helped = int(memory.get("helped", 0))
            harmed = int(memory.get("harmed", 0))
            faction_id = str(memory.get("faction", "")).strip().lower()
            faction_name = self.faction_name(faction_id) if faction_id else "Unaffiliated"
            lines.append(
                f"- {npc_data.get('name', self._fallback_name(npc_id))}: "
                f"trust {trust} ({self.tier_name(trust)}), faction {faction_name}, "
                f"quests {len(quests_completed)}, helped {helped}, harmed {harmed}"
            )
        if not visible:
            lines.append("No important NPC relations tracked yet.")
        return lines

    def dialogue_note(self, player: Character, npc_id: str, npc_data: dict) -> str:
        memory = player.ensure_npc_memory(npc_id, faction_id=npc_data.get("faction", ""))
        trust = int(memory.get("trust", 0))
        faction_id = str(memory.get("faction", "")).strip().lower()
        helped = int(memory.get("helped", 0))
        harmed = int(memory.get("harmed", 0))
        quests_completed = len(memory.get("quests_completed", []))

        notes = []
        if quests_completed:
            notes.append(f"They remember {quests_completed} quest{'s' if quests_completed != 1 else ''} you completed for them.")
        if helped > harmed and helped > 0:
            notes.append("Your past help still matters to them.")
        elif harmed > helped and harmed > 0:
            notes.append("They have not forgotten the harm you caused.")
        notes.append(f"Trust: {self.tier_name(trust)}.")
        if faction_id:
            rep = player.reputation_value(faction_id)
            notes.append(f"{self.faction_name(faction_id)} standing: {self.tier_name(rep)}.")
        return " ".join(notes)

    def service_access(self, player: Character, faction_id: str, npc_id: str | None = None) -> tuple[bool, str]:
        rep = player.reputation_value(faction_id)
        trust = player.npc_trust(npc_id) if npc_id else 0
        if rep <= -60:
            return False, f"Service denied: {self.faction_name(faction_id)} considers you hostile."
        if npc_id and trust <= -40:
            return False, "Service denied: that NPC does not trust you enough."
        return True, ""

    def price_for_service(self, player: Character, faction_id: str, npc_id: str | None, base_cost: int) -> int:
        rep = player.reputation_value(faction_id)
        trust = player.npc_trust(npc_id) if npc_id else 0
        multiplier = 1.0

        if rep >= 60:
            multiplier -= 0.25
        elif rep >= 20:
            multiplier -= 0.10
        elif rep <= -60:
            multiplier += 0.50
        elif rep <= -20:
            multiplier += 0.20

        if trust >= 40:
            multiplier -= 0.10
        elif trust >= 10:
            multiplier -= 0.05
        elif trust <= -40:
            multiplier += 0.15
        elif trust <= -10:
            multiplier += 0.05

        return max(1, int(round(int(base_cost) * multiplier)))

    def encounter_modifiers(self, player: Character, location_id: str) -> list[dict]:
        normalized_location = str(location_id).strip().lower()
        modifiers = []

        if normalized_location in {"village_square", "forest_path", "river_crossing", "old_watchtower"}:
            if player.reputation_value("merchant_guild") >= 20:
                modifiers.append({"type": "npc", "target": "merchant", "weight": 25})
            if player.reputation_value("kingdom_guard") <= -20:
                modifiers.append({"type": "enemy", "target": "thief", "weight": 30})

        if normalized_location in {"bandit_camp", "river_crossing", "forest_path"}:
            if player.reputation_value("thieves_circle") >= 20:
                modifiers.append({"type": "enemy", "target": "thief", "weight": 15})

        if normalized_location in {"ruined_shrine", "whispering_cave", "old_ruins"}:
            if player.reputation_value("cult_of_ash") <= -20:
                modifiers.append({"type": "enemy", "target": "cultist", "weight": 30})

        if normalized_location in {"forest_path", "deep_forest", "river_crossing"}:
            if player.reputation_value("forest_clans") >= 20:
                modifiers.append({"type": "npc", "target": "traveler", "weight": 20})

        return modifiers
