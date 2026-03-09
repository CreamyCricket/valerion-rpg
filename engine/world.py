import copy
import json
from pathlib import Path


class World:
    """Static data loader and persisting location/enemy/item runtime state."""
    RANK_ORDER = {"E": 0, "D": 1, "C": 2, "B": 3, "A": 4, "S": 5}
    DUNGEON_TIERS = {
        "E": {
            "label": "E-Rank",
            "danger": "beginner danger",
            "level_range": [1, 2],
            "families": ["slimes", "wolves", "bandits"],
            "enemy_weight": 16,
            "elite_weight": 0,
            "boss_weight": 4,
            "attack_bonus": 0,
            "defense_bonus": 0,
            "hp_bonus": 0,
            "xp_bonus": 0,
            "gold_bonus": 1,
            "elite_gold_bonus": 1,
            "boss_gold_bonus": 2,
            "loot_band": "Common to Uncommon",
            "event_risk": "Low",
            "world_event_bonus": 0,
            "world_event_dc_bonus": 0,
            "state_event_bonus": 2,
        },
        "D": {
            "label": "D-Rank",
            "danger": "trained adventurer",
            "level_range": [2, 3],
            "families": ["wolves", "bandits", "shrine_creatures", "cultists"],
            "enemy_weight": 18,
            "elite_weight": 3,
            "boss_weight": 6,
            "attack_bonus": 0,
            "defense_bonus": 0,
            "hp_bonus": 2,
            "xp_bonus": 4,
            "gold_bonus": 2,
            "elite_gold_bonus": 2,
            "boss_gold_bonus": 4,
            "loot_band": "Common to Uncommon",
            "event_risk": "Guarded",
            "world_event_bonus": 2,
            "world_event_dc_bonus": 1,
            "state_event_bonus": 3,
        },
        "C": {
            "label": "C-Rank",
            "danger": "veteran threats",
            "level_range": [3, 4],
            "families": ["bandits", "cultists", "spiders"],
            "enemy_weight": 20,
            "elite_weight": 6,
            "boss_weight": 10,
            "attack_bonus": 1,
            "defense_bonus": 1,
            "hp_bonus": 4,
            "xp_bonus": 8,
            "gold_bonus": 3,
            "elite_gold_bonus": 4,
            "boss_gold_bonus": 7,
            "loot_band": "Uncommon to Rare",
            "event_risk": "Elevated",
            "world_event_bonus": 4,
            "world_event_dc_bonus": 1,
            "state_event_bonus": 5,
        },
        "B": {
            "label": "B-Rank",
            "danger": "serious danger",
            "level_range": [4, 5],
            "families": ["cultists", "shrine_creatures", "ruin_guardians"],
            "enemy_weight": 22,
            "elite_weight": 9,
            "boss_weight": 14,
            "attack_bonus": 1,
            "defense_bonus": 1,
            "hp_bonus": 6,
            "xp_bonus": 12,
            "gold_bonus": 5,
            "elite_gold_bonus": 6,
            "boss_gold_bonus": 10,
            "loot_band": "Rare",
            "event_risk": "High",
            "world_event_bonus": 6,
            "world_event_dc_bonus": 2,
            "state_event_bonus": 6,
        },
        "A": {
            "label": "A-Rank",
            "danger": "extreme threats",
            "level_range": [5, 6],
            "families": ["ruin_guardians", "abyss_beasts", "ash_heralds"],
            "enemy_weight": 24,
            "elite_weight": 12,
            "boss_weight": 18,
            "attack_bonus": 2,
            "defense_bonus": 2,
            "hp_bonus": 8,
            "xp_bonus": 18,
            "gold_bonus": 8,
            "elite_gold_bonus": 8,
            "boss_gold_bonus": 14,
            "loot_band": "Rare to Epic",
            "event_risk": "Severe",
            "world_event_bonus": 8,
            "world_event_dc_bonus": 2,
            "state_event_bonus": 8,
        },
        "S": {
            "label": "S-Rank",
            "danger": "legendary danger",
            "level_range": [6, 8],
            "families": ["ruin_guardians", "abyss_beasts", "ash_heralds"],
            "enemy_weight": 26,
            "elite_weight": 15,
            "boss_weight": 22,
            "attack_bonus": 3,
            "defense_bonus": 2,
            "hp_bonus": 12,
            "xp_bonus": 25,
            "gold_bonus": 12,
            "elite_gold_bonus": 12,
            "boss_gold_bonus": 20,
            "loot_band": "Epic",
            "event_risk": "Catastrophic",
            "world_event_bonus": 10,
            "world_event_dc_bonus": 3,
            "state_event_bonus": 10,
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
        self.rumors = self._load_json(base / "rumors.json")
        self.quests = self._load_json(base / "quests.json")
        self.factions = self._load_json(base / "factions.json")
        self.arcs = self._load_json(base / "arcs.json")
        self.travel_routes = self._load_json(base / "travel_routes.json")
        self.road_encounters = self._load_json(base / "road_encounters.json")
        self.regional_event_zones = self._load_json(base / "regional_events.json")
        self.titles = self._load_json(base / "titles.json")

        # Runtime world state. Locations change when items are taken or enemies are defeated.
        self.state_locations = copy.deepcopy(self.locations)
        self.state_events = self._default_events()
        self.location_states = {location_id: [] for location_id in self.locations}
        self.active_regional_events_by_region = {}
        self.active_road_encounter = {}
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

    @classmethod
    def normalize_rank(cls, rank: str) -> str:
        normalized = str(rank).strip().upper()
        return normalized if normalized in cls.RANK_ORDER else ""

    @classmethod
    def rank_value(cls, rank: str) -> int:
        normalized = cls.normalize_rank(rank)
        return cls.RANK_ORDER.get(normalized, -1)

    @classmethod
    def rank_for_level(cls, level: int) -> str:
        normalized_level = max(1, int(level))
        for rank, profile in cls.DUNGEON_TIERS.items():
            level_range = profile.get("level_range", [1, 1])
            if isinstance(level_range, list) and len(level_range) == 2 and normalized_level <= int(level_range[1]):
                return rank
        return "S"

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
            allow_elite=False,
        )
        profile["elite_pool"] = self._validated_dungeon_enemy_pool(
            raw_profile.get("elite_pool", []),
            minimum_level,
            maximum_level + 1,
            normalized_families,
            allow_boss=False,
            allow_elite=True,
        )
        profile["boss_pool"] = self._validated_dungeon_enemy_pool(
            raw_profile.get("boss_pool", []),
            minimum_level,
            maximum_level + 1,
            normalized_families,
            allow_boss=True,
            allow_elite=True,
        )

        if not profile["enemy_pool"] and normalized_families:
            profile["enemy_pool"] = self._derived_dungeon_enemy_pool(
                minimum_level,
                maximum_level,
                normalized_families,
                allow_elite=False,
            )
        if not profile["elite_pool"] and normalized_families:
            profile["elite_pool"] = self._derived_dungeon_enemy_pool(
                minimum_level,
                maximum_level + 1,
                normalized_families,
                allow_elite=True,
            )

        return profile

    def _validated_dungeon_enemy_pool(
        self,
        enemy_ids: list,
        minimum_level: int,
        maximum_level: int,
        allowed_families: list[str],
        *,
        allow_boss: bool,
        allow_elite: bool,
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
            is_elite = bool(enemy.get("elite", False))
            if allowed_families and family not in allowed_families and not allow_boss:
                continue
            if level < minimum_level or level > maximum_level:
                continue
            if is_boss and not allow_boss:
                continue
            if is_elite and not allow_elite:
                continue
            if not is_elite and allow_elite and not allow_boss:
                continue
            if normalized_enemy not in pool:
                pool.append(normalized_enemy)
        return pool

    def _derived_dungeon_enemy_pool(
        self,
        minimum_level: int,
        maximum_level: int,
        allowed_families: list[str],
        *,
        allow_elite: bool,
    ) -> list[str]:
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
            if bool(enemy.get("elite", False)) != bool(allow_elite):
                continue
            pool.append(enemy_id)
        return pool

    def location_rank(self, location_id: str) -> str:
        dungeon = self.dungeon_profile(location_id)
        return self.normalize_rank(dungeon.get("tier", "")) if dungeon else ""

    def location_rank_profile(self, location_id: str) -> dict:
        dungeon = self.dungeon_profile(location_id)
        return dungeon if dungeon else {}

    def location_rank_text(self, location_id: str) -> str:
        profile = self.location_rank_profile(location_id)
        if not profile:
            return ""
        label = str(profile.get("label", "")).strip()
        danger = str(profile.get("danger", "")).strip()
        if label and danger:
            return f"{label} - {danger}"
        return label or danger

    def rank_warning_text(self, location_id: str, player_rank: str) -> str:
        location_rank = self.location_rank(location_id)
        if not location_rank:
            return ""
        if self.rank_value(location_rank) <= self.rank_value(player_rank):
            return ""
        label = self.location_rank_profile(location_id).get("label", f"{location_rank}-Rank")
        severity = self.rank_value(location_rank) - self.rank_value(player_rank)
        if severity >= 2:
            return f"Danger Warning: This region is rated {label}. Unprepared adventurers rarely return."
        return f"Danger Warning: This region is rated {label}. Proceed with caution."

    def combat_rank_modifiers(self, location_id: str, enemy_id: str) -> dict:
        dungeon = self.dungeon_profile(location_id)
        enemy = self.enemies.get(self._normalize_entity_id(enemy_id), {})
        if not dungeon or not enemy:
            return {"hp_bonus": 0, "attack_bonus": 0, "defense_bonus": 0, "xp_bonus": 0}

        modifiers = {
            "hp_bonus": int(dungeon.get("hp_bonus", 0)),
            "attack_bonus": int(dungeon.get("attack_bonus", 0)),
            "defense_bonus": int(dungeon.get("defense_bonus", 0)),
            "xp_bonus": int(dungeon.get("xp_bonus", 0)),
        }
        if bool(enemy.get("elite", False)):
            modifiers["hp_bonus"] += 2
            modifiers["attack_bonus"] += 1
            modifiers["xp_bonus"] += 6
        if bool(enemy.get("boss", False)) or self._normalize_entity_id(enemy_id) in dungeon.get("boss_pool", []):
            modifiers["hp_bonus"] += 4
            modifiers["defense_bonus"] += 1
            modifiers["xp_bonus"] += 10
        return modifiers

    def rank_reward_bonus(self, location_id: str, enemy_id: str) -> dict:
        dungeon = self.dungeon_profile(location_id)
        enemy = self.enemies.get(self._normalize_entity_id(enemy_id), {})
        if not dungeon or not enemy:
            return {"gold": 0}

        gold = int(dungeon.get("gold_bonus", 0))
        if bool(enemy.get("elite", False)):
            gold += int(dungeon.get("elite_gold_bonus", 0))
        if bool(enemy.get("boss", False)) or self._normalize_entity_id(enemy_id) in dungeon.get("boss_pool", []):
            gold += int(dungeon.get("boss_gold_bonus", 0))
        return {"gold": gold}

    def _ranked_entry_weight(self, dungeon: dict, entry: dict) -> int:
        weight = max(0, int(entry.get("weight", 0)))
        if not dungeon or str(entry.get("type", "")).strip().lower() != "enemy":
            return weight
        target = self._normalize_entity_id(entry.get("target", ""))
        enemy = self.enemies.get(target, {})
        if not enemy:
            return weight
        if bool(enemy.get("boss", False)):
            return max(weight, int(dungeon.get("boss_weight", 0)))
        if bool(enemy.get("elite", False)):
            return max(weight, int(dungeon.get("elite_weight", 0)))
        return weight

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

    def _regional_region(self, region_id: str) -> dict:
        return self.regional_event_zones.get(str(region_id).strip().lower(), {})

    def _regional_event_entry(self, event_id: str) -> dict:
        normalized_event = str(event_id).strip().lower()
        for region_id, region_data in self.regional_event_zones.items():
            if not isinstance(region_data, dict):
                continue
            for entry in region_data.get("events", []):
                if not isinstance(entry, dict):
                    continue
                if str(entry.get("event_id", "")).strip().lower() != normalized_event:
                    continue
                merged = copy.deepcopy(entry)
                merged["event_id"] = normalized_event
                merged["region_id"] = str(region_id).strip().lower()
                return merged
        return {}

    def regional_region_for_location(self, location_id: str) -> str:
        normalized_location = str(location_id).strip().lower()
        for region_id, region_data in self.regional_event_zones.items():
            if not isinstance(region_data, dict):
                continue
            locations = region_data.get("locations", [])
            if not isinstance(locations, list):
                continue
            normalized_locations = {str(entry).strip().lower() for entry in locations}
            if normalized_location in normalized_locations:
                return str(region_id).strip().lower()
        return ""

    def regional_event_candidates(self, location_id: str) -> list[dict]:
        region_id = self.regional_region_for_location(location_id)
        if not region_id:
            return []
        region_data = self._regional_region(region_id)
        if not isinstance(region_data, dict):
            return []

        max_active = max(1, int(region_data.get("max_active", 1)))
        active_entries = self.active_regional_events_by_region.get(region_id, [])
        if len(active_entries) >= max_active:
            return []

        active_chain_ids = {
            str(active.get("chain_id", "")).strip().lower()
            for active in active_entries
            if str(active.get("chain_id", "")).strip()
        }
        candidates = []
        for entry in region_data.get("events", []):
            if not isinstance(entry, dict):
                continue
            event_id = str(entry.get("event_id", "")).strip().lower()
            if not event_id:
                continue
            if int(entry.get("stage", 1) or 1) != 1:
                continue
            chain_id = str(entry.get("chain_id", "")).strip().lower()
            if chain_id and chain_id in active_chain_ids:
                continue
            candidate = copy.deepcopy(entry)
            candidate["event_id"] = event_id
            candidate["region_id"] = region_id
            candidates.append(candidate)
        return candidates

    def regional_activation_chance(self, location_id: str) -> int:
        region_id = self.regional_region_for_location(location_id)
        if not region_id:
            return 0
        region_data = self._regional_region(region_id)
        if not isinstance(region_data, dict):
            return 0
        return max(0, min(100, int(region_data.get("activation_chance", 0) or 0)))

    def activate_regional_event(self, event_id: str, location_id: str) -> dict | None:
        entry = self._regional_event_entry(event_id)
        if not entry:
            return None
        region_id = str(entry.get("region_id", "")).strip().lower()
        if not region_id:
            return None
        active_entries = self.active_regional_events_by_region.setdefault(region_id, [])
        max_active = max(1, int(self._regional_region(region_id).get("max_active", 1)))
        if len(active_entries) >= max_active:
            return None

        chain_id = str(entry.get("chain_id", "")).strip().lower()
        if chain_id:
            for active in active_entries:
                if str(active.get("chain_id", "")).strip().lower() == chain_id:
                    return None

        target_location = str(entry.get("location_id", location_id)).strip().lower()
        if target_location not in self.locations:
            target_location = str(location_id).strip().lower()
        if target_location not in self.locations:
            locations = self._regional_region(region_id).get("locations", [])
            if isinstance(locations, list) and locations:
                first_location = str(locations[0]).strip().lower()
                if first_location in self.locations:
                    target_location = first_location

        active = {
            "event_id": str(entry.get("event_id", "")).strip().lower(),
            "region_id": region_id,
            "location_id": target_location,
            "turns_active": 0,
            "stage": int(entry.get("stage", 1) or 1),
            "chain_id": chain_id,
        }
        active_entries.append(active)
        self._sync_regional_state_side_effects(target_location, entry)

        activated = copy.deepcopy(entry)
        activated.update(active)
        activated["location_name"] = self.get_location(target_location).get("name", self._fallback_name(target_location))
        activated["region_name"] = str(self._regional_region(region_id).get("name", "")).strip()
        return activated

    def _sync_regional_state_side_effects(self, location_id: str, entry: dict) -> None:
        spawn_enemy = self._normalize_entity_id(entry.get("spawn_enemy", ""))
        if spawn_enemy and self.has_enemy(spawn_enemy):
            self.add_enemy(location_id, spawn_enemy)
        for npc_id in entry.get("add_npcs", []):
            normalized_npc = self._normalize_entity_id(npc_id)
            if normalized_npc and self.has_npc(normalized_npc):
                self.add_npc(location_id, normalized_npc)

    def _clear_regional_state_side_effects(self, location_id: str, entry: dict, *, keep_event_id: str = "") -> None:
        normalized_location = str(location_id).strip().lower()
        if normalized_location not in self.state_locations:
            return

        spawn_enemy = self._normalize_entity_id(entry.get("spawn_enemy", ""))
        if spawn_enemy and spawn_enemy in self.get_enemies_at(normalized_location):
            base_enemies = {
                self._normalize_entity_id(enemy_id)
                for enemy_id in self.locations.get(normalized_location, {}).get("enemies", [])
            }
            still_required = False
            for active in self.active_regional_events():
                if str(active.get("location_id", "")).strip().lower() != normalized_location:
                    continue
                if keep_event_id and str(active.get("event_id", "")).strip().lower() == keep_event_id:
                    continue
                if self._normalize_entity_id(active.get("spawn_enemy", "")) == spawn_enemy:
                    still_required = True
                    break
            if spawn_enemy not in base_enemies and not still_required:
                self.remove_enemy(normalized_location, spawn_enemy)

        transient_npcs = {
            self._normalize_entity_id(npc_id)
            for npc_id in entry.get("add_npcs", [])
            if self.has_npc(npc_id)
        }
        if transient_npcs:
            retained_npcs = list(self.locations.get(normalized_location, {}).get("npcs", []))
            for npc_id in self._state_added_npcs(normalized_location):
                normalized_npc = self._normalize_entity_id(npc_id)
                if normalized_npc and normalized_npc not in retained_npcs:
                    retained_npcs.append(normalized_npc)
            for active in self.active_regional_events():
                if str(active.get("location_id", "")).strip().lower() != normalized_location:
                    continue
                if keep_event_id and str(active.get("event_id", "")).strip().lower() == keep_event_id:
                    continue
                for npc_id in active.get("add_npcs", []):
                    normalized_npc = self._normalize_entity_id(npc_id)
                    if normalized_npc and normalized_npc not in retained_npcs:
                        retained_npcs.append(normalized_npc)
            self.state_locations[normalized_location]["npcs"] = retained_npcs

    def _regional_transition_payload(self, entry: dict) -> dict:
        payload = copy.deepcopy(entry)
        location_id = str(payload.get("location_id", "")).strip().lower()
        payload["location_id"] = location_id
        payload["location_name"] = self.get_location(location_id).get("name", self._fallback_name(location_id))
        payload["region_name"] = str(self._regional_region(payload.get("region_id", "")).get("name", "")).strip()
        return payload

    def advance_regional_events(self, turns: int = 1) -> list[dict]:
        transitions = []
        for _ in range(max(1, int(turns))):
            for region_id in list(self.active_regional_events_by_region.keys()):
                active_entries = self.active_regional_events_by_region.get(region_id, [])
                next_entries = []
                for active in active_entries:
                    active["turns_active"] = int(active.get("turns_active", 0)) + 1
                    entry = self._regional_event_entry(active.get("event_id", ""))
                    if not entry:
                        continue

                    expire_after = int(entry.get("expire_after_turns", 0) or 0)
                    if expire_after > 0 and active["turns_active"] >= expire_after:
                        self._clear_regional_state_side_effects(
                            active.get("location_id", ""),
                            entry,
                            keep_event_id=str(active.get("event_id", "")).strip().lower(),
                        )
                        resolved = self._regional_transition_payload({**entry, **active, "resolution_reason": "timed_expiration"})
                        resolved["transition"] = "resolved"
                        transitions.append(resolved)
                        continue

                    escalate_after = int(entry.get("turns_to_escalate", 0) or 0)
                    escalates_to = str(entry.get("escalates_to", "")).strip().lower()
                    if escalate_after > 0 and escalates_to and active["turns_active"] >= escalate_after:
                        next_entry = self._regional_event_entry(escalates_to)
                        if next_entry:
                            self._clear_regional_state_side_effects(
                                active.get("location_id", ""),
                                entry,
                                keep_event_id=str(active.get("event_id", "")).strip().lower(),
                            )
                            escalated = {
                                "event_id": escalates_to,
                                "region_id": region_id,
                                "location_id": str(next_entry.get("location_id", active.get("location_id", ""))).strip().lower() or str(active.get("location_id", "")).strip().lower(),
                                "turns_active": 0,
                                "stage": int(next_entry.get("stage", active.get("stage", 1)) or 1),
                                "chain_id": str(next_entry.get("chain_id", active.get("chain_id", ""))).strip().lower(),
                            }
                            self._sync_regional_state_side_effects(escalated["location_id"], next_entry)
                            next_entries.append(escalated)
                            transitioned = self._regional_transition_payload({**next_entry, **escalated, "previous_event_id": active.get("event_id", "")})
                            transitioned["transition"] = "escalated"
                            transitions.append(transitioned)
                            continue

                    next_entries.append(active)
                if next_entries:
                    self.active_regional_events_by_region[region_id] = next_entries
                else:
                    self.active_regional_events_by_region.pop(region_id, None)
        return transitions

    def _resolve_matching_regional_events(self, predicate, reason: str) -> list[dict]:
        resolved = []
        for region_id in list(self.active_regional_events_by_region.keys()):
            active_entries = self.active_regional_events_by_region.get(region_id, [])
            next_entries = []
            for active in active_entries:
                entry = self._regional_event_entry(active.get("event_id", ""))
                if not entry:
                    continue
                if predicate(entry, active):
                    self._clear_regional_state_side_effects(
                        active.get("location_id", ""),
                        entry,
                        keep_event_id=str(active.get("event_id", "")).strip().lower(),
                    )
                    payload = self._regional_transition_payload({**entry, **active, "resolution_reason": reason})
                    payload["transition"] = "resolved"
                    resolved.append(payload)
                    continue
                next_entries.append(active)
            if next_entries:
                self.active_regional_events_by_region[region_id] = next_entries
            else:
                self.active_regional_events_by_region.pop(region_id, None)
        return resolved

    def resolve_regional_event_by_enemy(self, enemy_id: str, location_id: str = "") -> list[dict]:
        normalized_enemy = str(enemy_id).strip().lower()
        normalized_location = str(location_id).strip().lower()

        def _predicate(entry: dict, active: dict) -> bool:
            if normalized_location and str(active.get("location_id", "")).strip().lower() != normalized_location:
                return False
            targets = {str(target).strip().lower() for target in entry.get("resolve_on_enemy_defeat", [])}
            return normalized_enemy in targets

        return self._resolve_matching_regional_events(_predicate, reason=f"defeated_{normalized_enemy}")

    def resolve_regional_event_by_contract(self, contract_id: str) -> list[dict]:
        normalized_contract = str(contract_id).strip().lower()

        def _predicate(entry: dict, active: dict) -> bool:
            contracts = {str(target).strip().lower() for target in entry.get("resolve_on_contract_claim", [])}
            return normalized_contract in contracts

        return self._resolve_matching_regional_events(_predicate, reason=f"claimed_{normalized_contract}")

    def active_regional_events(self) -> list[dict]:
        active = []
        for region_id in self.regional_event_zones:
            for entry in self.active_regional_events_by_region.get(region_id, []):
                event_data = self._regional_event_entry(entry.get("event_id", ""))
                if not event_data:
                    continue
                payload = self._regional_transition_payload({**event_data, **entry})
                payload["important"] = bool(event_data.get("important", True))
                active.append(payload)
        return active

    def regional_encounter_modifiers(self, location_id: str) -> list[dict]:
        normalized_location = str(location_id).strip().lower()
        modifiers = []
        for event in self.active_regional_events():
            if str(event.get("location_id", "")).strip().lower() != normalized_location:
                continue
            for entry in event.get("encounter_modifiers", []):
                if isinstance(entry, dict):
                    modifiers.append(copy.deepcopy(entry))
        return self.filter_encounter_entries(modifiers)

    def regional_npc_dialogue_note(self, location_id: str, npc_id: str) -> str:
        normalized_location = str(location_id).strip().lower()
        normalized_npc = str(npc_id).strip().lower()
        for event in self.active_regional_events():
            if str(event.get("location_id", "")).strip().lower() != normalized_location:
                continue
            note = event.get("npc_notes", {}).get(normalized_npc)
            if note:
                return str(note)
        return ""

    def regional_travel_warnings(self, location_id: str) -> list[str]:
        region_id = self.regional_region_for_location(location_id)
        if not region_id:
            return []
        warnings = []
        for event in self.active_regional_events_by_region.get(region_id, []):
            entry = self._regional_event_entry(event.get("event_id", ""))
            warning = str(entry.get("travel_warning", "")).strip()
            if warning and warning not in warnings:
                warnings.append(warning)
        return warnings

    def regional_contract_focus(self, board_location: str) -> list[str]:
        normalized_board = str(board_location).strip().lower()
        focus = []
        for event in self.active_regional_events():
            board = str(event.get("board_location", "market_square")).strip().lower()
            if board != normalized_board:
                continue
            for contract_id in event.get("contract_focus", []):
                normalized_contract = str(contract_id).strip().lower()
                if normalized_contract and normalized_contract not in focus:
                    focus.append(normalized_contract)
        return focus

    def road_encounter_chance(self) -> int:
        meta = self.road_encounters.get("meta", {}) if isinstance(self.road_encounters, dict) else {}
        return max(0, min(100, int(meta.get("travel_chance", 15) or 0)))

    def road_encounter_candidates(self, route: dict) -> list[dict]:
        if not isinstance(route, dict):
            return []

        origin = str(route.get("origin", "")).strip().lower()
        destination = str(route.get("destination", "")).strip().lower()
        mode = str(route.get("mode", "")).strip().lower()
        route_id = str(route.get("route_id", "")).strip().lower()
        origin_region = str(self.locations.get(origin, {}).get("region", "")).strip().lower()
        destination_region = str(self.locations.get(destination, {}).get("region", "")).strip().lower()

        entries = self.road_encounters.get("encounters", []) if isinstance(self.road_encounters, dict) else []
        candidates = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            encounter_id = str(entry.get("encounter_id", "")).strip().lower()
            if not encounter_id:
                continue

            def _matches(field: str, value: str) -> bool:
                allowed = entry.get(field, [])
                if not allowed:
                    return True
                if isinstance(allowed, str):
                    allowed_values = {str(allowed).strip().lower()}
                elif isinstance(allowed, list):
                    allowed_values = {str(item).strip().lower() for item in allowed if str(item).strip()}
                else:
                    return True
                return value in allowed_values

            if not _matches("route_ids", route_id):
                continue
            if not _matches("origins", origin):
                continue
            if not _matches("destinations", destination):
                continue
            if not _matches("modes", mode):
                continue
            if not _matches("origin_regions", origin_region):
                continue
            if not _matches("destination_regions", destination_region):
                continue

            candidate = copy.deepcopy(entry)
            candidate["encounter_id"] = encounter_id
            candidates.append(candidate)
        return candidates

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
        for event in self.active_regional_events():
            active.append(
                {
                    "location_id": event.get("location_id", ""),
                    "location_name": event.get("location_name", event.get("location_id", "Unknown")),
                    "state_id": event.get("event_id", ""),
                    "name": event.get("name", event.get("event_id", "")),
                    "summary": event.get("summary", ""),
                    "important": bool(event.get("important", True)),
                }
            )
        return active

    def encounter_entries(self, location_id: str) -> list[dict]:
        base_entries = self.get_location(location_id).get("encounters", [])
        dungeon = self.dungeon_profile(location_id)
        entries = []
        for entry in self.filter_encounter_entries(base_entries):
            weighted_entry = copy.deepcopy(entry)
            weighted_entry["weight"] = self._ranked_entry_weight(dungeon or {}, weighted_entry)
            entries.append(weighted_entry)
        for state in self.get_location_states(location_id):
            modifiers = state.get("encounter_modifiers", [])
            if isinstance(modifiers, list):
                entries.extend(self.filter_encounter_entries(modifiers))
        entries.extend(self.regional_encounter_modifiers(location_id))
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
                entries.append({"type": "enemy", "target": enemy_id, "weight": int(dungeon.get("enemy_weight", 18))})
                existing.add(key)
            elite_weight = int(dungeon.get("elite_weight", 0))
            for enemy_id in dungeon.get("elite_pool", []):
                key = ("enemy", enemy_id)
                if key in existing or elite_weight <= 0:
                    continue
                entries.append({"type": "enemy", "target": enemy_id, "weight": elite_weight})
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
        regional_note = self.regional_npc_dialogue_note(location_id, normalized_npc)
        if regional_note:
            return regional_note
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
        query = " ".join(query.strip().lower().split())
        normalized_query = query
        for prefix in ("the ", "a ", "an "):
            if normalized_query.startswith(prefix):
                normalized_query = normalized_query[len(prefix):].strip()
        for enemy_id in self.get_enemies_at(location_id):
            enemy = self.enemies.get(enemy_id, {})
            enemy_name = " ".join(str(enemy.get("name", "")).strip().lower().split())
            simplified_name = enemy_name
            for prefix in ("the ", "a ", "an "):
                if simplified_name.startswith(prefix):
                    simplified_name = simplified_name[len(prefix):].strip()
            if (
                normalized_query == enemy_id.lower()
                or normalized_query == enemy_name
                or normalized_query == simplified_name
                or (normalized_query and normalized_query in enemy_name)
            ):
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
        world_state["_regional_events"] = {
            region_id: copy.deepcopy(entries)
            for region_id, entries in self.active_regional_events_by_region.items()
            if entries
        }
        if self.active_road_encounter:
            world_state["_road_encounter"] = copy.deepcopy(self.active_road_encounter)
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

        regional_data = data.get("_regional_events", {})
        self.active_regional_events_by_region = {}
        if isinstance(regional_data, dict):
            for region_id, entries in regional_data.items():
                normalized_region = str(region_id).strip().lower()
                if normalized_region not in self.regional_event_zones:
                    continue
                if not isinstance(entries, list):
                    continue
                restored_entries = []
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    event_id = str(entry.get("event_id", "")).strip().lower()
                    event_data = self._regional_event_entry(event_id)
                    if not event_data:
                        continue
                    location_id = str(entry.get("location_id", event_data.get("location_id", ""))).strip().lower()
                    if location_id not in self.locations:
                        continue
                    restored = {
                        "event_id": event_id,
                        "region_id": normalized_region,
                        "location_id": location_id,
                        "turns_active": max(0, int(entry.get("turns_active", 0) or 0)),
                        "stage": int(event_data.get("stage", entry.get("stage", 1)) or 1),
                        "chain_id": str(event_data.get("chain_id", entry.get("chain_id", ""))).strip().lower(),
                    }
                    restored_entries.append(restored)
                    self._sync_regional_state_side_effects(location_id, event_data)
                if restored_entries:
                    self.active_regional_events_by_region[normalized_region] = restored_entries

        road_encounter = data.get("_road_encounter", {})
        self.active_road_encounter = {}
        if isinstance(road_encounter, dict):
            encounter_id = str(road_encounter.get("encounter_id", "")).strip().lower()
            location_id = str(road_encounter.get("location_id", "")).strip().lower()
            enemy_id = str(road_encounter.get("enemy_id", "")).strip().lower()
            if encounter_id and location_id in self.locations and enemy_id and self.has_enemy(enemy_id):
                self.active_road_encounter = {
                    "encounter_id": encounter_id,
                    "name": str(road_encounter.get("name", encounter_id)).strip(),
                    "route_id": str(road_encounter.get("route_id", "")).strip().lower(),
                    "location_id": location_id,
                    "enemy_id": enemy_id,
                }

    def set_active_road_encounter(self, encounter_id: str, name: str, route_id: str, location_id: str, enemy_id: str) -> None:
        normalized_location = str(location_id).strip().lower()
        normalized_enemy = self._normalize_entity_id(enemy_id)
        if normalized_location not in self.locations or not self.has_enemy(normalized_enemy):
            return
        self.active_road_encounter = {
            "encounter_id": str(encounter_id).strip().lower(),
            "name": str(name).strip(),
            "route_id": str(route_id).strip().lower(),
            "location_id": normalized_location,
            "enemy_id": normalized_enemy,
        }

    def clear_active_road_encounter(self, location_id: str, enemy_id: str) -> dict | None:
        if not self.active_road_encounter:
            return None
        normalized_location = str(location_id).strip().lower()
        normalized_enemy = self._normalize_entity_id(enemy_id)
        if (
            str(self.active_road_encounter.get("location_id", "")).strip().lower() != normalized_location
            or str(self.active_road_encounter.get("enemy_id", "")).strip().lower() != normalized_enemy
        ):
            return None
        payload = copy.deepcopy(self.active_road_encounter)
        self.active_road_encounter = {}
        return payload

    def map_lines(self, current_location: str) -> list[str]:
        lines = ["World Map"]
        for location_id, location in self.locations.items():
            location_name = location.get("name", self._fallback_name(location_id))
            current_marker = " [YOU]" if location_id == current_location else ""
            rank_text = self.location_rank_text(location_id)
            rank_suffix = f" | rank: {rank_text}" if rank_text else ""
            hub_data = location.get("major_hub", {})
            hub_suffix = ""
            if isinstance(hub_data, dict):
                hub_name = str(hub_data.get("name", "")).strip()
                if hub_name:
                    hub_suffix = f" | hub: {hub_name}"
            exits = location.get("connected_locations", {})
            if not exits:
                lines.append(f"- {location_name}{current_marker}{rank_suffix}{hub_suffix} | exits: none")
                continue

            exit_text = ", ".join(
                f"{direction}->{self.locations.get(target_id, {}).get('name', self._fallback_name(target_id))}"
                for direction, target_id in exits.items()
            )
            lines.append(f"- {location_name}{current_marker}{rank_suffix}{hub_suffix} | exits: {exit_text}")

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
        for event in self.active_regional_events():
            location_id = str(event.get("location_id", "")).strip().lower()
            location_name = str(event.get("location_name", self._fallback_name(location_id))).strip()
            label = " [YOU]" if location_id == current_location else ""
            lines.append(f"- {location_name}{label}: {event.get('name', event.get('event_id', 'Regional Event'))}")
        return lines
