import copy
import json
from pathlib import Path


class World:
    """Static data loader and persisting location/enemy/item runtime state."""
    DUNGEON_TIERS = {
        "E": {
            "label": "Rank E",
            "level_range": [1, 2],
            "families": ["slimes", "wolves", "bandits"],
            "boss_weight": 4,
            "loot_band": "Common to Uncommon",
            "event_risk": "Low",
            "world_event_bonus": 0,
            "world_event_dc_bonus": 0,
            "state_event_bonus": 2,
        },
        "D": {
            "label": "Rank D",
            "level_range": [2, 3],
            "families": ["wolves", "bandits", "shrine_creatures", "cultists"],
            "boss_weight": 6,
            "loot_band": "Common to Uncommon",
            "event_risk": "Guarded",
            "world_event_bonus": 2,
            "world_event_dc_bonus": 1,
            "state_event_bonus": 3,
        },
        "C": {
            "label": "Rank C",
            "level_range": [3, 4],
            "families": ["bandits", "cultists", "spiders"],
            "boss_weight": 10,
            "loot_band": "Uncommon to Rare",
            "event_risk": "Elevated",
            "world_event_bonus": 4,
            "world_event_dc_bonus": 1,
            "state_event_bonus": 5,
        },
        "B": {
            "label": "Rank B",
            "level_range": [4, 5],
            "families": ["cultists", "shrine_creatures", "ruin_guardians"],
            "boss_weight": 14,
            "loot_band": "Rare",
            "event_risk": "High",
            "world_event_bonus": 6,
            "world_event_dc_bonus": 2,
            "state_event_bonus": 6,
        },
        "A": {
            "label": "Rank A",
            "level_range": [5, 6],
            "families": ["ruin_guardians", "abyss_beasts", "ash_heralds"],
            "boss_weight": 18,
            "loot_band": "Rare to Epic",
            "event_risk": "Severe",
            "world_event_bonus": 8,
            "world_event_dc_bonus": 2,
            "state_event_bonus": 8,
        },
    }

    def __init__(self, data_dir: str = "data"):
        base = Path(data_dir)
        self.locations = self._load_json(base / "locations.json")
        self.enemies = self._load_json(base / "enemies.json")
        self.items = self._load_json(base / "items.json")
        self.contracts = self._load_json(base / "contracts.json")
        self.recipes = self._load_json(base / "recipes.json")
        self.npcs = self._load_json(base / "npcs.json")
        self.quests = self._load_json(base / "quests.json")
        self.factions = self._load_json(base / "factions.json")
        self.arcs = self._load_json(base / "arcs.json")

        # Runtime world state. Locations change when items are taken or enemies are defeated.
        self.state_locations = copy.deepcopy(self.locations)
        self.state_events = self._default_events()
        self.location_states = {location_id: [] for location_id in self.locations}
        self.starting_location = "village_square"

    @staticmethod
    def _load_json(path: Path) -> dict:
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError as exc:
            raise ValueError(f"Missing required game data file: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in game data file: {path}") from exc

    def get_location(self, location_id: str) -> dict:
        return self.state_locations[location_id]

    def get_enemies_at(self, location_id: str) -> list[str]:
        return self.get_location(location_id).get("enemies", [])

    def get_items_at(self, location_id: str) -> list[str]:
        return self.get_location(location_id).get("items", [])

    def get_npcs_at(self, location_id: str) -> list[str]:
        return self.get_location(location_id).get("npcs", [])

    @staticmethod
    def _normalize_entity_id(entity_id: str) -> str:
        return str(entity_id).strip().lower()

    def has_enemy(self, enemy_id: str) -> bool:
        return self._normalize_entity_id(enemy_id) in self.enemies

    def has_item(self, item_id: str) -> bool:
        return self._normalize_entity_id(item_id) in self.items

    def has_npc(self, npc_id: str) -> bool:
        return self._normalize_entity_id(npc_id) in self.npcs

    def filter_encounter_entries(self, entries: list[dict]) -> list[dict]:
        filtered = []
        if not isinstance(entries, list):
            return filtered

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            encounter_type = self._normalize_entity_id(entry.get("type", ""))
            target = self._normalize_entity_id(entry.get("target", ""))
            if encounter_type == "enemy" and self.has_enemy(target):
                filtered.append(copy.deepcopy(entry))
            elif encounter_type == "npc" and self.has_npc(target):
                filtered.append(copy.deepcopy(entry))
        return filtered

    def dungeon_profile(self, location_id: str) -> dict | None:
        location = self.locations.get(location_id, {})
        raw_profile = location.get("dungeon", {})
        if not isinstance(raw_profile, dict):
            return None

        tier = str(raw_profile.get("tier", "")).strip().upper()
        template = copy.deepcopy(self.DUNGEON_TIERS.get(tier, {}))
        if not template:
            return None

        profile = template
        for key, value in raw_profile.items():
            if key == "tier":
                continue
            profile[key] = copy.deepcopy(value)

        profile["tier"] = tier
        level_range = profile.get("level_range", [1, 1])
        if not isinstance(level_range, list) or len(level_range) != 2:
            level_range = [1, 1]
        minimum_level = max(1, int(level_range[0]))
        maximum_level = max(minimum_level, int(level_range[1]))
        profile["level_range"] = [minimum_level, maximum_level]

        normalized_families = []
        for family in profile.get("families", []):
            normalized_family = self._normalize_entity_id(family)
            if normalized_family and normalized_family not in normalized_families:
                normalized_families.append(normalized_family)
        profile["families"] = normalized_families
        profile["family_names"] = [family.replace("_", " ").title() for family in normalized_families]

        profile["enemy_pool"] = self._validated_dungeon_enemy_pool(
            raw_profile.get("enemy_pool", []),
            minimum_level,
            maximum_level,
            normalized_families,
            allow_boss=False,
        )
        profile["boss_pool"] = self._validated_dungeon_enemy_pool(
            raw_profile.get("boss_pool", []),
            minimum_level,
            maximum_level + 1,
            normalized_families,
            allow_boss=True,
        )

        if not profile["enemy_pool"] and normalized_families:
            profile["enemy_pool"] = self._derived_dungeon_enemy_pool(minimum_level, maximum_level, normalized_families)

        return profile

    def _validated_dungeon_enemy_pool(
        self,
        enemy_ids: list,
        minimum_level: int,
        maximum_level: int,
        allowed_families: list[str],
        *,
        allow_boss: bool,
    ) -> list[str]:
        pool = []
        if not isinstance(enemy_ids, list):
            return pool

        for enemy_id in enemy_ids:
            normalized_enemy = self._normalize_entity_id(enemy_id)
            enemy = self.enemies.get(normalized_enemy)
            if not enemy:
                continue
            family = self._normalize_entity_id(enemy.get("family", ""))
            level = max(1, int(enemy.get("level", 1)))
            is_boss = bool(enemy.get("boss", False))
            if allowed_families and family not in allowed_families and not allow_boss:
                continue
            if level < minimum_level or level > maximum_level:
                continue
            if is_boss and not allow_boss:
                continue
            if normalized_enemy not in pool:
                pool.append(normalized_enemy)
        return pool

    def _derived_dungeon_enemy_pool(self, minimum_level: int, maximum_level: int, allowed_families: list[str]) -> list[str]:
        pool = []
        for enemy_id, enemy in self.enemies.items():
            family = self._normalize_entity_id(enemy.get("family", ""))
            level = max(1, int(enemy.get("level", 1)))
            if allowed_families and family not in allowed_families:
                continue
            if level < minimum_level or level > maximum_level:
                continue
            if enemy.get("boss", False):
                continue
            pool.append(enemy_id)
        return pool

    def world_event_chance(self, location_id: str) -> int:
        base = int(self.get_location(location_id).get("world_event_chance", 0))
        dungeon = self.dungeon_profile(location_id)
        bonus = int(dungeon.get("world_event_bonus", 0)) if dungeon else 0
        return max(0, min(100, base + bonus))

    def state_event_chance(self, location_id: str) -> int:
        base = int(self.get_location(location_id).get("state_event_chance", 0))
        dungeon = self.dungeon_profile(location_id)
        bonus = int(dungeon.get("state_event_bonus", 0)) if dungeon else 0
        return max(0, min(100, base + bonus))

    def world_event_dc(self, location_id: str, base_dc: int) -> int:
        dungeon = self.dungeon_profile(location_id)
        bonus = int(dungeon.get("world_event_dc_bonus", 0)) if dungeon else 0
        return max(1, int(base_dc) + bonus)

    @staticmethod
    def _state_library() -> dict:
        return {
            "bandit_raid": {
                "state_id": "bandit_raid",
                "name": "Bandit Raid",
                "summary": "Raiders are choking the road and forcing locals to keep their heads down.",
                "resolved_summary": "The raiders have been driven off and the road begins to settle.",
                "encounter_modifiers": [
                    {"type": "enemy", "target": "bandit_raider", "weight": 35},
                    {"type": "enemy", "target": "bandit", "weight": 25},
                    {"type": "enemy", "target": "cutpurse", "weight": 20},
                    {"type": "enemy", "target": "thief", "weight": 15},
                ],
                "dialogue_notes": {
                    "elder": "The Elder is focused on keeping the village calm while raiders trouble the road.",
                    "captain": "The Captain is looking for someone who can break the raid before it spreads.",
                    "merchant": "The Merchant has hidden her better stock until the raiders are pushed back.",
                    "ferryman": "The Ferryman refuses reckless crossings while raiders prowl nearby.",
                },
                "spawn_enemy": "bandit_raider",
                "clear_on_victory": ["bandit_raider", "bandit", "cutpurse", "thief"],
                "conflicts": ["merchant_caravan"],
                "important": True,
            },
            "merchant_caravan": {
                "state_id": "merchant_caravan",
                "name": "Merchant Caravan",
                "summary": "Pack wagons and fresh goods have drawn traders, gossip, and opportunity to the area.",
                "resolved_summary": "The caravan has traded what it can and moved on down the road.",
                "encounter_modifiers": [
                    {"type": "npc", "target": "merchant", "weight": 80},
                ],
                "dialogue_notes": {
                    "merchant": "The Merchant is busy keeping caravan ledgers straight and moving stock quickly.",
                    "captain": "The Captain sees the caravan as good for morale, but risky if the road turns hot.",
                    "ferryman": "The Ferryman is ferrying crates as much as people while the caravan is here.",
                },
                "add_npcs": ["merchant"],
                "conflicts": ["bandit_raid"],
                "important": True,
            },
            "shrine_corruption": {
                "state_id": "shrine_corruption",
                "name": "Shrine Corruption",
                "summary": "The shrine stones are seeping a cold corruption that draws hostile things back in.",
                "resolved_summary": "The corrupt pressure around the shrine loosens and the air steadies.",
                "encounter_modifiers": [
                    {"type": "enemy", "target": "cultist", "weight": 30},
                    {"type": "enemy", "target": "ash_wisp", "weight": 30},
                    {"type": "enemy", "target": "bone_warden", "weight": 20},
                    {"type": "enemy", "target": "skeleton", "weight": 15},
                ],
                "dialogue_notes": {
                    "caretaker": "The Caretaker is alarmed by the way the shrine has turned harsh again.",
                    "hermit": "The Hermit claims the cave echoes changed the moment the shrine darkened.",
                    "scholar": "The Scholar wants the corrupted surge documented before it spreads further.",
                },
                "spawn_enemy": "ash_wisp",
                "clear_on_victory": ["cultist", "ash_wisp", "bone_warden", "skeleton", "shrine_guardian"],
                "important": True,
            },
            "wolf_infestation": {
                "state_id": "wolf_infestation",
                "name": "Wolf Infestation",
                "summary": "Wolf tracks are multiplying fast, and the brush feels ready to break into motion.",
                "resolved_summary": "The wolf pressure has eased and the nearby trail is less tense.",
                "encounter_modifiers": [
                    {"type": "enemy", "target": "dire_wolf", "weight": 30},
                    {"type": "enemy", "target": "pack_wolf", "weight": 25},
                    {"type": "enemy", "target": "wolf", "weight": 20},
                ],
                "dialogue_notes": {
                    "elder": "The Elder is worried the road is turning into hunting ground again.",
                    "scout": "The Scout keeps finding fresher tracks than the last set.",
                    "ferryman": "The Ferryman has heard howls too close to the bank for comfort.",
                    "merchant": "The Merchant is counting losses every time another pack prowls too near the road.",
                },
                "spawn_enemy": "dire_wolf",
                "clear_on_victory": ["dire_wolf", "pack_wolf", "wolf"],
                "important": True,
            },
            "traveler_in_need": {
                "state_id": "traveler_in_need",
                "name": "Traveler In Need",
                "summary": "A worn traveler has stopped here, injured and in clear need of help.",
                "resolved_summary": "The traveler has been helped and is able to continue onward.",
                "dialogue_notes": {
                    "elder": "The Elder would rather see the traveler helped than left to the road.",
                    "merchant": "The Merchant has water ready, but the traveler still needs proper treatment.",
                    "ferryman": "The Ferryman has kept the traveler off the roughest stretch until help arrives.",
                    "traveler": "The Traveler looks exhausted and badly needs a bandage before continuing.",
                },
                "add_npcs": ["traveler"],
                "important": False,
            },
        }

    @classmethod
    def _state_template(cls, state_id: str) -> dict:
        return copy.deepcopy(cls._state_library().get(state_id, {}))

    def get_location_state_ids(self, location_id: str) -> list[str]:
        return list(self.location_states.get(location_id, []))

    def get_location_states(self, location_id: str) -> list[dict]:
        states = []
        for state_id in self.get_location_state_ids(location_id):
            template = self._state_template(state_id)
            if template:
                template["location_id"] = location_id
                states.append(template)
        return states

    def has_location_state(self, location_id: str, state_id: str) -> bool:
        normalized_state = str(state_id).strip().lower()
        return normalized_state in self.get_location_state_ids(location_id)

    def _state_added_npcs(self, location_id: str) -> list[str]:
        npcs = []
        for state in self.get_location_states(location_id):
            for npc_id in state.get("add_npcs", []):
                if npc_id not in npcs:
                    npcs.append(npc_id)
        return npcs

    def _sync_state_npcs(self, location_id: str) -> None:
        npcs = self.get_npcs_at(location_id)
        required_npcs = self._state_added_npcs(location_id)
        for npc_id in required_npcs:
            if npc_id not in npcs:
                npcs.append(npc_id)

    def activate_location_state(self, location_id: str, state_id: str) -> dict | None:
        normalized_state = str(state_id).strip().lower()
        if not normalized_state or location_id not in self.location_states:
            return None
        if self.has_location_state(location_id, normalized_state):
            return None

        template = self._state_template(normalized_state)
        if not template:
            return None

        for conflicting_state in template.get("conflicts", []):
            self.clear_location_state(location_id, conflicting_state)

        self.location_states[location_id].append(normalized_state)
        spawn_enemy = str(template.get("spawn_enemy", "")).strip().lower()
        if spawn_enemy and spawn_enemy not in self.get_enemies_at(location_id):
            self.add_enemy(location_id, spawn_enemy)
        self._sync_state_npcs(location_id)
        template["location_id"] = location_id
        return template

    def clear_location_state(self, location_id: str, state_id: str) -> dict | None:
        normalized_state = str(state_id).strip().lower()
        states = self.location_states.get(location_id, [])
        if normalized_state not in states:
            return None
        template = self._state_template(normalized_state)
        states.remove(normalized_state)
        spawn_enemy = self._normalize_entity_id(template.get("spawn_enemy", "")) if template else ""
        if spawn_enemy and spawn_enemy in self.get_enemies_at(location_id):
            base_enemies = {
                self._normalize_entity_id(enemy_id)
                for enemy_id in self.locations.get(location_id, {}).get("enemies", [])
            }
            still_required = any(
                self._normalize_entity_id(state.get("spawn_enemy", "")) == spawn_enemy
                for state in self.get_location_states(location_id)
            )
            if spawn_enemy not in base_enemies and not still_required:
                self.remove_enemy(location_id, spawn_enemy)
        self.clear_transient_npcs(location_id)
        if template:
            template["location_id"] = location_id
        return template

    def active_world_states(self) -> list[dict]:
        active = []
        for location_id in self.locations:
            location_name = self.get_location(location_id).get("name", self._fallback_name(location_id))
            for state in self.get_location_states(location_id):
                active.append(
                    {
                        "location_id": location_id,
                        "location_name": location_name,
                        "state_id": state.get("state_id", ""),
                        "name": state.get("name", state.get("state_id", "")),
                        "summary": state.get("summary", ""),
                        "important": bool(state.get("important", False)),
                    }
                )
        return active

    def encounter_entries(self, location_id: str) -> list[dict]:
        base_entries = self.get_location(location_id).get("encounters", [])
        entries = self.filter_encounter_entries(base_entries)
        for state in self.get_location_states(location_id):
            modifiers = state.get("encounter_modifiers", [])
            if isinstance(modifiers, list):
                entries.extend(self.filter_encounter_entries(modifiers))
        dungeon = self.dungeon_profile(location_id)
        if dungeon:
            existing = {
                (
                    self._normalize_entity_id(entry.get("type", "")),
                    self._normalize_entity_id(entry.get("target", "")),
                )
                for entry in entries
                if isinstance(entry, dict)
            }
            for enemy_id in dungeon.get("enemy_pool", []):
                key = ("enemy", enemy_id)
                if key in existing:
                    continue
                entries.append({"type": "enemy", "target": enemy_id, "weight": 18})
                existing.add(key)
            boss_weight = int(dungeon.get("boss_weight", 0))
            for enemy_id in dungeon.get("boss_pool", []):
                key = ("enemy", enemy_id)
                if key in existing or boss_weight <= 0:
                    continue
                entries.append({"type": "enemy", "target": enemy_id, "weight": boss_weight})
                existing.add(key)
        return entries

    def npc_dialogue_note(self, location_id: str, npc_id: str) -> str:
        normalized_npc = str(npc_id).strip().lower()
        for state in self.get_location_states(location_id):
            note = state.get("dialogue_notes", {}).get(normalized_npc)
            if note:
                return str(note)
        return ""

    def location_state_lines(self, location_id: str, current: bool = False) -> list[str]:
        states = self.get_location_states(location_id)
        if not states:
            label = " [YOU]" if current else ""
            return [f"- {self.get_location(location_id).get('name', self._fallback_name(location_id))}{label}: calm"]

        location_name = self.get_location(location_id).get("name", self._fallback_name(location_id))
        label = " [YOU]" if current else ""
        lines = []
        for state in states:
            lines.append(f"- {location_name}{label}: {state.get('name', state.get('state_id', 'State'))}")
        return lines

    def add_enemy(self, location_id: str, enemy_id: str) -> None:
        normalized_enemy = self._normalize_entity_id(enemy_id)
        if location_id not in self.state_locations or not self.has_enemy(normalized_enemy):
            return
        enemies = self.get_enemies_at(location_id)
        if normalized_enemy not in enemies:
            enemies.append(normalized_enemy)

    def remove_enemy(self, location_id: str, enemy_id: str) -> None:
        enemies = self.get_enemies_at(location_id)
        if enemy_id in enemies:
            enemies.remove(enemy_id)

    def remove_item(self, location_id: str, item_id: str) -> None:
        items = self.get_items_at(location_id)
        if item_id in items:
            items.remove(item_id)

    def add_item(self, location_id: str, item_id: str) -> None:
        normalized_item = self._normalize_entity_id(item_id)
        if location_id not in self.state_locations or not self.has_item(normalized_item):
            return
        items = self.get_items_at(location_id)
        if normalized_item not in items:
            items.append(normalized_item)

    def add_npc(self, location_id: str, npc_id: str) -> None:
        normalized_npc = self._normalize_entity_id(npc_id)
        if location_id not in self.state_locations or not self.has_npc(normalized_npc):
            return
        npcs = self.get_npcs_at(location_id)
        if normalized_npc not in npcs:
            npcs.append(normalized_npc)

    def _sync_state_enemies(self, location_id: str) -> None:
        enemies = self.get_enemies_at(location_id)
        for state in self.get_location_states(location_id):
            spawn_enemy = self._normalize_entity_id(state.get("spawn_enemy", ""))
            if spawn_enemy and self.has_enemy(spawn_enemy) and spawn_enemy not in enemies:
                enemies.append(spawn_enemy)

    def clear_transient_npcs(self, location_id: str) -> None:
        default_npcs = list(self.locations.get(location_id, {}).get("npcs", []))
        for npc_id in self._state_added_npcs(location_id):
            if npc_id not in default_npcs:
                default_npcs.append(npc_id)
        self.state_locations[location_id]["npcs"] = default_npcs

    def find_connected_location(self, current_location: str, query: str) -> str | None:
        query = query.strip().lower()
        connected = self.get_location(current_location).get("connected_locations", {})

        if query in connected:
            return connected[query]

        for target_id in connected.values():
            target_name = self.get_location(target_id).get("name", "").lower()
            if query == target_id.lower() or query == target_name:
                return target_id

        return None

    def exit_direction_to(self, current_location: str, target_location: str) -> str | None:
        connected = self.get_location(current_location).get("connected_locations", {})
        for direction, location_id in connected.items():
            if location_id == target_location:
                return direction
        return None

    def find_item_at_location(self, location_id: str, query: str) -> str | None:
        query = query.strip().lower()
        for item_id in self.get_items_at(location_id):
            item = self.items.get(item_id, {})
            if query == item_id.lower() or query == item.get("name", "").lower():
                return item_id
        return None

    def find_enemy_at_location(self, location_id: str, query: str) -> str | None:
        query = query.strip().lower()
        for enemy_id in self.get_enemies_at(location_id):
            enemy = self.enemies.get(enemy_id, {})
            if query == enemy_id.lower() or query == enemy.get("name", "").lower():
                return enemy_id
        return None

    def find_npc_at_location(self, location_id: str, query: str) -> str | None:
        query = query.strip().lower()
        for npc_id in self.get_npcs_at(location_id):
            npc_normalized = str(npc_id).strip().lower()
            npc_display = self.npc_name(npc_normalized).lower()
            aliases = [str(alias).strip().lower() for alias in self.npcs.get(npc_normalized, {}).get("aliases", [])]
            if query == npc_normalized or query == npc_display or query in aliases:
                return npc_normalized
        return None

    def is_current_location_query(self, current_location: str, query: str) -> bool:
        normalized = " ".join(query.strip().lower().split())
        if not normalized:
            return False

        if normalized in {"here", "location", "area"}:
            return True

        location = self.get_location(current_location)
        location_name = location.get("name", "").lower()
        current_id = current_location.lower()
        if normalized == current_id or normalized == location_name:
            return True
        return normalized in location_name or location_name in normalized

    @staticmethod
    def normalize_search_target(query: str) -> str | None:
        normalized = " ".join(query.strip().lower().split())
        if normalized in {"area", "ground", "location"}:
            return normalized
        return None

    @staticmethod
    def _fallback_name(entity_id: str) -> str:
        return entity_id.replace("_", " ").title()

    def enemy_name(self, enemy_id: str) -> str:
        return self.enemies.get(enemy_id, {}).get("name", self._fallback_name(enemy_id))

    def item_name(self, item_id: str) -> str:
        return self.items.get(item_id, {}).get("name", self._fallback_name(item_id))

    def npc_name(self, npc_id: str) -> str:
        return self.npcs.get(npc_id, {}).get("name", self._fallback_name(npc_id))

    def get_npc(self, npc_id: str) -> dict:
        return self.npcs.get(npc_id, {})

    def _default_events(self) -> dict:
        return {
            "village_well": {
                "event_id": "village_well",
                "name": "Village Well",
                "location_id": "village_square",
                "trigger": "enter",
                "resolved": False,
                "effect": {
                    "type": "heal",
                    "amount": 4,
                },
            }
        }

    def get_location_events(self, location_id: str, trigger: str = "enter") -> list[dict]:
        events = []
        for event in self.state_events.values():
            if event.get("resolved"):
                continue
            if event.get("location_id") != location_id:
                continue
            if event.get("trigger") != trigger:
                continue
            events.append(event)
        return events

    def resolve_event(self, event_id: str) -> None:
        event = self.state_events.get(event_id)
        if event:
            event["resolved"] = True

    def state_to_dict(self) -> dict:
        world_state = {}
        for location_id in self.locations:
            location = self.get_location(location_id)
            world_state[location_id] = {
                "enemies": list(location.get("enemies", [])),
                "items": list(location.get("items", [])),
                "npcs": list(location.get("npcs", [])),
            }
        world_state["_events"] = {
            event_id: {"resolved": bool(event.get("resolved", False))}
            for event_id, event in self.state_events.items()
        }
        world_state["_location_states"] = {
            location_id: list(self.location_states.get(location_id, []))
            for location_id in self.locations
            if self.location_states.get(location_id)
        }
        return world_state

    def load_state_from_dict(self, data: dict) -> None:
        if not isinstance(data, dict):
            return

        for location_id, default_location in self.locations.items():
            location_state = data.get(location_id)
            if not isinstance(location_state, dict):
                continue

            default_enemies = default_location.get("enemies", [])
            default_items = default_location.get("items", [])
            default_npcs = default_location.get("npcs", [])

            saved_enemies = location_state.get("enemies", default_enemies)
            saved_items = location_state.get("items", default_items)
            saved_npcs = location_state.get("npcs", default_npcs)

            enemy_allow = {
                self._normalize_entity_id(enemy_id)
                for enemy_id in saved_enemies
                if self.has_enemy(enemy_id)
            } if isinstance(saved_enemies, list) else set(default_enemies)
            item_allow = {
                self._normalize_entity_id(item_id)
                for item_id in saved_items
                if self.has_item(item_id)
            } if isinstance(saved_items, list) else set(default_items)
            npc_allow = {
                self._normalize_entity_id(npc_id)
                for npc_id in saved_npcs
                if self.has_npc(npc_id)
            } if isinstance(saved_npcs, list) else set(default_npcs)
            saved_enemy_order = [
                self._normalize_entity_id(enemy_id)
                for enemy_id in saved_enemies
                if self.has_enemy(enemy_id)
            ] if isinstance(saved_enemies, list) else list(default_enemies)
            saved_item_order = [
                self._normalize_entity_id(item_id)
                for item_id in saved_items
                if self.has_item(item_id)
            ] if isinstance(saved_items, list) else list(default_items)
            saved_npc_order = [
                self._normalize_entity_id(npc_id)
                for npc_id in saved_npcs
                if self.has_npc(npc_id)
            ] if isinstance(saved_npcs, list) else list(default_npcs)

            # Preserve canonical ordering from base data while restoring only saved survivors.
            self.state_locations[location_id]["enemies"] = [
                enemy_id for enemy_id in default_enemies if enemy_id in enemy_allow
            ] + [enemy_id for enemy_id in saved_enemy_order if enemy_id not in default_enemies]
            self.state_locations[location_id]["items"] = [
                item_id for item_id in default_items if item_id in item_allow
            ] + [item_id for item_id in saved_item_order if item_id not in default_items]
            self.state_locations[location_id]["npcs"] = [
                npc_id for npc_id in default_npcs if npc_id in npc_allow
            ] + [npc_id for npc_id in saved_npc_order if npc_id not in default_npcs]

        events_state = data.get("_events", {})
        if isinstance(events_state, dict):
            for event_id, event in self.state_events.items():
                saved_event = events_state.get(event_id, {})
                if isinstance(saved_event, dict):
                    event["resolved"] = bool(saved_event.get("resolved", event.get("resolved", False)))

        states_data = data.get("_location_states", {})
        if isinstance(states_data, dict):
            for location_id in self.locations:
                raw_states = states_data.get(location_id, [])
                if not isinstance(raw_states, list):
                    continue
                restored = []
                for state_id in raw_states:
                    normalized_state = str(state_id).strip().lower()
                    if self._state_template(normalized_state):
                        restored.append(normalized_state)
                self.location_states[location_id] = restored
                self._sync_state_enemies(location_id)
                self._sync_state_npcs(location_id)

    def map_lines(self, current_location: str) -> list[str]:
        lines = ["World Map"]
        for location_id, location in self.locations.items():
            location_name = location.get("name", self._fallback_name(location_id))
            current_marker = " [YOU]" if location_id == current_location else ""
            exits = location.get("connected_locations", {})
            if not exits:
                lines.append(f"- {location_name}{current_marker} | exits: none")
                continue

            exit_text = ", ".join(
                f"{direction}->{self.locations.get(target_id, {}).get('name', self._fallback_name(target_id))}"
                for direction, target_id in exits.items()
            )
            lines.append(f"- {location_name}{current_marker} | exits: {exit_text}")

        return lines

    def world_state_lines(self, current_location: str) -> list[str]:
        active_states = self.active_world_states()
        lines = ["World State"]
        if not active_states:
            lines.append("No dynamic world events are active.")
            return lines

        for location_id in self.locations:
            if not self.get_location_state_ids(location_id):
                continue
            lines.extend(self.location_state_lines(location_id, current=(location_id == current_location)))
        return lines
