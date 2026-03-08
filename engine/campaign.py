class CampaignEngine:
    """Evaluates lightweight campaign arcs from deterministic game state."""

    def __init__(self, arcs_data: dict):
        self.arcs = []
        if isinstance(arcs_data, dict):
            for arc_id, raw in arcs_data.items():
                if not isinstance(raw, dict):
                    continue
                self.arcs.append(
                    {
                        "id": str(arc_id).strip().lower(),
                        "index": max(1, int(raw.get("index", len(self.arcs) + 1))),
                        "title": str(raw.get("title", arc_id)).strip(),
                        "note": str(raw.get("note", "")).strip(),
                        "tone": str(raw.get("tone", "")).strip().lower(),
                        "scene_focus": str(raw.get("scene_focus", "")).strip(),
                        "requires_all": list(raw.get("requires_all", [])) if isinstance(raw.get("requires_all", []), list) else [],
                        "requires_any": list(raw.get("requires_any", [])) if isinstance(raw.get("requires_any", []), list) else [],
                    }
                )
        self.arcs.sort(key=lambda arc: arc["index"])
        self.arc_index_by_id = {arc["id"]: int(arc["index"]) for arc in self.arcs}

    def current_arc(self, player, quests) -> dict:
        if not self.arcs:
            return {
                "id": "arc_1_village_roads",
                "index": 1,
                "title": "Arc 1: Village Roads",
                "note": "Secure the nearby roads and keep moving forward.",
                "tone": "grounded",
                "scene_focus": "The dangers still feel local and immediate.",
            }

        current = self.arcs[0]
        for arc in self.arcs:
            if self._arc_unlocked(player, quests, arc):
                current = arc

        next_arc = None
        for arc in self.arcs:
            if int(arc["index"]) > int(current["index"]):
                next_arc = arc
                break

        result = dict(current)
        if next_arc:
            result["next_title"] = next_arc["title"]
            result["next_index"] = next_arc["index"]
        else:
            result["next_title"] = ""
            result["next_index"] = current["index"]
        result["arc_indices"] = dict(self.arc_index_by_id)
        return result

    def arc_index(self, arc_id: str) -> int:
        return int(self.arc_index_by_id.get(str(arc_id).strip().lower(), 0))

    def _arc_unlocked(self, player, quests, arc: dict) -> bool:
        requires_all = arc.get("requires_all", [])
        requires_any = arc.get("requires_any", [])

        if requires_all and not all(self._condition_met(player, quests, requirement) for requirement in requires_all):
            return False
        if requires_any and not any(self._condition_met(player, quests, requirement) for requirement in requires_any):
            return False
        return True

    def _condition_met(self, player, quests, requirement: dict) -> bool:
        if not isinstance(requirement, dict):
            return True

        requirement_type = str(requirement.get("type", "")).strip().lower()
        if not requirement_type:
            return True

        if requirement_type == "quest_completed":
            quest_id = str(requirement.get("quest_id", "")).strip().lower()
            return bool(quest_id) and quest_id in getattr(quests, "completed", set())

        if requirement_type == "location_visited":
            location_id = str(requirement.get("location_id", "")).strip().lower()
            return bool(location_id) and player.has_event("location_visited", "location_id", location_id)

        if requirement_type == "enemy_defeated":
            enemy_id = str(requirement.get("enemy_id", "")).strip().lower()
            return bool(enemy_id) and player.has_event("enemy_defeated", "enemy_id", enemy_id)

        if requirement_type == "miniboss_defeated":
            enemy_id = str(requirement.get("enemy_id", "")).strip().lower()
            return bool(enemy_id) and player.has_event("miniboss_defeated", "enemy_id", enemy_id)

        if requirement_type == "important_item_acquired":
            item_id = str(requirement.get("item_id", "")).strip().lower()
            return bool(item_id) and player.has_event("important_item_acquired", "item_id", item_id)

        if requirement_type == "inventory_has_item":
            item_id = str(requirement.get("item_id", "")).strip().lower()
            return bool(item_id) and item_id in getattr(player, "inventory", [])

        if requirement_type == "reputation_at_least":
            faction_id = str(requirement.get("faction", "")).strip().lower()
            threshold = int(requirement.get("value", requirement.get("min", 0)))
            return bool(faction_id) and player.reputation_value(faction_id) >= threshold

        if requirement_type == "event":
            event_type = str(requirement.get("event_type", "")).strip().lower()
            detail_key = requirement.get("detail_key")
            detail_value = requirement.get("detail_value")
            if not event_type:
                return True
            if detail_key is None:
                return player.has_event(event_type)
            return player.has_event(event_type, str(detail_key), detail_value)

        return False
