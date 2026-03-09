import json
import hashlib
import re
import re
import time
from datetime import datetime
from pathlib import Path

from ai.dm_context import DMContextBuilder
from ai.intent_parser import IntentParseResult, IntentParser
from ai.narrator import Narrator
from ai.scene_composer import SceneComposer
from engine.action_router import ActionRouter
from engine.abilities import AbilityEngine
from engine.campaign import CampaignEngine
from engine.combat import CombatEngine
from engine.contracts import ContractEngine
from engine.crafting import CraftingEngine
from engine.dice import DiceEngine
from engine.encounters import EncounterEngine
from engine.factions import FactionEngine
from engine.inventory import InventoryEngine
from engine.quests import QuestEngine
from engine.world import World
from player.character import Character


class Game:
    """Engine-first RPG core: tracks locations, inventory, quests, events, and persistence."""
    LEGACY_SAVE_FILE = "savegame.json"
    SAVE_DIR = "saves"
    GLOBAL_UNLOCK_FILE = "account_unlocks.json"
    DEFAULT_SLOT = "1"
    CONTRACT_BOARD_LOCATION = "market_square"
    SAFE_REST_LOCATIONS = {"village_square", "shop", "inn", "stormbreak", "valewood", "emberfall", "vaultreach"}
    CRAFTING_STATIONS = {
        "shop": {"alchemy"},
        "blacksmith": {"forge"},
        "weapon_shop": {"forge"},
        "mage_shop": {"alchemy"},
        "town_shrine": {"alchemy"},
        "ruined_shrine": {"alchemy"},
        "ironridge_forge": {"forge"},
    }
    UPGRADE_SERVICE_NPCS = {"blacksmith", "fletcher", "arcanist", "forgemistress"}
    CRAFTING_SERVICE_NPCS = {
        "merchant": "alchemy",
        "blacksmith": "forge",
        "arcanist": "alchemy",
        "shrine_caretaker": "alchemy",
        "forgemistress": "forge",
    }
    IMPORTANT_ITEM_IDS = {
        "rusty_sword",
        "wolf_pelt",
        "guardian_sigil",
        "sundered_crest",
        "weeping_resin",
        "ironfang_alpha_fang",
        "ash_mark_cinder",
        "vault_core",
    }
    HUNTER_GUILD_RANKS = [
        ("Iron", 0),
        ("Bronze", 20),
        ("Silver", 45),
        ("Gold", 75),
        ("Platinum", 110),
    ]
    HUNTER_GUILD_CONTRACT_POINTS = {
        "E": 6,
        "D": 10,
        "C": 14,
        "B": 18,
        "A": 24,
        "S": 30,
    }
    HUNTER_GUILD_BOSS_POINTS = {
        "gorgos_the_sundered": 10,
        "vorgar_ironfang_alpha": 8,
        "weeping_husk": 8,
        "cinder_guardian": 9,
        "ash_herald": 10,
        "vault_keeper": 12,
    }
    HUNTER_GUILD_QUEST_POINTS = {
        "q001_clear_forest_path": 4,
        "q003_watchtower_threat": 4,
        "q005_sigil_for_the_caretaker": 5,
    }
    RIVAL_HUNTER_IDS = {
        "havik_ironborn",
        "dessa",
        "old_crane",
        "sable",
        "brother_aldun",
    }
    NPC_REACTION_CATEGORY_ORDER = {
        "major_story_events": 1,
        "boss_defeats": 2,
        "faction_reputation": 3,
        "rank_recognition": 4,
        "generic": 5,
    }
    TALKABLE_NPCS = {
        "elder": "Elder",
        "merchant": "Merchant",
        "scout": "Scout",
        "caretaker": "Caretaker",
    }
    NPC_ALIASES = {
        "elder": ("village elder", "elder of the village"),
        "merchant": ("shopkeeper", "trader"),
        "scout": ("forest scout", "watchtower scout"),
        "caretaker": ("shrine caretaker", "shrine keeper"),
    }
    COMMAND_NAMES = {
        "look",
        "inspect",
        "search",
        "map",
        "move",
        "fight",
        "take",
        "inventory",
        "gear",
        "character",
        "sheet",
        "stats",
        "skills",
        "abilities",
        "recap",
        "story",
        "history",
        "world",
        "events",
        "reputation",
        "factions",
        "relations",
        "hint",
        "rest",
        "use",
        "cast",
        "ability",
        "quests",
        "quest",
        "board",
        "contracts",
        "routes",
        "travel",
        "activities",
        "journal",
        "about",
        "talk",
        "ask",
        "accept",
        "claim",
        "do",
        "buy",
        "sell",
        "recipes",
        "craft",
        "upgrade",
        "save",
        "load",
        "slots",
        "delete",
        "help",
        "quit",
    }
    NLP_COMMAND_TRIGGERS = {"ask", "fight", "inspect", "look", "move", "take", "talk", "use"}
    ACTION_COMMAND_TRIGGERS = {"fight", "move", "take", "use"}

    def __init__(
        self,
        data_dir: str = "data",
        player_name: str = "Hero",
        character_profile: dict | None = None,
        save_root: str | Path = ".",
    ):
        self.data_dir = data_dir
        self.save_root = Path(save_root)
        self.save_dir = self.save_root / self.SAVE_DIR
        self.legacy_save_path = self.save_root / self.LEGACY_SAVE_FILE
        self.current_slot = self.DEFAULT_SLOT
        self.save_path = self._slot_path(self.current_slot)
        self.unlocks_path = self.save_dir / self.GLOBAL_UNLOCK_FILE
        self.unlocked_classes = set()
        self.unlocked_races = set()
        self.playtime_seconds = 0
        self.session_started_at = time.time()
        self.world = World(self.data_dir)
        if isinstance(character_profile, dict):
            self.player = Character.create_from_profile(
                name=str(character_profile.get("name", player_name)),
                gender=str(character_profile.get("gender", "other")),
                race=str(character_profile.get("race", "human")),
                player_class=str(character_profile.get("player_class", "warrior")),
                background=str(character_profile.get("background", "village_born")),
                bio=str(character_profile.get("bio", "")),
            )
        else:
            self.player = Character(name=player_name)
        self.current_location = self.world.starting_location
        self.current_dungeon_room = None
        self._load_npc_registry()

        self.combat = CombatEngine()
        self.abilities = AbilityEngine()
        self.dice = DiceEngine()
        self.encounters = EncounterEngine()
        self.factions = FactionEngine(self.world.factions)
        self.campaign = CampaignEngine(self.world.arcs)
        self.crafting = CraftingEngine()
        self.inventory = InventoryEngine()
        self.quests = QuestEngine(self.world.quests, self.world.items)
        self.contracts = ContractEngine(self.world.contracts, self.world.items)
        self.intent_parser = IntentParser()
        self.action_router = ActionRouter()
        self.dm_context = DMContextBuilder()
        self.scene_composer = SceneComposer()

        self.running = True
        self._ensure_save_storage()
        self._load_global_unlocks()
        self._sync_social_state()
        self._record_location_visit(self.current_location)
        self.contracts.sync_active_targets(self.player, self.world)
        self._refresh_hunter_guild_rank(source="campaign start")
        self._refresh_titles(notify=False, source="campaign start")

    @classmethod
    def _normalize_slot_id(cls, slot_id: str) -> str:
        raw = str(slot_id).strip().lower()
        if not raw:
            return cls.DEFAULT_SLOT
        match = re.search(r"(\d+)", raw)
        if not match:
            return ""
        normalized = str(int(match.group(1)))
        return normalized if normalized else ""

    def _slot_path(self, slot_id: str) -> Path:
        normalized = self._normalize_slot_id(slot_id) or self.DEFAULT_SLOT
        return self.save_dir / f"slot_{normalized}.json"

    def _set_active_slot(self, slot_id: str) -> None:
        normalized = self._normalize_slot_id(slot_id) or self.DEFAULT_SLOT
        self.current_slot = normalized
        self.save_path = self._slot_path(normalized)

    def _slot_sort_key(self, path: Path) -> tuple[int, str]:
        normalized = self._normalize_slot_id(path.stem)
        if normalized:
            return int(normalized), path.name
        return 9999, path.name

    def _slot_files(self) -> list[Path]:
        if not self.save_dir.exists():
            return []
        return sorted(
            [path for path in self.save_dir.glob("slot_*.json") if path.is_file()],
            key=self._slot_sort_key,
        )

    def _default_slot_choice(self) -> str:
        existing = {self._normalize_slot_id(path.stem) for path in self._slot_files()}
        index = 1
        while str(index) in existing:
            index += 1
        return str(index)

    def default_slot_choice(self) -> str:
        self._ensure_save_storage()
        return self._default_slot_choice()

    @staticmethod
    def _format_playtime(playtime_seconds: int) -> str:
        total = max(0, int(playtime_seconds))
        hours, remainder = divmod(total, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _current_playtime_seconds(self) -> int:
        elapsed = max(0, int(time.time() - self.session_started_at))
        return max(0, int(self.playtime_seconds) + elapsed)

    def _slot_meta_from_data(self, data: dict, slot_id: str, path: Path) -> dict:
        player_data = data.get("player", {}) if isinstance(data, dict) else {}
        slot_meta = data.get("slot_meta", {}) if isinstance(data, dict) else {}
        location_id = str(data.get("current_location", self.world.starting_location)) if isinstance(data, dict) else self.world.starting_location
        location_name = self.world.locations.get(location_id, {}).get("name", location_id)
        saved_at = str(slot_meta.get("saved_at", "")).strip()
        if not saved_at:
            try:
                saved_at = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
            except OSError:
                saved_at = ""
        return {
            "slot_id": self._normalize_slot_id(slot_meta.get("slot_id", slot_id)) or self._normalize_slot_id(slot_id) or self.DEFAULT_SLOT,
            "character_name": str(slot_meta.get("character_name", player_data.get("name", "Hero"))).strip() or "Hero",
            "race": str(slot_meta.get("race", player_data.get("race", "Human"))).strip() or "Human",
            "player_class": str(slot_meta.get("player_class", player_data.get("player_class", "Warrior"))).strip() or "Warrior",
            "level": max(1, int(slot_meta.get("level", player_data.get("level", 1)) or 1)),
            "current_location": location_id,
            "current_location_name": str(slot_meta.get("current_location_name", location_name)).strip() or location_name,
            "saved_at": saved_at,
            "playtime_seconds": max(0, int(slot_meta.get("playtime_seconds", 0) or 0)),
        }

    def _read_save_file(self, path: Path) -> tuple[dict | None, str | None]:
        if not path.exists():
            return None, f"No save file found at {path}."
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except OSError as exc:
            return None, f"Could not load game: {exc}"
        except json.JSONDecodeError:
            return None, f"Could not load game: {path} is not valid JSON."
        if not isinstance(data, dict):
            return None, "Could not load game: save data format is invalid."
        return data, None

    def _ensure_save_storage(self) -> None:
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self._migrate_legacy_save()

    def _load_global_unlocks(self) -> None:
        self.unlocked_classes = set(Character.default_unlocked_class_ids())
        self.unlocked_races = set(Character.default_unlocked_race_ids())
        if self.unlocks_path.exists():
            data, error = self._read_save_file(self.unlocks_path)
            if not error and isinstance(data, dict):
                for category, unlocked_ids in (
                    ("class", data.get("classes", [])),
                    ("race", data.get("races", [])),
                ):
                    if not isinstance(unlocked_ids, list):
                        continue
                    catalog = (
                        Character.class_catalog()
                        if category == "class"
                        else Character.race_catalog()
                    )
                    for option_id in unlocked_ids:
                        normalized = Character._normalize_key(str(option_id))
                        if normalized not in catalog:
                            continue
                        if category == "class":
                            self.unlocked_classes.add(normalized)
                        else:
                            self.unlocked_races.add(normalized)
        self._persist_global_unlocks()

    def _persist_global_unlocks(self) -> None:
        payload = {
            "classes": sorted(
                class_id
                for class_id in self.unlocked_classes
                if class_id in Character.class_catalog()
            ),
            "races": sorted(
                race_id
                for race_id in self.unlocked_races
                if race_id in Character.race_catalog()
            ),
        }
        self.unlocks_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def available_creation_options(self, category: str) -> list[dict]:
        options = Character.creation_options(category)
        normalized = str(category).strip().lower().replace("-", "_").replace(" ", "_")
        if normalized == "race":
            return [option for option in options if option.get("id", "") in self.unlocked_races]
        if normalized in {"class", "player_class"}:
            return [option for option in options if option.get("id", "") in self.unlocked_classes]
        return options

    def _unlock_hint_text(self, conditions: dict) -> str:
        if not isinstance(conditions, dict) or not conditions:
            return "Progress further through the campaign."

        minimum_rank = str(conditions.get("requires_rank", "")).strip().upper()
        if minimum_rank:
            return f"Reach {minimum_rank}-rank contract standing."

        quest_requirements = conditions.get("requires_quests", [])
        if isinstance(quest_requirements, list) and quest_requirements:
            quest_id = ""
            first = quest_requirements[0]
            if isinstance(first, str):
                quest_id = str(first).strip().lower()
            elif isinstance(first, dict):
                quest_id = str(first.get("quest_id", "")).strip().lower()
            if quest_id:
                quest_title = str(self.quests.quests.get(quest_id, {}).get("title", quest_id.replace("_", " ").title())).strip()
                return f"Complete quest: {quest_title}."

        contract_requirements = conditions.get("requires_contracts_completed", [])
        if isinstance(contract_requirements, list) and contract_requirements:
            contract_id = ""
            first = contract_requirements[0]
            if isinstance(first, str):
                contract_id = str(first).strip().lower()
            elif isinstance(first, dict):
                contract_id = str(first.get("contract_id", "")).strip().lower()
            if contract_id:
                contract_title = str(self.contracts.contracts.get(contract_id, {}).get("title", contract_id.replace("_", " ").title())).strip()
                return f"Complete contract: {contract_title}."

        reputation_requirements = conditions.get("requires_reputation", [])
        if isinstance(reputation_requirements, list) and reputation_requirements:
            first = reputation_requirements[0]
            if isinstance(first, dict):
                faction_id = str(first.get("faction", "")).strip().lower()
                minimum = int(first.get("min", 0) or 0)
                if faction_id:
                    return f"Reach {minimum} reputation with {self.factions.faction_name(faction_id)}."

        event_requirements = conditions.get("requires_events", [])
        if isinstance(event_requirements, list) and event_requirements:
            first = event_requirements[0]
            if isinstance(first, dict):
                event_type = str(first.get("type", "")).strip().lower()
                details = first.get("details", {})
                if isinstance(details, dict):
                    enemy_id = str(details.get("enemy_id", "")).strip().lower()
                    if enemy_id:
                        return f"Defeat {self.world.enemy_name(enemy_id)}."
                    location_id = str(details.get("location_id", "")).strip().lower()
                    if location_id:
                        location_name = self.world.get_location(location_id).get("name", location_id.replace("_", " ").title())
                        return f"Reach {location_name}."
                if event_type:
                    return f"Achieve event milestone: {event_type.replace('_', ' ')}."

        return "Progress further through the campaign."

    @staticmethod
    def _lore_hook(lore_text: str, max_length: int = 90) -> str:
        text = " ".join(str(lore_text or "").strip().split())
        if not text:
            return ""
        for delimiter in (". ", "; ", ": "):
            if delimiter in text:
                text = text.split(delimiter, 1)[0].strip()
                break
        if len(text) <= max_length:
            return text
        return text[: max_length - 3].rstrip() + "..."

    def locked_creation_preview_options(self, category: str) -> list[dict]:
        normalized = str(category).strip().lower().replace("-", "_").replace(" ", "_")
        if normalized == "race":
            visible_ids = set(self.unlocked_races)
            catalog = Character.race_catalog()
        elif normalized in {"class", "player_class"}:
            visible_ids = set(self.unlocked_classes)
            catalog = Character.class_catalog()
        else:
            return []

        previews = []
        for option_id, option in catalog.items():
            if option_id in visible_ids:
                continue
            lore = str(option.get("lore", "")).strip()
            previews.append(
                {
                    "id": option_id,
                    "name": str(option.get("name", option_id.replace("_", " ").title())),
                    "lore_hook": self._lore_hook(lore),
                    "unlock_hint": self._unlock_hint_text(option.get("unlock_conditions", {})),
                }
            )
        return previews

    def _event_requirement_met(self, requirement: dict) -> bool:
        if not isinstance(requirement, dict):
            return True
        event_type = str(requirement.get("type", "")).strip().lower()
        details = requirement.get("details", {})
        if not event_type:
            return True
        if not isinstance(details, dict) or not details:
            return self.player.has_event(event_type)
        for key, value in details.items():
            if not self.player.has_event(event_type, str(key), value):
                return False
        return True

    def _quest_requirement_met(self, requirement) -> bool:
        if isinstance(requirement, str):
            return str(requirement).strip().lower() in self.quests.completed
        if not isinstance(requirement, dict):
            return True
        quest_id = str(requirement.get("quest_id", "")).strip().lower()
        if not quest_id:
            return True
        if bool(requirement.get("completed", True)) and quest_id not in self.quests.completed:
            return False
        return True

    def _contract_requirement_met(self, requirement) -> bool:
        if isinstance(requirement, str):
            contract_id = str(requirement).strip().lower()
            return bool(contract_id) and int(self.contracts.completed_counts.get(contract_id, 0)) > 0
        if not isinstance(requirement, dict):
            return True
        contract_id = str(requirement.get("contract_id", "")).strip().lower()
        minimum = max(1, int(requirement.get("count", 1) or 1))
        if not contract_id:
            return False
        return int(self.contracts.completed_counts.get(contract_id, 0)) >= minimum

    def _npc_trust_requirement_met(self, requirement: dict) -> bool:
        if not isinstance(requirement, dict):
            return True
        npc_id = str(requirement.get("npc", "")).strip().lower()
        minimum = int(requirement.get("min", 0) or 0)
        if not npc_id:
            return True
        return self.player.npc_trust(npc_id) >= minimum

    def _unlock_conditions_met(self, conditions: dict, *, unlocked_by_default: bool = False) -> bool:
        if unlocked_by_default:
            return True
        if not isinstance(conditions, dict) or not conditions:
            return False

        event_requirements = conditions.get("requires_events", [])
        if isinstance(event_requirements, list) and event_requirements:
            if not all(self._event_requirement_met(requirement) for requirement in event_requirements):
                return False

        reputation_requirements = conditions.get("requires_reputation", [])
        if isinstance(reputation_requirements, list) and reputation_requirements:
            for requirement in reputation_requirements:
                if not isinstance(requirement, dict):
                    continue
                faction_id = str(requirement.get("faction", "")).strip().lower()
                minimum = int(requirement.get("min", 0) or 0)
                if faction_id and self.player.reputation_value(faction_id) < minimum:
                    return False

        quest_requirements = conditions.get("requires_quests", [])
        if isinstance(quest_requirements, list) and quest_requirements:
            if not all(self._quest_requirement_met(requirement) for requirement in quest_requirements):
                return False

        contract_requirements = conditions.get("requires_contracts_completed", [])
        if isinstance(contract_requirements, list) and contract_requirements:
            if not all(self._contract_requirement_met(requirement) for requirement in contract_requirements):
                return False

        trust_requirements = conditions.get("requires_npc_trust", [])
        if isinstance(trust_requirements, list) and trust_requirements:
            if not all(self._npc_trust_requirement_met(requirement) for requirement in trust_requirements):
                return False

        minimum_rank = str(conditions.get("requires_rank", "")).strip().upper()
        if minimum_rank:
            current_rank = self.contracts.highest_unlocked_rank()
            if self.world.rank_value(current_rank) < self.world.rank_value(minimum_rank):
                return False

        minimum_hunter_rank = Character.normalize_hunter_guild_rank(conditions.get("requires_hunter_guild_rank", ""))
        if minimum_hunter_rank and minimum_hunter_rank != "Iron":
            if Character.hunter_guild_rank_value(self.player.hunter_guild_rank) < Character.hunter_guild_rank_value(minimum_hunter_rank):
                return False

        return True

    def _hunter_guild_rank_from_points(self, points: int) -> tuple[str, int | None]:
        normalized_points = max(0, int(points))
        current_rank = self.HUNTER_GUILD_RANKS[0][0]
        next_threshold = None
        for rank_name, threshold in self.HUNTER_GUILD_RANKS:
            if normalized_points >= threshold:
                current_rank = rank_name
                next_threshold = None
                continue
            next_threshold = threshold
            break
        return current_rank, next_threshold

    def _hunter_guild_progress_summary(self) -> dict:
        points = 0
        for contract_id, count in self.contracts.completed_counts.items():
            if int(count or 0) <= 0:
                continue
            contract = self.contracts.contracts.get(contract_id, {})
            category = str(contract.get("category", "")).strip().lower()
            faction_rewards = contract.get("faction_rewards", {})
            supports_hunters_guild = (
                isinstance(faction_rewards, dict) and int(faction_rewards.get("hunters_guild", 0) or 0) > 0
            ) or category in {"hunter_extermination", "cult_hunt", "shrine_cleansing"}
            if not supports_hunters_guild:
                continue
            contract_rank = str(contract.get("rank", "E")).strip().upper()
            points += self.HUNTER_GUILD_CONTRACT_POINTS.get(contract_rank, 6) * int(count or 0)

        for enemy_id, bonus in self.HUNTER_GUILD_BOSS_POINTS.items():
            if self.player.has_event("miniboss_defeated", "enemy_id", enemy_id) or self.player.has_event("enemy_defeated", "enemy_id", enemy_id):
                points += int(bonus)

        for quest_id, bonus in self.HUNTER_GUILD_QUEST_POINTS.items():
            if self.player.has_event("quest_completed", "quest_id", quest_id):
                points += int(bonus)

        rank_name, next_threshold = self._hunter_guild_rank_from_points(points)
        current_threshold = 0
        for candidate_rank, threshold in self.HUNTER_GUILD_RANKS:
            if candidate_rank == rank_name:
                current_threshold = threshold
                break
        progress_in_rank = max(0, points - current_threshold)
        needed = max(0, next_threshold - points) if next_threshold is not None else 0
        return {
            "rank": rank_name,
            "points": points,
            "next_threshold": next_threshold,
            "progress_in_rank": progress_in_rank,
            "needed": needed,
        }

    def _refresh_hunter_guild_rank(self, source: str = "") -> list[str]:
        summary = self._hunter_guild_progress_summary()
        previous_rank = Character.normalize_hunter_guild_rank(self.player.hunter_guild_rank)
        previous_points = max(0, int(self.player.hunter_guild_points or 0))
        self.player.hunter_guild_rank = summary["rank"]
        self.player.hunter_guild_points = int(summary["points"])

        if previous_rank == summary["rank"] and previous_points == summary["points"]:
            return []

        lines = []
        if Character.hunter_guild_rank_value(summary["rank"]) > Character.hunter_guild_rank_value(previous_rank):
            next_threshold = summary.get("next_threshold")
            progress_note = "You now stand among the guild's proven hunters."
            if next_threshold is not None:
                progress_note = f"{summary['needed']} points remain until {self._hunter_guild_rank_from_points(next_threshold)[0]}."
            text = (
                f"The Hunter Guild advances you to {summary['rank']} rank. "
                f"Contracts, boss marks, and hard field work have begun to add up. {progress_note}"
            )
            self._log_event(
                "hunter_guild_rank_up",
                rank=summary["rank"],
                points=int(summary["points"]),
                source=source,
                location_id=self.current_location,
                location_name=self.current_location_name(),
                text=text,
            )
            lines.append("Hunter Guild: " + text)
        return lines

    def _mark_rival_hunter_seen(self, npc_id: str) -> None:
        normalized_npc = str(npc_id).strip().lower()
        if normalized_npc not in self.RIVAL_HUNTER_IDS:
            return
        entry = dict(self.player.rival_hunter_flags.get(normalized_npc, {}))
        entry["met"] = True
        entry["spoken"] = max(0, int(entry.get("spoken", 0))) + 1
        entry["last_location"] = self.current_location
        self.player.rival_hunter_flags[normalized_npc] = entry

    def _authored_content_conditions_met(self, entry: dict) -> bool:
        if not isinstance(entry, dict):
            return False
        single_condition = entry.get("condition")
        if isinstance(single_condition, str) and single_condition.strip():
            return self._named_condition_met(single_condition)
        if isinstance(single_condition, list) and single_condition:
            return all(self._named_condition_met(condition) for condition in single_condition)
        conditions = entry.get("conditions", {})
        if not isinstance(conditions, dict) or not conditions:
            return True
        return self._unlock_conditions_met(conditions, unlocked_by_default=False)

    def _named_condition_met(self, condition: str) -> bool:
        normalized = str(condition or "").strip().lower()
        if not normalized:
            return True

        if normalized == "boss_gorgos_defeated":
            return self.player.has_event("miniboss_defeated", "enemy_id", "gorgos_the_sundered")
        if normalized == "shrine_chain_completed":
            return self.player.has_event("quest_completed", "quest_id", "q005_sigil_for_the_caretaker")

        rank_at_least = re.fullmatch(r"player_rank_at_least_([a-z])", normalized)
        if rank_at_least:
            required_rank = rank_at_least.group(1).upper()
            current_rank = self.contracts.highest_unlocked_rank()
            return self.world.rank_value(current_rank) >= self.world.rank_value(required_rank)

        rank_or_higher = re.fullmatch(r"player_rank_([a-z])_or_higher", normalized)
        if rank_or_higher:
            required_rank = rank_or_higher.group(1).upper()
            current_rank = self.contracts.highest_unlocked_rank()
            return self.world.rank_value(current_rank) >= self.world.rank_value(required_rank)

        hunter_rank_at_least = re.fullmatch(r"hunter_guild_rank_at_least_([a-z]+)", normalized)
        if hunter_rank_at_least:
            required_rank = Character.normalize_hunter_guild_rank(hunter_rank_at_least.group(1))
            return Character.hunter_guild_rank_value(self.player.hunter_guild_rank) >= Character.hunter_guild_rank_value(required_rank)

        hunter_rank_above = re.fullmatch(r"hunter_guild_rank_above_([a-z]+)", normalized)
        if hunter_rank_above:
            required_rank = Character.normalize_hunter_guild_rank(hunter_rank_above.group(1))
            return Character.hunter_guild_rank_value(self.player.hunter_guild_rank) > Character.hunter_guild_rank_value(required_rank)

        faction_at_least = re.fullmatch(r"faction_([a-z0-9_]+)_at_least_(\d+)", normalized)
        if faction_at_least:
            faction_id = faction_at_least.group(1)
            minimum = int(faction_at_least.group(2))
            return self.player.reputation_value(faction_id) >= minimum

        contract_completed = re.fullmatch(r"contract_([a-z0-9_]+)_completed", normalized)
        if contract_completed:
            contract_id = contract_completed.group(1)
            return int(self.contracts.completed_counts.get(contract_id, 0)) > 0

        quest_completed = re.fullmatch(r"quest_([a-z0-9_]+)_completed", normalized)
        if quest_completed:
            quest_id = quest_completed.group(1)
            return self.player.has_event("quest_completed", "quest_id", quest_id)

        discovered_region = re.fullmatch(r"discovered_([a-z0-9_]+)", normalized)
        if discovered_region:
            location_id = discovered_region.group(1)
            return self.player.has_event("location_visited", "location_id", location_id)

        unlocked_race = re.fullmatch(r"unlocked_race_([a-z0-9_]+)", normalized)
        if unlocked_race:
            return unlocked_race.group(1) in self.unlocked_races

        unlocked_class = re.fullmatch(r"unlocked_class_([a-z0-9_]+)", normalized)
        if unlocked_class:
            return unlocked_class.group(1) in self.unlocked_classes

        earned_title = re.fullmatch(r"(?:title|has_title)_([a-z0-9_]+)", normalized)
        if earned_title:
            return earned_title.group(1) in getattr(self.player, "unlocked_titles", [])

        boss_defeated = re.fullmatch(r"boss_([a-z0-9_]+)_defeated", normalized)
        if boss_defeated:
            enemy_id = boss_defeated.group(1)
            return self.player.has_event("miniboss_defeated", "enemy_id", enemy_id)

        return False

    @staticmethod
    def _topic_matches_entry(topic: str, entry: dict) -> bool:
        normalized_topic = " ".join(str(topic or "").strip().lower().split())
        if not normalized_topic:
            return True

        broad_topics = {"rumor", "rumors", "news", "road", "roads", "travel", "route", "routes", "work", "contracts", "contract"}
        if normalized_topic in broad_topics:
            return True

        topics = entry.get("topics", [])
        if not isinstance(topics, list) or not topics:
            return False

        for candidate in topics:
            normalized_candidate = " ".join(str(candidate or "").strip().lower().split())
            if not normalized_candidate:
                continue
            if normalized_topic == normalized_candidate:
                return True
            if normalized_topic in normalized_candidate or normalized_candidate in normalized_topic:
                return True
        return False

    def _npc_authored_lines(self, npc_id: str, field: str, *, topic: str = "", limit: int = 2) -> list[str]:
        return [entry["text"] for entry in self._npc_authored_entries(npc_id, field, topic=topic, limit=limit)]

    def _npc_authored_entries(self, npc_id: str, field: str, *, topic: str = "", limit: int = 2) -> list[dict]:
        npc_data = self.world.get_npc(npc_id)
        entries = []
        inline_entries = npc_data.get(field, [])
        if isinstance(inline_entries, list):
            entries.extend(inline_entries)
        if str(field).strip().lower() == "rumors":
            rumor_pools = npc_data.get("rumor_pools", [])
            if isinstance(rumor_pools, list):
                for pool_id in rumor_pools:
                    pool_entries = getattr(self.world, "rumors", {}).get(str(pool_id).strip().lower(), [])
                    if isinstance(pool_entries, list):
                        entries.extend(pool_entries)
        if not entries:
            return []

        matched = []
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            text = str(entry.get("text", "")).strip()
            if not text or not self._authored_content_conditions_met(entry):
                continue
            entry_topics = entry.get("topics", [])
            if topic and isinstance(entry_topics, list) and entry_topics and not self._topic_matches_entry(topic, entry):
                continue
            category = str(entry.get("category", "generic")).strip().lower() or "generic"
            priority = int(entry.get("priority", 0) or 0)
            category_order = self.NPC_REACTION_CATEGORY_ORDER.get(category, self.NPC_REACTION_CATEGORY_ORDER["generic"])
            if str(field).strip().lower() == "reactions":
                sort_key = (category_order, -priority, index)
            else:
                sort_key = (0, -priority, index)
            matched.append(
                (
                    sort_key,
                    {
                        "text": text,
                        "category": category,
                        "priority": priority,
                    },
                )
            )

        matched.sort(key=lambda item: item[0])
        return [entry for _, entry in matched[:max(0, limit)]]

    def _class_unlock_conditions_met(self, class_data: dict) -> bool:
        return self._unlock_conditions_met(
            class_data.get("unlock_conditions", {}),
            unlocked_by_default=bool(class_data.get("unlocked_by_default", True)),
        )

    def _race_unlock_conditions_met(self, race_data: dict) -> bool:
        return self._unlock_conditions_met(
            race_data.get("unlock_conditions", {}),
            unlocked_by_default=bool(race_data.get("unlocked_by_default", True)),
        )

    def _refresh_class_unlocks(self, notify: bool = True, source: str = "") -> list[str]:
        lines = []
        changed = False
        for class_id, class_data in Character.class_catalog().items():
            if class_id in self.unlocked_classes:
                continue
            if not self._class_unlock_conditions_met(class_data):
                continue
            self.unlocked_classes.add(class_id)
            changed = True
            if notify:
                class_name = str(class_data.get("name", class_id.replace("_", " ").title()))
                lines.append(Narrator.class_unlock_text(class_name, source))
        if changed:
            self._persist_global_unlocks()
        return lines

    def _refresh_race_unlocks(self, notify: bool = True, source: str = "") -> list[str]:
        lines = []
        changed = False
        for race_id, race_data in Character.race_catalog().items():
            if race_id in self.unlocked_races:
                continue
            if not self._race_unlock_conditions_met(race_data):
                continue
            self.unlocked_races.add(race_id)
            changed = True
            if notify:
                race_name = str(race_data.get("name", race_id.replace("_", " ").title()))
                homeland = str(race_data.get("homeland", "")).strip()
                lines.append(Narrator.race_unlock_text(race_name, source=source, homeland=homeland))
        if changed:
            self._persist_global_unlocks()
        return lines

    def _refresh_identity_unlocks(self, notify: bool = True, source: str = "") -> list[str]:
        lines = []
        lines.extend(self._refresh_race_unlocks(notify=notify, source=source))
        lines.extend(self._refresh_class_unlocks(notify=notify, source=source))
        return lines

    def _player_title_entries(self) -> list[dict]:
        entries = []
        for title_id in getattr(self.player, "unlocked_titles", []):
            title_data = self.world.titles.get(title_id, {})
            if not isinstance(title_data, dict):
                title_data = {}
            entries.append(
                {
                    "id": title_id,
                    "name": str(title_data.get("name", title_id.replace("_", " ").title())).strip() or title_id.replace("_", " ").title(),
                    "description": str(title_data.get("description", "")).strip(),
                    "flavor_text": str(title_data.get("flavor_text", "")).strip(),
                }
            )
        return entries

    def _title_summary(self) -> dict:
        entries = self._player_title_entries()
        latest = entries[-1] if entries else {}
        return {
            "count": len(entries),
            "names": [entry["name"] for entry in entries],
            "latest_name": str(latest.get("name", "")).strip(),
            "latest_flavor": str(latest.get("flavor_text", "")).strip(),
        }

    def _refresh_titles(self, notify: bool = True, source: str = "") -> list[str]:
        lines = []
        unlocked_titles = getattr(self.player, "unlocked_titles", [])
        if not isinstance(unlocked_titles, list):
            unlocked_titles = []
            self.player.unlocked_titles = unlocked_titles

        for title_id, title_data in self.world.titles.items():
            normalized_title_id = str(title_id).strip().lower()
            if not normalized_title_id or normalized_title_id in unlocked_titles:
                continue
            if not self._unlock_conditions_met(title_data.get("unlock_conditions", {})):
                continue
            unlocked_titles.append(normalized_title_id)
            title_name = str(title_data.get("name", normalized_title_id.replace("_", " ").title())).strip()
            self._log_event(
                "title_unlocked",
                title_id=normalized_title_id,
                title_name=title_name,
                source=source,
            )
            if notify:
                lines.append(Narrator.title_unlock_text(title_name, str(title_data.get("description", "")).strip()))

        return lines

    def _migrate_legacy_save(self) -> None:
        if not self.legacy_save_path.exists():
            return
        target = self._slot_path(self.DEFAULT_SLOT)
        if target.exists():
            return
        data, error = self._read_save_file(self.legacy_save_path)
        if error or data is None:
            return
        data["slot_meta"] = self._slot_meta_from_data(data, self.DEFAULT_SLOT, self.legacy_save_path)
        target.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            self.legacy_save_path.unlink()
        except OSError:
            pass

    def slot_summaries(self) -> list[dict]:
        self._ensure_save_storage()
        summaries = []
        for path in self._slot_files():
            data, error = self._read_save_file(path)
            if error or data is None:
                continue
            summaries.append(self._slot_meta_from_data(data, path.stem, path))
        return summaries

    def _cmd_slots(self) -> str:
        summaries = self.slot_summaries()
        lines = ["Save Slots"]
        if not summaries:
            lines.append("- none")
            return "\n".join(lines)
        active_path = self.save_path.resolve()
        for summary in summaries:
            slot_id = summary["slot_id"]
            slot_path = self._slot_path(slot_id).resolve()
            marker = " [CURRENT]" if slot_path == active_path else ""
            saved_at = summary["saved_at"] or "unknown time"
            playtime = self._format_playtime(int(summary.get("playtime_seconds", 0)))
            lines.append(
                f"- Slot {slot_id}{marker}: {summary['character_name']} | "
                f"{summary['race']} {summary['player_class']} | "
                f"Level {summary['level']} | "
                f"{summary['current_location_name']} | "
                f"Saved {saved_at} | "
                f"Playtime {playtime}"
            )
        return "\n".join(lines)

    def _cmd_delete(self, arg: str) -> str:
        slot_id = self._normalize_slot_id(arg)
        if not slot_id:
            return "Delete which slot? Use 'delete <slot>'."
        target = self._slot_path(slot_id)
        if not target.exists():
            return f"Slot {slot_id} does not exist."
        try:
            target.unlink()
        except OSError as exc:
            return f"Could not delete slot {slot_id}: {exc}"
        return f"Deleted save slot {slot_id}."

    def _load_npc_registry(self) -> None:
        self.TALKABLE_NPCS = {
            npc_id: self.world.npc_name(npc_id)
            for npc_id in self.world.npcs
        }
        self.NPC_ALIASES = {
            npc_id: tuple(str(alias) for alias in self.world.get_npc(npc_id).get("aliases", []))
            for npc_id in self.world.npcs
        }

    def _sync_social_state(self) -> None:
        self.factions.ensure_player_state(self.player)
        for npc_id, npc_data in self.world.npcs.items():
            if not npc_data.get("important", False):
                continue
            self.player.ensure_npc_memory(npc_id, faction_id=npc_data.get("faction", ""))

    def _log_event(self, event_type: str, **details) -> None:
        """Append deterministic game events so narration and quests stay reactive."""
        self.player.record_event(event_type, details)

    def _change_reputation(self, faction_id: str, amount: int, source: str) -> list[str]:
        change = self.factions.adjust_reputation(self.player, faction_id, amount)
        if not change:
            return []

        self._log_event(
            "reputation_changed",
            faction_id=change["faction_id"],
            faction_name=change["name"],
            amount=change["change"],
            score=change["after"],
            source=source,
        )
        lines = [
            Narrator.reputation_change_text(
                change["name"],
                change["change"],
                change["after"],
                change["tier"],
            )
        ]
        lines.extend(self._refresh_identity_unlocks(source=f"standing with {change['name']}"))
        return lines

    def _change_npc_trust(self, npc_id: str, amount: int, source: str) -> list[str]:
        npc_data = self.world.get_npc(npc_id)
        npc_name = self.world.npc_name(npc_id)
        before = self.player.npc_trust(npc_id)
        after = self.player.adjust_npc_trust(npc_id, amount, faction_id=npc_data.get("faction", ""))
        delta = after - before
        if delta == 0:
            return []

        self._log_event(
            "npc_trust_changed",
            npc_id=npc_id,
            npc_name=npc_name,
            amount=delta,
            trust=after,
            source=source,
        )
        return [Narrator.trust_change_text(npc_name, delta, after, self.factions.tier_name(after))]

    def _apply_social_rewards(self, reputation_changes: dict | None = None, trust_changes: dict | None = None, source: str = "") -> list[str]:
        lines = []
        if isinstance(reputation_changes, dict):
            for faction_id, amount in reputation_changes.items():
                lines.extend(self._change_reputation(str(faction_id), int(amount), source))
        if isinstance(trust_changes, dict):
            for npc_id, amount in trust_changes.items():
                lines.extend(self._change_npc_trust(str(npc_id), int(amount), source))
        return lines

    def _record_location_visit(self, location_id: str) -> None:
        if self.player.has_event("location_visited", "location_id", location_id):
            return
        location_name = self.world.get_location(location_id).get("name", location_id)
        self._log_event("location_visited", location_id=location_id, location_name=location_name)

    def _record_important_item_acquired(self, item_id: str, source: str) -> None:
        if item_id not in self.IMPORTANT_ITEM_IDS and item_id not in self.world.relics:
            return
        if self.player.has_event("important_item_acquired", "item_id", item_id):
            return
        location_id = self.current_location if self.current_location in self.world.locations else ""
        self._log_event(
            "important_item_acquired",
            item_id=item_id,
            item_name=self.world.item_name(item_id),
            source=source,
            location_id=location_id,
            location_name=self.world.get_location(location_id).get("name", location_id) if location_id else "",
        )

    def _apply_contract_item_updates(self) -> list[str]:
        lines = self.contracts.refresh_passive_progress(self.player, self.world)
        if lines:
            location_name = self.world.get_location(self.current_location).get("name", self.current_location)
            lines.extend(self._apply_recent_contract_completions(self.current_location, location_name))
        return lines

    def _backfill_world_progress_events(self) -> None:
        """Ensure event memory reflects world state (needed for legacy saves without history)."""
        forest_path_enemies = self.world.get_enemies_at("forest_path")
        if "slime" not in forest_path_enemies and not self.player.has_event("enemy_defeated", "location_id", "forest_path"):
            self._log_event(
                "enemy_defeated",
                enemy_id="slime",
                enemy_name=self.world.enemy_name("slime"),
                location_id="forest_path",
                location_name=self.world.get_location("forest_path").get("name", "Forest Path"),
            )

        watchtower_enemies = self.world.get_enemies_at("old_watchtower")
        if "slime" not in watchtower_enemies and not self.player.has_event("enemy_defeated", "location_id", "old_watchtower"):
            self._log_event(
                "enemy_defeated",
                enemy_id="slime",
                enemy_name=self.world.enemy_name("slime"),
                location_id="old_watchtower",
                location_name=self.world.get_location("old_watchtower").get("name", "Old Watchtower"),
            )

        shrine_enemies = self.world.get_enemies_at("ruined_shrine")
        if "shrine_guardian" not in shrine_enemies:
            if not self.player.has_event("enemy_defeated", "enemy_id", "shrine_guardian"):
                self._log_event(
                    "enemy_defeated",
                    enemy_id="shrine_guardian",
                    enemy_name=self.world.enemy_name("shrine_guardian"),
                    location_id="ruined_shrine",
                    location_name=self.world.get_location("ruined_shrine").get("name", "Ruined Shrine"),
                )
            if not self.player.has_event("miniboss_defeated", "enemy_id", "shrine_guardian"):
                self._log_event(
                    "miniboss_defeated",
                    enemy_id="shrine_guardian",
                    enemy_name=self.world.enemy_name("shrine_guardian"),
                    location_id="ruined_shrine",
                    location_name=self.world.get_location("ruined_shrine").get("name", "Ruined Shrine"),
                )

        if "guardian_sigil" in self.player.inventory and not self.player.has_event("important_item_acquired", "item_id", "guardian_sigil"):
            self._record_important_item_acquired("guardian_sigil", source="inventory_backfill")

    def _backfill_quest_progress_events(self) -> None:
        for quest_id in sorted(self.quests.completed):
            if self.player.has_event("quest_completed", "quest_id", quest_id):
                continue
            quest_data = self.quests.quests.get(quest_id, {})
            objective = quest_data.get("objective", {})
            location_id = str(objective.get("turn_in", self.current_location)).strip().lower()
            if location_id not in self.world.locations:
                location_id = self.current_location
            self._log_event(
                "quest_completed",
                quest_id=quest_id,
                quest_title=quest_data.get("title", quest_id),
                location_id=location_id,
                location_name=self.world.get_location(location_id).get("name", location_id),
            )

    def _history_flags(self) -> dict:
        """Expose cached progress flags derived from event history for narration/visibility."""
        return {
            "forest_path_cleared": self.player.has_event("enemy_defeated", "location_id", "forest_path"),
            "forest_path_quest_completed": self.player.has_event("quest_completed", "quest_id", "q001_clear_forest_path"),
            "watchtower_cleared": self.player.has_event("enemy_defeated", "location_id", "old_watchtower"),
            "watchtower_sweep_completed": self.player.has_event("quest_completed", "quest_id", "q003_watchtower_threat"),
            "shrine_guardian_defeated": self.player.has_event("miniboss_defeated", "enemy_id", "shrine_guardian"),
            "sigil_quest_completed": self.player.has_event("quest_completed", "quest_id", "q005_sigil_for_the_caretaker"),
            "carrying_guardian_sigil": "guardian_sigil" in self.player.inventory,
            "guardian_sigil_claimed": self.player.has_event("important_item_acquired", "item_id", "guardian_sigil"),
        }

    def _npc_visible(self, npc_id: str) -> bool:
        npc_id = str(npc_id).strip().lower()
        history_flags = self._history_flags()

        if npc_id == "scout":
            return history_flags.get("watchtower_cleared", False)
        if npc_id == "caretaker":
            return history_flags.get("shrine_guardian_defeated", False)
        return True

    def _visible_npcs_at_location(self, location_id: str) -> list[str]:
        npcs = [str(npc).strip().lower() for npc in self.world.get_npcs_at(location_id)]
        return [npc_id for npc_id in npcs if self._npc_visible(npc_id)]

    def _visible_npc_names_at_location(self, location_id: str) -> list[str]:
        return [self.TALKABLE_NPCS.get(npc_id, npc_id.title()) for npc_id in self._visible_npcs_at_location(location_id)]

    def _available_quest_titles_here(self) -> list[str]:
        npcs_here = self._visible_npcs_at_location(self.current_location)
        campaign_context = self.arc_context()
        if len(npcs_here) == 1:
            return self.quests.quest_offer_lines(
                self.player,
                npcs_here[0],
                world=self.world,
                current_location=self.current_location,
                campaign_context=campaign_context,
            )
        return [
            quest.get("title", quest_id)
            for quest_id, quest in self.quests.available_quests(
                self.player,
                npcs_here,
                world=self.world,
                current_location=self.current_location,
                campaign_context=campaign_context,
            )
        ]

    def _resolve_location_events(self, location_id: str) -> list[str]:
        location = self.world.get_location(location_id)
        location_name = location.get("name", location_id)
        lines = []

        for event in self.world.get_location_events(location_id, trigger="enter"):
            effect = event.get("effect", {})
            effect_type = str(effect.get("type", "")).strip().lower()
            event_id = str(event.get("event_id", ""))
            event_name = str(event.get("name", event_id or "World Event"))

            if effect_type == "heal":
                amount = int(effect.get("amount", 0))
                healed = self.player.heal(amount)
                if healed <= 0:
                    continue
                self.world.resolve_event(event_id)
                outcome = f"Recovered {healed} HP."
                self._log_event(
                    "world_event_resolved",
                    event_id=event_id,
                    event_name=event_name,
                    location_id=location_id,
                    location_name=location_name,
                    outcome=outcome,
                )
                lines.append(Narrator.world_event_text(event_name, location_name, outcome))

        return lines

    def _skill_check(self, skill_name: str, dc: int) -> dict:
        modifier = self.player.skill_value(skill_name) + max(0, self.player.stat_modifier("luck"))
        roll = self.dice.roll_d20(modifier)
        return {
            "skill": skill_name,
            "dc": dc,
            "roll": roll,
            "success": roll["total"] >= dc,
        }

    def _grant_xp(self, amount: int, source: str) -> list[str]:
        amount = max(0, int(amount))
        if amount <= 0:
            return []

        known_before = {
            str(ability.get("id", "")).strip().lower()
            for ability in self.abilities.available_to(self.player)
            if str(ability.get("id", "")).strip()
        }
        level_ups = self.player.gain_xp(amount)
        self._log_event("xp_gained", amount=amount, source=source)
        lines = ["You feel more experienced."]
        lines.append(
            Narrator.xp_text(
                amount,
                self.player.level,
                self.player.xp,
                self.player.xp_needed_for_next_level(),
            )
        )

        for level_up in level_ups:
            self._log_event(
                "level_up",
                level=level_up["level"],
                max_hp=level_up["max_hp"],
                max_focus=level_up.get("max_focus", self.player.max_focus),
                base_attack=level_up["base_attack"],
            )
            lines.append(
                Narrator.level_up_text(
                    level_up["level"],
                    level_up["max_hp"],
                    level_up["base_attack"],
                    level_up.get("max_focus"),
                )
            )

        known_after = {
            str(ability.get("id", "")).strip().lower()
            for ability in self.abilities.available_to(self.player)
            if str(ability.get("id", "")).strip()
        }
        unlocked = [ability_id for ability_id in sorted(known_after) if ability_id not in known_before]
        for ability_id in unlocked:
            lines.append(f"You unlocked a new skill: {self._ability_name(ability_id)}.")

        return lines

    def _skill_display_data(self) -> dict[str, dict[str, int | str]]:
        display = {}
        for skill_name in self.player.skill_order():
            stat_name = self.player.SKILL_STAT_MAP.get(skill_name, "mind")
            display[skill_name] = {
                "proficiency": self.player.skill_proficiency(skill_name, self.world.items),
                "total": self.player.skill_value(skill_name, self.world.items),
                "stat": stat_name,
            }
        return display

    def _ability_name(self, ability_id: str) -> str:
        ability = self.abilities.ABILITIES.get(str(ability_id).strip().lower(), {})
        return str(ability.get("name", str(ability_id).replace("_", " ").title()))

    def _combat_ability_lines(self, enemy_id: str | None = None) -> list[str]:
        enemy_name = self.world.enemy_name(enemy_id) if enemy_id else ""
        lines = ["- Attack with: fight <enemy>"]
        available = self.abilities.available_to(self.player)
        affordable = [ability for ability in available if self.player.focus >= int(ability.get("cost", 0))]
        if enemy_id:
            for ability in affordable:
                target = str(ability.get("target", "")).strip().lower()
                if target == "enemy":
                    lines.append(
                        f"- Cast {ability['name']} now: cast {ability['name'].lower()} {enemy_name.lower()} "
                        f"(cost {int(ability.get('cost', 0))})"
                    )
        self_target_lines = []
        for ability in affordable:
            target = str(ability.get("target", "")).strip().lower()
            if target == "self":
                self_target_lines.append(
                    f"- Prepare {ability['name']}: cast {ability['name'].lower()} "
                    f"(cost {int(ability.get('cost', 0))})"
                )
        lines.extend(self_target_lines)
        return lines

    def _enemy_combat_summary(self, enemy_id: str) -> str:
        enemy_data = self.world.enemies.get(enemy_id, {})
        profile = self.combat.preview_enemy(
            enemy_id,
            enemy_data,
            combat_modifiers=self.world.combat_rank_modifiers(self.current_location, enemy_id),
        )
        tags = []
        if self._enemy_is_boss(enemy_id, enemy_data, self.current_location):
            tags.append("boss")
        elif bool(enemy_data.get("elite", False)):
            tags.append("elite")
        rank = str(enemy_data.get("rank", "")).strip().upper()
        if rank:
            tags.append(f"{rank}-rank")
        family = str(profile.get("family", "unknown")).replace("_", " ")
        class_type = str(profile.get("class_type", "foe")).replace("_", " ")
        level = int(profile.get("level", 1))
        abilities = [str(ability.get("name", "")).strip() for ability in profile.get("abilities", [])]
        ability_text = ", ".join(abilities) if abilities else "none"
        tag_text = ", ".join(tags)
        if tag_text:
            return f"{tag_text}; {family}, {class_type}, level {level}. Abilities: {ability_text}."
        return f"{family}, {class_type}, level {level}. Abilities: {ability_text}."

    def _enemy_is_boss(self, enemy_id: str, enemy_data: dict | None = None, location_id: str | None = None) -> bool:
        enemy_data = enemy_data or self.world.enemies.get(enemy_id, {})
        if bool(enemy_data.get("boss", False)):
            return True
        active_location = location_id or self.current_location
        dungeon = self.world.dungeon_profile(active_location) or {}
        boss_pool = {str(candidate).strip().lower() for candidate in dungeon.get("boss_pool", [])}
        return str(enemy_id).strip().lower() in boss_pool

    @staticmethod
    def _deterministic_percent(seed: str) -> int:
        digest = hashlib.sha256(str(seed).encode("utf-8")).hexdigest()
        return (int(digest[:8], 16) % 100) + 1

    @staticmethod
    def _deterministic_index(seed: str, size: int) -> int:
        if size <= 0:
            return 0
        digest = hashlib.sha256(str(seed).encode("utf-8")).hexdigest()
        return int(digest[8:16], 16) % size

    def _roll_boss_relic_drop(self, enemy_id: str, enemy_name: str) -> str | None:
        if self.player.has_event("boss_relic_dropped", "enemy_id", enemy_id):
            return None

        relic_pool = self.world.relic_ids_for_boss(enemy_id)
        if not relic_pool:
            return None

        chance = self.world.boss_relic_drop_chance(enemy_id)
        roll = self._deterministic_percent(f"{self.player.name}|{enemy_id}|relic_roll")
        if roll > chance:
            return None

        pick_index = self._deterministic_index(f"{self.player.name}|{enemy_id}|relic_pick", len(relic_pool))
        relic_id = relic_pool[pick_index]
        self._log_event(
            "boss_relic_dropped",
            enemy_id=enemy_id,
            enemy_name=enemy_name,
            item_id=relic_id,
            item_name=self.world.item_name(relic_id),
            roll=roll,
            chance=chance,
        )
        return relic_id

    @staticmethod
    def _crit_threshold_for_chance(chance: int) -> int:
        steps = max(1, int(chance) // 5)
        return max(15, 21 - steps)

    def _prepared_effect_line(self) -> str:
        if not self.player.has_combat_boosts():
            return ""
        if self.player.combat_boost_summary:
            if self.player.combat_boost_name:
                return f"{self.player.combat_boost_name}: {self.player.combat_boost_summary}"
            return self.player.combat_boost_summary
        return self.player.combat_boost_name

    def _typical_rank(self) -> str:
        contract_rank = self.contracts.highest_unlocked_rank()
        level_rank = self.world.rank_for_level(self.player.level)
        if self.world.rank_value(contract_rank) >= self.world.rank_value(level_rank):
            return contract_rank
        return level_rank

    def _location_rank_warning(self, location_id: str) -> str:
        return self.world.rank_warning_text(location_id, self._typical_rank())

    def _apply_ability_buff(self, ability: dict, buff: dict) -> str:
        if not isinstance(buff, dict) or not buff:
            return ""

        normalized_buff = {}
        for key, amount in buff.items():
            if key not in self.player.DEFAULT_COMBAT_BOOSTS:
                continue
            normalized_buff[str(key)] = int(amount)

        if not normalized_buff:
            return ""

        parts = []
        labels = {
            "attack_bonus": "Accuracy",
            "damage_bonus": "Damage",
            "defense_bonus": "Defense",
            "dodge_bonus": "Dodge",
            "crit_bonus": "Crit",
            "spell_bonus": "Spell Power",
            "heal_bonus": "Healing Power",
            "enemy_attack_penalty": "Enemy Accuracy",
            "enemy_defense_penalty": "Enemy Defense",
        }
        for key, amount in normalized_buff.items():
            sign = "+" if amount >= 0 else ""
            if key == "dodge_bonus":
                parts.append(f"{sign}{amount * 5}% {labels[key]}")
            elif key == "crit_bonus":
                parts.append(f"{sign}{amount}% {labels[key]}")
            else:
                parts.append(f"{sign}{amount} {labels[key]}")

        summary = ", ".join(parts)
        self.player.apply_combat_boost(ability["name"], summary=summary, **normalized_buff)
        return summary

    def _ability_scale_bonus(self, effect: dict) -> int:
        stat_name = str(effect.get("scale_stat", "")).strip().lower()
        secondary_stat = str(effect.get("secondary_stat", "")).strip().lower()
        skill_name = str(effect.get("scale_skill", "")).strip().lower()
        total = 0
        if stat_name in self.player.DEFAULT_STATS:
            total += max(0, self.player.effective_stat_modifier(stat_name, self.world.items))
        if secondary_stat in self.player.DEFAULT_STATS:
            total += max(0, self.player.effective_stat_modifier(secondary_stat, self.world.items))
        if skill_name:
            total += self.player.skill_proficiency(skill_name, self.world.items) // 2
        return total

    def _resolve_opening_ability_attack(self, ability: dict, enemy_id: str, enemy_data: dict) -> dict:
        effect = ability.get("effect", {})
        attack_stat = str(effect.get("scale_stat", self.player.attack_stat_name(self.world.items))).strip().lower()
        attack_modifier = self.player.attack_roll_modifier(
            self.world.items,
            stat_name=attack_stat,
            bonus=int(effect.get("accuracy_bonus", 0)),
        )
        enemy_name = self.world.enemy_name(enemy_id)
        enemy_defense = int(enemy_data.get("defense", self.combat.DEFAULT_ENEMY_DEFENSE))
        if str(enemy_data.get("behavior", "")).strip().lower() == "defensive":
            enemy_defense += 2
        enemy_defense = max(5, enemy_defense - self.player.combat_boosts["enemy_defense_penalty"])

        roll = self.dice.roll_d20(attack_modifier)
        hit = roll["total"] >= enemy_defense
        damage = 0
        critical = False

        if hit:
            damage = max(0, int(effect.get("damage", 0)) + self._ability_scale_bonus(effect))
            crit_chance = min(
                25,
                self.player.crit_chance(self.world.items, stat_name=attack_stat) + int(effect.get("crit_bonus", 0)),
            )
            critical = damage > 0 and roll["die"] >= self._crit_threshold_for_chance(crit_chance)
            if critical:
                damage = self.player.critical_damage(damage)

        return {
            "enemy_name": enemy_name,
            "enemy_defense": enemy_defense,
            "roll": roll,
            "hit": hit,
            "damage": damage,
            "critical": critical,
        }

    def _resolve_random_encounter(self, location_id: str) -> list[str]:
        location = self.world.get_location(location_id)
        location_name = location.get("name", location_id)

        if self.world.get_enemies_at(location_id):
            return []

        encounter_entries = self.world.encounter_entries(location_id)
        encounter_entries.extend(self.factions.encounter_modifiers(self.player, location_id))
        encounter_entries = self.world.filter_encounter_entries(encounter_entries)
        encounter = self.encounters.roll_from_table(encounter_entries)
        if not encounter:
            return []

        encounter_type = str(encounter.get("type", "")).strip().lower()
        target = str(encounter.get("target", "")).strip().lower()
        if not target:
            return []

        if encounter_type == "enemy":
            if not self.world.has_enemy(target):
                return []
            if target in self.world.get_enemies_at(location_id):
                return []
            self.world.add_enemy(location_id, target)
            encounter_name = self.world.enemy_name(target)
            self._log_event(
                "encounter_triggered",
                encounter_id=target,
                encounter_name=encounter_name,
                location_id=location_id,
                location_name=location_name,
            )
            return [Narrator.encounter_text(location_name, [encounter_name])]

        if encounter_type == "npc":
            if not self.world.has_npc(target):
                return []
            if target in self.world.get_npcs_at(location_id):
                return []
            self.world.add_npc(location_id, target)
            encounter_name = self.world.npc_name(target)
            self._log_event(
                "encounter_triggered",
                encounter_id=target,
                encounter_name=encounter_name,
                location_id=location_id,
                location_name=location_name,
            )
            return [Narrator.encounter_npc_text(location_name, encounter_name)]

        return []

    def _trigger_dynamic_world_state(self, location_id: str, trigger: str, source: str) -> list[str]:
        location = self.world.get_location(location_id)
        chance = self.world.state_event_chance(location_id)
        if chance <= 0:
            return []
        if len(self.world.get_location_state_ids(location_id)) >= 2:
            return []
        if self.dice.roll_percent() > chance:
            return []

        event = self.encounters.roll_from_table(location.get("state_events", []))
        if not event:
            return []

        state_id = str(event.get("state_id", event.get("event_id", ""))).strip().lower()
        activated = self.world.activate_location_state(location_id, state_id)
        if not activated:
            return []

        location_name = location.get("name", location_id)
        state_name = activated.get("name", state_id)
        summary = activated.get("summary", "The area changes.")
        self._log_event(
            "world_state_started",
            state_id=state_id,
            event_name=state_name,
            location_id=location_id,
            location_name=location_name,
            trigger=trigger,
            source=source,
            outcome=summary,
        )
        return [Narrator.world_event_text(state_name, location_name, summary)]

    def _trigger_regional_event(self, location_id: str, trigger: str, source: str) -> list[str]:
        chance = self.world.regional_activation_chance(location_id)
        if chance <= 0:
            return []
        if self.dice.roll_percent() > chance:
            return []

        candidates = self.world.regional_event_candidates(location_id)
        if not candidates:
            return []
        event = self.encounters.roll_from_table(candidates)
        if not event:
            return []

        event_id = str(event.get("event_id", "")).strip().lower()
        activated = self.world.activate_regional_event(event_id, location_id)
        if not activated:
            return []

        location_name = activated.get("location_name", self.world.get_location(location_id).get("name", location_id))
        event_name = str(activated.get("name", event_id)).strip() or event_id
        summary = str(activated.get("summary", "Regional pressure rises.")).strip()
        self._log_event(
            "regional_event_started",
            event_id=event_id,
            event_name=event_name,
            region_id=str(activated.get("region_id", "")).strip().lower(),
            region_name=str(activated.get("region_name", "")).strip(),
            stage=int(activated.get("stage", 1) or 1),
            location_id=str(activated.get("location_id", location_id)).strip().lower(),
            location_name=location_name,
            trigger=trigger,
            source=source,
            outcome=summary,
        )
        return [Narrator.world_event_text(event_name, location_name, summary)]

    def _regional_resolution_social_effects(self, resolved_event: dict, source: str) -> list[str]:
        if not isinstance(resolved_event, dict):
            return []
        faction_effects = resolved_event.get("faction_effects", {})
        if not isinstance(faction_effects, dict) or not faction_effects:
            return []
        normalized_effects = {}
        for faction_id, delta in faction_effects.items():
            normalized_id = str(faction_id).strip().lower()
            if not normalized_id:
                continue
            normalized_effects[normalized_id] = int(delta)
        if not normalized_effects:
            return []
        return self._apply_social_rewards(reputation_changes=normalized_effects, source=source)

    def _advance_regional_events(self, source: str) -> list[str]:
        transitions = self.world.advance_regional_events(turns=1)
        lines = []
        for transition in transitions:
            if not isinstance(transition, dict):
                continue
            transition_type = str(transition.get("transition", "")).strip().lower()
            event_id = str(transition.get("event_id", "")).strip().lower()
            event_name = str(transition.get("name", event_id)).strip() or event_id
            location_id = str(transition.get("location_id", self.current_location)).strip().lower()
            location_name = str(transition.get("location_name", self.world.get_location(location_id).get("name", location_id))).strip()
            region_id = str(transition.get("region_id", "")).strip().lower()
            region_name = str(transition.get("region_name", "")).strip()
            stage = int(transition.get("stage", 1) or 1)

            if transition_type == "escalated":
                outcome = str(transition.get("summary", "Regional pressure intensifies.")).strip()
                self._log_event(
                    "regional_event_escalated",
                    event_id=event_id,
                    event_name=event_name,
                    previous_event_id=str(transition.get("previous_event_id", "")).strip().lower(),
                    region_id=region_id,
                    region_name=region_name,
                    stage=stage,
                    source=source,
                    location_id=location_id,
                    location_name=location_name,
                    outcome=outcome,
                )
                lines.append(Narrator.world_event_text(event_name, location_name, outcome))
                continue

            if transition_type == "resolved":
                reason = str(transition.get("resolution_reason", "")).strip()
                outcome = str(transition.get("resolved_summary", "Regional pressure settles.")).strip()
                self._log_event(
                    "regional_event_resolved",
                    event_id=event_id,
                    event_name=event_name,
                    region_id=region_id,
                    region_name=region_name,
                    stage=stage,
                    source=source,
                    location_id=location_id,
                    location_name=location_name,
                    resolution_reason=reason,
                    outcome=outcome,
                )
                lines.append(Narrator.world_event_text(event_name, location_name, outcome))
                lines.extend(self._regional_resolution_social_effects(transition, source=reason or source))
        return lines

    def _resolve_regional_events_after_combat(self, location_id: str, enemy_id: str) -> list[str]:
        resolved = self.world.resolve_regional_event_by_enemy(enemy_id, location_id=location_id)
        lines = []
        for entry in resolved:
            if not isinstance(entry, dict):
                continue
            event_id = str(entry.get("event_id", "")).strip().lower()
            event_name = str(entry.get("name", event_id)).strip() or event_id
            event_location_id = str(entry.get("location_id", location_id)).strip().lower()
            event_location_name = str(entry.get("location_name", self.world.get_location(event_location_id).get("name", event_location_id))).strip()
            reason = str(entry.get("resolution_reason", f"defeated_{enemy_id}")).strip()
            outcome = str(entry.get("resolved_summary", "Regional pressure settles after the victory.")).strip()
            self._log_event(
                "regional_event_resolved",
                event_id=event_id,
                event_name=event_name,
                region_id=str(entry.get("region_id", "")).strip().lower(),
                region_name=str(entry.get("region_name", "")).strip(),
                stage=int(entry.get("stage", 1) or 1),
                source="combat",
                location_id=event_location_id,
                location_name=event_location_name,
                resolution_reason=reason,
                outcome=outcome,
            )
            lines.append(Narrator.world_event_text(event_name, event_location_name, outcome))
            lines.extend(self._regional_resolution_social_effects(entry, source=reason))
        return lines

    def _clear_location_state(self, location_id: str, state_id: str, reason: str) -> list[str]:
        cleared = self.world.clear_location_state(location_id, state_id)
        if not cleared:
            return []

        location_name = self.world.get_location(location_id).get("name", location_id)
        state_name = cleared.get("name", state_id)
        outcome = cleared.get("resolved_summary", "The situation settles.")
        self._log_event(
            "world_state_cleared",
            state_id=state_id,
            event_name=state_name,
            location_id=location_id,
            location_name=location_name,
            source=reason,
            outcome=outcome,
        )
        lines = [Narrator.world_event_text(state_name, location_name, outcome)]
        lines.extend(self._state_resolution_social_effects(str(state_id).strip().lower(), reason))
        return lines

    def _state_resolution_social_effects(self, state_id: str, source: str) -> list[str]:
        if state_id == "bandit_raid":
            return self._apply_social_rewards(
                reputation_changes={
                    "kingdom_guard": 10,
                    "merchant_guild": 6,
                    "thieves_circle": -10,
                },
                source=source,
            )
        if state_id == "merchant_caravan":
            return self._apply_social_rewards(
                reputation_changes={"merchant_guild": 6},
                trust_changes={"merchant": 4},
                source=source,
            )
        if state_id == "shrine_corruption":
            return self._apply_social_rewards(
                reputation_changes={
                    "shrine_keepers": 12,
                    "cult_of_ash": -12,
                },
                trust_changes={"caretaker": 6, "scholar": 4},
                source=source,
            )
        if state_id == "wolf_infestation":
            return self._apply_social_rewards(
                reputation_changes={"forest_clans": 8},
                trust_changes={"elder": 3, "hermit": 4},
                source=source,
            )
        if state_id == "traveler_in_need":
            return self._apply_social_rewards(
                reputation_changes={"forest_clans": 6},
                trust_changes={"traveler": 10},
                source=source,
            )
        return []

    def _resolve_world_states_after_combat(self, location_id: str, enemy_id: str) -> list[str]:
        lines = []
        for state in self.world.get_location_states(location_id):
            clear_on_victory = {str(target).strip().lower() for target in state.get("clear_on_victory", [])}
            if enemy_id in clear_on_victory:
                lines.extend(self._clear_location_state(location_id, state.get("state_id", ""), reason=f"defeated_{enemy_id}"))
        return lines

    def _resolve_traveler_state(self, location_id: str) -> list[str]:
        if not self.world.has_location_state(location_id, "traveler_in_need"):
            return []
        if "bandage" not in self.player.inventory:
            return ["The Traveler needs a bandage before they can safely continue."]

        self.player.inventory.remove("bandage")
        self.player.gold += 4
        traveler_data = self.world.get_npc("traveler")
        self.player.record_npc_help("traveler", faction_id=traveler_data.get("faction", ""))
        lines = [
            "You give the Traveler a bandage.",
            "The Traveler steadies, thanks you, and presses 4 gold into your hand.",
        ]
        lines.extend(self._clear_location_state(location_id, "traveler_in_need", reason="helped_traveler"))
        return lines

    def _post_action_world_tick(self, source: str) -> list[str]:
        lines = []
        lines.extend(self._trigger_regional_event(self.current_location, trigger="action", source=source))
        lines.extend(self._trigger_dynamic_world_state(self.current_location, trigger="action", source=source))
        lines.extend(self._advance_regional_events(source=f"action:{source}"))
        return lines

    def _recent_world_events(self) -> list[dict]:
        world_event_types = {
            "world_state_started",
            "world_state_cleared",
            "world_event_resolved",
            "regional_event_started",
            "regional_event_escalated",
            "regional_event_resolved",
        }
        return [event for event in self.player.event_log if event.get("type") in world_event_types][-8:]

    def _apply_quest_social_effects(self, quest_id: str) -> list[str]:
        quest_data = self.quests.quests.get(quest_id, {})
        giver = str(quest_data.get("giver", "")).strip().lower()
        trust_reward = int(quest_data.get("trust_reward", 0))
        lines = self._apply_social_rewards(
            reputation_changes=quest_data.get("faction_rewards", {}),
            trust_changes={giver: trust_reward} if giver and trust_reward else {},
            source=quest_id,
        )
        if giver:
            giver_data = self.world.get_npc(giver)
            self.player.record_npc_quest_completed(giver, quest_id, faction_id=giver_data.get("faction", ""))
            self.player.record_npc_help(giver, faction_id=giver_data.get("faction", ""))
        return lines

    def _apply_contract_social_effects(self, contract_id: str) -> list[str]:
        contract_data = self.contracts.contracts.get(contract_id, {})
        lines = self._apply_social_rewards(
            reputation_changes=contract_data.get("faction_rewards", {}),
            trust_changes=contract_data.get("trust_rewards", {}),
            source=contract_id,
        )
        for npc_id in contract_data.get("trust_rewards", {}):
            npc_key = str(npc_id).strip().lower()
            npc_data = self.world.get_npc(npc_key)
            self.player.record_npc_help(npc_key, faction_id=npc_data.get("faction", ""))
        return lines

    def _apply_recent_quest_completions(self, location_id: str, location_name: str) -> list[str]:
        lines = []
        for quest_id in self.quests.recently_completed_quests:
            quest_data = self.quests.quests.get(quest_id, {})
            quest_title = quest_data.get("title", quest_id)
            self._log_event(
                "quest_completed",
                quest_id=quest_id,
                quest_title=quest_title,
                location_id=location_id,
                location_name=location_name,
            )
            lines.extend(self._apply_quest_social_effects(quest_id))
            reward_items = quest_data.get("reward", {}).get("items", [])
            if isinstance(reward_items, list):
                for reward_item_id in reward_items:
                    self._record_important_item_acquired(str(reward_item_id), source="quest_reward")
        self.quests.recently_completed_quests = []
        lines.extend(self._refresh_hunter_guild_rank(source="quest progress"))
        lines.extend(self._refresh_identity_unlocks(source="quest progress"))
        lines.extend(self._refresh_titles(source="quest progress"))
        return lines

    def _apply_recent_contract_completions(self, location_id: str, location_name: str) -> list[str]:
        lines = []
        for contract_id in self.contracts.recently_completed_contracts:
            contract_data = self.contracts.contracts.get(contract_id, {})
            contract_title = contract_data.get("title", contract_id)
            self._log_event(
                "contract_completed",
                contract_id=contract_id,
                contract_title=contract_title,
                location_id=location_id,
                location_name=location_name,
            )
        self.contracts.recently_completed_contracts = []
        lines.extend(self._refresh_hunter_guild_rank(source="contract progress"))
        lines.extend(self._refresh_identity_unlocks(source="contract progress"))
        lines.extend(self._refresh_titles(source="contract progress"))
        return lines

    def _contract_board_here(self) -> bool:
        return self.current_location == self.CONTRACT_BOARD_LOCATION

    def _resolve_random_world_event(self, location_id: str) -> list[str]:
        location = self.world.get_location(location_id)
        location_name = location.get("name", location_id)
        event = self.encounters.roll_world_event(location, chance_override=self.world.world_event_chance(location_id))
        if not event:
            return []

        event_name = str(event.get("name", event.get("event_id", "World Event")))
        event_type = str(event.get("type", "")).strip().lower()
        skill_name = str(event.get("skill", "survival")).strip().lower()
        dc = self.world.world_event_dc(location_id, int(event.get("dc", 10)))
        check = self._skill_check(skill_name, dc)
        roll = check["roll"]
        roll_text = f"{roll['die']} + {roll['modifier']} = {roll['total']} vs DC {dc}"
        social_lines = []

        if event_type == "ambush":
            enemy_id = str(event.get("enemy", "bandit"))
            if not self.world.has_enemy(enemy_id):
                return []
            enemy_name = self.world.enemy_name(enemy_id)
            self.world.add_enemy(location_id, enemy_id)
            if check["success"]:
                outcome = f"You beat the {skill_name} check ({roll_text}) and spot {enemy_name} before the attack."
            else:
                damage = max(1, int(self.world.enemies.get(enemy_id, {}).get("attack", 2)) - 1)
                self.player.hp = max(0, self.player.hp - damage)
                outcome = f"You fail the {skill_name} check ({roll_text}) and take {damage} damage before {enemy_name} closes in."
                if not self.player.is_alive():
                    self.running = False
                    outcome += " The blow drops you."

        elif event_type == "trader":
            self.world.add_npc(location_id, "merchant")
            reward_gold = int(event.get("reward_gold", 0)) if check["success"] else 0
            if reward_gold:
                self.player.gold += reward_gold
                social_lines.extend(
                    self._apply_social_rewards(
                        reputation_changes={"merchant_guild": 4},
                        trust_changes={"merchant": 2},
                        source=str(event.get("event_id", event_name)),
                    )
                )
                outcome = f"You pass a persuasion check ({roll_text}); the trader tips you {reward_gold} gold and offers to deal."
            else:
                outcome = f"A wandering trader arrives. Your persuasion check ({roll_text}) is not enough for a better offer."

        elif event_type == "traveler":
            reward_item = str(event.get("reward_item", "bandage"))
            reward_gold = int(event.get("reward_gold", 0))
            if check["success"]:
                self.inventory.add_item(self.player, reward_item)
                self.player.gold += reward_gold
                traveler_data = self.world.get_npc("traveler")
                self.player.record_npc_help("traveler", faction_id=traveler_data.get("faction", ""))
                social_lines.extend(
                    self._apply_social_rewards(
                        reputation_changes={"forest_clans": 5},
                        trust_changes={"traveler": 6},
                        source=str(event.get("event_id", event_name)),
                    )
                )
                outcome = (
                    f"You succeed on a survival check ({roll_text}) and help the traveler. "
                    f"You gain {self.world.item_name(reward_item)} and {reward_gold} gold."
                )
            else:
                outcome = f"You fail the survival check ({roll_text}) and cannot do much for the traveler."

        elif event_type == "treasure":
            reward_item = str(event.get("reward_item", "potion"))
            reward_gold = int(event.get("reward_gold", 0))
            if check["success"]:
                self.inventory.add_item(self.player, reward_item)
                self.player.gold += reward_gold
                social_lines.extend(
                    self._apply_social_rewards(
                        reputation_changes={"thieves_circle": 3},
                        source=str(event.get("event_id", event_name)),
                    )
                )
                outcome = (
                    f"You pass a {skill_name} check ({roll_text}) and crack open the cache. "
                    f"You find {self.world.item_name(reward_item)} and {reward_gold} gold."
                )
            else:
                outcome = f"You fail the {skill_name} check ({roll_text}) and leave the cache sealed."

        else:
            outcome = f"The event passes without a clear effect ({roll_text})."

        self._log_event(
            "world_event_resolved",
            event_id=str(event.get("event_id", event_name)).strip().lower(),
            event_name=event_name,
            location_id=location_id,
            location_name=location_name,
            outcome=outcome,
        )
        return [Narrator.world_event_text(event_name, location_name, outcome), *social_lines]

    def _active_quest_scene_note(self, location_id: str) -> tuple[str, str]:
        next_objective = self.quests.next_objective(self.player, campaign_context=self.arc_context())
        if not next_objective:
            return "", ""

        title = str(next_objective.get("title", "")).strip()
        objective = next_objective.get("objective", {})
        ready_to_turn_in = bool(next_objective.get("ready_to_turn_in"))
        have = int(next_objective.get("have", 0))
        need = int(next_objective.get("need", 1))
        turn_in_id = str(next_objective.get("turn_in", "village_square"))
        turn_in_name = self.world.get_location(turn_in_id).get("name", turn_in_id)

        if ready_to_turn_in:
            if location_id == turn_in_id:
                return title, "This objective can be closed out here."
            return title, f"Return to {turn_in_name} to finish it."

        objective_type = str(objective.get("type", "")).strip().lower()
        if objective_type == "defeat_enemy":
            enemy_id = str(objective.get("enemy", "enemy"))
            target_location_id = str(objective.get("location", location_id))
            target_location_name = self.world.get_location(target_location_id).get("name", target_location_id)
            enemy_name = self.world.enemy_name(enemy_id)
            if target_location_id == location_id:
                return title, f"Target here: {enemy_name} ({have}/{need})."
            return title, f"Next target: {enemy_name} at {target_location_name} ({have}/{need})."

        if objective_type == "bring_item":
            item_id = str(objective.get("item", "item"))
            item_name = self.world.item_name(item_id)
            if item_id in self.player.inventory:
                if location_id == turn_in_id:
                    return title, f"You have {item_name}; turn it in here."
                return title, f"You have {item_name}; bring it to {turn_in_name}."
            return title, f"Recover {item_name} ({have}/{need}) and return to {turn_in_name}."

        if objective_type == "visit_location":
            target_location_id = str(objective.get("location", location_id))
            target_location_name = self.world.get_location(target_location_id).get("name", target_location_id)
            if have >= need:
                if location_id == turn_in_id:
                    return title, "This exploration has been confirmed here."
                return title, f"Return to {turn_in_name} with your report."
            return title, f"Reach {target_location_name} ({have}/{need})."

        return title, f"Progress: {have}/{need}."

    def _build_scene_context(self, location_id: str | None = None, recent_events: list[dict] | None = None):
        location_id = location_id or self.current_location
        location = self.world.get_location(location_id)
        chapter_progress = self.arc_context()
        active_quest_title, active_quest_note = self._active_quest_scene_note(location_id)
        return self.dm_context.build(
            location_id=location_id,
            location_name=location.get("name", location_id),
            location_description=location.get("description", ""),
            visible_enemy_names=[self.world.enemy_name(enemy_id) for enemy_id in self.world.get_enemies_at(location_id)],
            visible_item_names=[self.world.item_name(item_id) for item_id in self.world.get_items_at(location_id)],
            visible_npc_names=self._visible_npc_names_at_location(location_id),
            exits={
                direction: self.world.get_location(target_id).get("name", target_id)
                for direction, target_id in location.get("connected_locations", {}).items()
            },
            recent_events=recent_events if recent_events is not None else self.player.event_log[-5:],
            chapter_progress=chapter_progress,
            active_quest_title=active_quest_title,
            active_quest_note=active_quest_note,
        )

    def _scene_transition_text(self, recent_events: list[dict]) -> str:
        if not recent_events:
            return ""

        event_types = {str(event.get("type", "")).strip().lower() for event in recent_events}
        impact_types = {"enemy_defeated", "enemy_fled", "miniboss_defeated", "quest_completed", "important_item_acquired"}
        if not event_types.intersection(impact_types):
            return ""

        context = self._build_scene_context(recent_events=self.player.event_log[-5:])
        return "\n".join(self.scene_composer.compose_transition_lines(context, event_types))

    def _find_visible_npc_at_location(self, location_id: str, query: str) -> str | None:
        npc_query = self._extract_talkable_npc(query)
        if npc_query and npc_query in self._visible_npcs_at_location(location_id):
            return npc_query

        normalized = " ".join(query.strip().lower().split())
        for npc_id in self._visible_npcs_at_location(location_id):
            display_name = self.TALKABLE_NPCS.get(npc_id, npc_id.title()).lower()
            if normalized == npc_id or normalized == display_name:
                return npc_id
        return None

    @staticmethod
    def _location_lore_objects(location_id: str) -> dict[str, tuple[str, ...]]:
        if location_id == "ruined_shrine":
            return {
                "shrine_altar": (
                    "altar",
                    "shrine altar",
                    "altar stone",
                    "altar stones",
                    "altar basin",
                    "blackened basin",
                    "offering basin",
                ),
                "cracked_sigil_stone": (
                    "sigil stone",
                    "cracked sigil stone",
                    "sigil",
                    "stone sigil",
                    "cracked stone",
                    "sigil rock",
                ),
            }
        if location_id == "old_watchtower":
            return {
                "watchtower_journal": (
                    "journal",
                    "watchtower journal",
                    "captain journal",
                    "captain's journal",
                    "captain log",
                    "captain's log",
                    "watch log",
                ),
                "memorial_plaque": (
                    "plaque",
                    "memorial plaque",
                    "plaque stone",
                    "memorial",
                    "stone memorial",
                    "watch memorial",
                ),
            }
        if location_id == "river_crossing":
            return {
                "ferry_ledger": (
                    "ledger",
                    "ferry ledger",
                    "ferry records",
                    "toll ledger",
                    "toll records",
                    "ferry log",
                )
            }
        return {}

    def _find_lore_object_at_location(self, location_id: str, query: str) -> str | None:
        normalized = " ".join(query.strip().lower().split())
        lore_objects = self._location_lore_objects(location_id)
        for lore_id, aliases in lore_objects.items():
            if normalized == lore_id:
                return lore_id
            if normalized in aliases:
                return lore_id
        return None

    def process_command(self, raw_command: str) -> str:
        """Parse a raw input line and route it to deterministic handlers."""
        raw_command = " ".join(raw_command.strip().split())
        if not raw_command:
            return ""

        free_text_output = self._maybe_process_free_text(raw_command)
        if free_text_output is not None:
            return free_text_output

        parts = raw_command.split(maxsplit=1)
        if not parts:
            return ""

        command = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if command == "look":
            return self._cmd_look()
        if command == "inspect":
            return self._cmd_inspect(arg)
        if command == "search":
            return self._cmd_search(arg)
        if command == "map":
            return self._cmd_map()
        if command == "move":
            return self._cmd_move(arg)
        if command == "fight":
            return self._cmd_fight(arg)
        if command == "take":
            return self._cmd_take(arg)
        if command == "inventory":
            return self._cmd_inventory()
        if command == "gear":
            return self._cmd_gear()
        if command in {"character", "sheet"}:
            return self._cmd_character()
        if command == "stats":
            return self._cmd_stats()
        if command == "skills":
            return self._cmd_skills()
        if command == "abilities":
            return self._cmd_abilities()
        if command == "recap":
            return self._cmd_recap()
        if command == "story":
            return self._cmd_story()
        if command == "history":
            return self._cmd_history()
        if command == "world":
            return self._cmd_world()
        if command == "events":
            return self._cmd_events()
        if command == "reputation":
            return self._cmd_reputation()
        if command == "factions":
            return self._cmd_factions()
        if command == "relations":
            return self._cmd_relations()
        if command == "hint":
            return self._cmd_hint()
        if command == "rest":
            return self._cmd_rest()
        if command == "use":
            return self._cmd_use(arg)
        if command == "cast":
            return self._cmd_cast(arg)
        if command == "ability":
            return self._cmd_abilities() if not arg else self._cmd_cast(arg)
        if command == "quests":
            return self._cmd_quests()
        if command == "quest":
            if not arg:
                return self._cmd_quests()
            return "Use 'quests' to review your log or 'accept <quest>' to take an offered quest."
        if command == "board":
            return self._cmd_board()
        if command == "contracts":
            return self._cmd_contracts()
        if command == "routes":
            return self._cmd_routes()
        if command == "travel":
            return self._cmd_travel(arg)
        if command == "activities":
            return self._cmd_activities(arg)
        if command == "journal":
            return self._cmd_journal()
        if command == "about":
            return self._cmd_about()
        if command == "talk":
            return self._cmd_talk(arg)
        if command == "ask":
            return self._cmd_ask(arg)
        if command == "accept":
            return self._cmd_accept(arg)
        if command == "claim":
            return self._cmd_claim(arg)
        if command == "do":
            return self._cmd_do(arg)
        if command == "buy":
            return self._cmd_buy(arg)
        if command == "sell":
            return self._cmd_sell(arg)
        if command == "recipes":
            return self._cmd_recipes()
        if command == "craft":
            return self._cmd_craft(arg)
        if command == "upgrade":
            return self._cmd_upgrade(arg)
        if command == "save":
            return self._cmd_save(arg)
        if command == "load":
            return self._cmd_load(arg)
        if command == "slots":
            return self._cmd_slots()
        if command == "delete":
            return self._cmd_delete(arg)
        if command == "help":
            return self._cmd_help()
        if command == "quit":
            self.running = False
            return "Goodbye."

        return (
            f"Unknown command: '{command}'. "
            "Type 'help' to see valid commands."
        )

    def _in_dungeon(self) -> bool:
        return bool(self.current_dungeon_room and self.world.has_dungeon(self.current_location))

    def _dungeon_exits(self) -> dict:
        if not self._in_dungeon():
            return {}
        return self.world.dungeon_room_exits(self.current_location, self.current_dungeon_room or "")

    def _ensure_dungeon_room_state(self) -> list[str]:
        if not self._in_dungeon():
            return []

        location_id = self.current_location
        room_id = self.current_dungeon_room or ""
        lines = []
        room_enemies = self.world.dungeon_room_enemies(location_id, room_id)
        if not room_enemies and not self.world.dungeon_encounter_seeded(location_id, room_id):
            encounter = self.encounters.roll_from_table(self.world.dungeon_room_possible_encounters(location_id, room_id))
            if encounter and str(encounter.get("type", "")).strip().lower() == "enemy":
                enemy_id = str(encounter.get("target", "")).strip().lower()
                if self.world.has_enemy(enemy_id):
                    self.world.add_enemy_to_dungeon_room(location_id, room_id, enemy_id)
                    lines.append(Narrator.encounter_text(self.current_location_name(), [self.world.enemy_name(enemy_id)]))
            self.world.mark_dungeon_encounter_seeded(location_id, room_id)

        for event in self.world.dungeon_room_events(location_id, room_id):
            event_id = str(event.get("id", "")).strip().lower()
            if not event_id:
                continue
            if bool(event.get("once", True)) and self.world.dungeon_event_resolved(location_id, room_id, event_id):
                continue
            self.world.mark_dungeon_event_resolved(location_id, room_id, event_id)
            text = str(event.get("text", "")).strip()
            if text:
                lines.append("Event: " + text)
            reward_item = str(event.get("reward_item", "")).strip().lower()
            if reward_item and self.world.has_item(reward_item):
                self.world.add_item_to_dungeon_room(location_id, room_id, reward_item)
            reward_gold = max(0, int(event.get("reward_gold", 0) or 0))
            if reward_gold:
                self.player.gold += reward_gold
                lines.append(f"Event reward: {reward_gold} gold.")
        return lines

    def _dungeon_exit_label(self, target: str) -> str:
        if target == "__exit__":
            surface_id = self.world.dungeon_surface_exit(self.current_location) or self.current_location
            return self.world.get_location(surface_id).get("name", surface_id)
        return self.world.dungeon_room_name(self.current_location, target)

    def _move_within_dungeon(self, query: str) -> str:
        exits = self._dungeon_exits()
        if not exits:
            return "No exits from here."

        normalized_query = str(query or "").strip().lower()
        if not normalized_query:
            return "Move where? Available exits: " + ", ".join(exits.keys())

        target_room = exits.get(normalized_query)
        if not target_room:
            for direction, candidate_room in exits.items():
                candidate_name = self.world.dungeon_room_name(self.current_location, candidate_room).lower()
                if normalized_query == candidate_room or normalized_query == candidate_name:
                    target_room = candidate_room
                    normalized_query = direction
                    break
        if not target_room:
            return "You cannot go there from here. Available exits: " + ", ".join(exits.keys())

        if target_room == "__exit__":
            surface_id = self.world.dungeon_surface_exit(self.current_location)
            if not surface_id:
                return "This route is blocked."
            return self._transition_to_location(
                surface_id,
                [f"You climb out from {self.world.get_location(self.current_location).get('name', self.current_location)}."],
                source="dungeon_exit",
                allow_random_events=False,
            )

        self.current_dungeon_room = target_room
        lines = [f"You move {normalized_query} to {self.world.dungeon_room_name(self.current_location, target_room)}."]
        lines.extend(self._ensure_dungeon_room_state())
        lines.append(self._cmd_look())
        return "\n".join(lines)

    def _cmd_look(self) -> str:
        if self._in_dungeon():
            location_id = self.current_location
            room_id = self.current_dungeon_room or ""
            location = {
                "name": self.world.dungeon_room_name(location_id, room_id),
                "description": self.world.dungeon_room_description(location_id, room_id),
            }
            enemies = self.world.dungeon_room_enemies(location_id, room_id)
            items = self.world.dungeon_room_items(location_id, room_id)
            exits = self.world.dungeon_room_exits(location_id, room_id)
            exits_display = {direction: self._dungeon_exit_label(target) for direction, target in exits.items()}
            enemy_names = {enemy_id: self.world.enemy_name(enemy_id) for enemy_id in enemies}
            item_names = {item_id: self.world.item_name(item_id) for item_id in items}
            location_context = dict(self._location_lore_context())
            location_context["location_name"] = self.world.get_location(location_id).get("name", location_id)
            location_context["services"] = []
            return Narrator.location_text(
                location_id=f"{location_id}:{room_id}",
                location=location,
                enemies=enemies,
                items=items,
                exits=exits_display,
                enemy_names=enemy_names,
                item_names=item_names,
                npc_names=[],
                scene_lines=[f"Dungeon site: {self.world.get_location(location_id).get('name', location_id)}"],
                state_lines=[],
                history_flags=self._history_flags(),
                location_context=location_context,
            )

        location = self.world.get_location(self.current_location)
        enemies = self.world.get_enemies_at(self.current_location)
        items = self.world.get_items_at(self.current_location)
        exits = location.get("connected_locations", {})
        exits_display = {
            direction: self.world.get_location(target_id).get("name", target_id)
            for direction, target_id in exits.items()
        }

        enemy_names = {
            enemy_id: self.world.enemy_name(enemy_id)
            for enemy_id in enemies
        }
        item_names = {
            item_id: self.world.item_name(item_id)
            for item_id in items
        }
        scene_context = self._build_scene_context()

        text = Narrator.location_text(
            location_id=self.current_location,
            location=location,
            enemies=enemies,
            items=items,
            exits=exits_display,
            enemy_names=enemy_names,
            item_names=item_names,
            npc_names=list(scene_context.visible_npc_names),
            scene_lines=self.scene_composer.compose_look_lines(scene_context),
            state_lines=[state.get("name", state.get("state_id", "State")) for state in self.world.get_location_states(self.current_location)],
            history_flags=self._history_flags(),
            location_context=self._location_lore_context(),
        )
        if self._contract_board_here():
            text += "\nA contract board stands beside the market lane. Use 'board' to read the current postings."
        if self._travel_service_here():
            text += "\nA Waycarter post keeps route ledgers here. Use 'routes' to review major-hub passage."
        return text

    def _inspect_with_quest_updates(self, base_text: str, target_id: str, target_type: str) -> str:
        self._log_event(
            "inspected",
            target_id=target_id,
            target_type=target_type,
            location_id=self.current_location,
        )
        quest_lines = self.quests.on_inspect(
            self.player,
            target_id,
            target_type,
            self.current_location,
            self.inventory,
            world=self.world,
            campaign_context=self.arc_context(),
        )
        if quest_lines:
            lines = [base_text]
            lines.extend(quest_lines)
            location_name = self.world.get_location(self.current_location).get("name", self.current_location)
            lines.extend(self._apply_recent_quest_completions(self.current_location, location_name))
            return "\n".join(lines)
        return base_text

    def _cmd_inspect(self, arg: str) -> str:
        if not arg.strip():
            return "Inspect what? Try your location, an item nearby, an item in your backpack, or an NPC here."

        query = self._strip_leading_article(arg.strip())
        query_lower = query.lower()

        if self._contract_board_here() and query_lower in {"board", "contract board", "job board", "hunters board"}:
            return self._cmd_board()

        if self.world.is_current_location_query(self.current_location, query):
            location = self.world.get_location(self.current_location)
            if self.current_location in {"old_watchtower", "ruined_shrine"}:
                return self._inspect_with_quest_updates(
                    Narrator.inspect_special_location_text(
                        self.current_location,
                        location,
                        self._history_flags(),
                        location_context=self._location_lore_context(),
                    ),
                    self.current_location,
                    "location",
                )
            return self._inspect_with_quest_updates(
                Narrator.inspect_location_text(
                    location,
                    self.current_location,
                    self._history_flags(),
                    location_context=self._location_lore_context(),
                ),
                self.current_location,
                "location",
            )

        lore_object_id = self._find_lore_object_at_location(self.current_location, query)
        if lore_object_id:
            return self._inspect_with_quest_updates(
                Narrator.inspect_lore_object_text(
                    lore_object_id=lore_object_id,
                    location_id=self.current_location,
                    history_flags=self._history_flags(),
                ),
                lore_object_id,
                "lore",
            )

        inventory_item_id = self.inventory.find_item_in_inventory(self.player, self.world.items, query)
        if inventory_item_id:
            return self._inspect_with_quest_updates(
                "\n".join(self.inventory.inspect_item_lines(self.player, inventory_item_id, self.world.items, "your backpack")),
                inventory_item_id,
                "item",
            )

        location_item_id = self.world.find_item_at_location(self.current_location, query)
        if location_item_id:
            return self._inspect_with_quest_updates(
                "\n".join(
                    self.inventory.inspect_item_lines(
                        self.player,
                        location_item_id,
                        self.world.items,
                        "the ground here",
                        include_upgrade_state=False,
                    )
                ),
                location_item_id,
                "item",
            )

        npc_id = self._find_visible_npc_at_location(self.current_location, query)
        if npc_id:
            npc_name = self.TALKABLE_NPCS.get(npc_id, npc_id.title())
            location_name = self.world.get_location(self.current_location).get("name", self.current_location)
            return self._inspect_with_quest_updates(
                Narrator.inspect_npc_text(npc_name, location_name),
                npc_id,
                "npc",
            )

        hints = []
        location_name = self.world.get_location(self.current_location).get("name", self.current_location)
        hints.append(f"location ({location_name})")
        hints.extend(alias for aliases in self._location_lore_objects(self.current_location).values() for alias in aliases[:1])
        hints.extend(self.world.item_name(item_id) for item_id in self.world.get_items_at(self.current_location))
        hints.extend(self.world.item_name(item_id) for item_id in self.player.inventory)
        hints.extend(self.TALKABLE_NPCS.get(npc_id, npc_id.title()) for npc_id in self._visible_npcs_at_location(self.current_location))
        if hints:
            return (
                f"You cannot inspect '{query_lower}' here.\n"
                "Try one of: " + ", ".join(hints[:6]) + "."
            )
        return f"You cannot inspect '{query_lower}' here."

    def _cmd_map(self) -> str:
        if self._in_dungeon():
            lines = [f"Dungeon Map: {self.world.get_location(self.current_location).get('name', self.current_location)}"]
            dungeon = self.world.dungeons.get(self.current_location, {})
            for room_id, room in dungeon.get("rooms", {}).items():
                marker = " [YOU]" if room_id == self.current_dungeon_room else ""
                exits = room.get("exits", {})
                if exits:
                    exit_text = ", ".join(f"{direction}->{self._dungeon_exit_label(target)}" for direction, target in exits.items())
                else:
                    exit_text = "none"
                lines.append(f"- {self.world.dungeon_room_name(self.current_location, room_id)}{marker} | exits: {exit_text}")
            return "\n".join(lines)
        return "\n".join(self.world.map_lines(self.current_location))

    def _cmd_search(self, arg: str) -> str:
        if not arg.strip():
            return "Search what? Try: area, ground, or location."

        target = self.world.normalize_search_target(arg)
        if not target:
            return "You can search only: area, ground, or location."

        if self._in_dungeon():
            location_name = self.world.dungeon_room_name(self.current_location, self.current_dungeon_room or "")
            enemy_names = [
                self.world.enemy_name(enemy_id)
                for enemy_id in self.world.dungeon_room_enemies(self.current_location, self.current_dungeon_room or "")
            ]
            item_names = [
                self.world.item_name(item_id)
                for item_id in self.world.dungeon_room_items(self.current_location, self.current_dungeon_room or "")
            ]
            npc_names = []
            exits = {
                direction: self._dungeon_exit_label(target)
                for direction, target in self.world.dungeon_room_exits(self.current_location, self.current_dungeon_room or "").items()
            }
        else:
            location = self.world.get_location(self.current_location)
            location_name = location.get("name", self.current_location)
            enemy_names = [self.world.enemy_name(enemy_id) for enemy_id in self.world.get_enemies_at(self.current_location)]
            item_names = [self.world.item_name(item_id) for item_id in self.world.get_items_at(self.current_location)]
            npc_names = [self.TALKABLE_NPCS.get(npc_id, npc_id.title()) for npc_id in self._visible_npcs_at_location(self.current_location)]
            exits = {
                direction: self.world.get_location(target_id).get("name", target_id)
                for direction, target_id in location.get("connected_locations", {}).items()
            }

        return Narrator.search_text(
            location_name=location_name,
            target=target,
            item_names=item_names,
            enemy_names=enemy_names,
            npc_names=npc_names,
            exits=exits,
            location_context=self._location_lore_context(),
        )

    def _travel_service_here(self) -> bool:
        return bool(self._travel_routes_here())

    def _travel_routes_here(self) -> list[dict]:
        routes = []
        for route_id, route in getattr(self.world, "travel_routes", {}).items():
            if not isinstance(route, dict):
                continue
            if str(route.get("origin", "")).strip().lower() != self.current_location:
                continue
            destination = str(route.get("destination", "")).strip().lower()
            if destination not in self.world.locations:
                continue
            route_entry = dict(route)
            route_entry["route_id"] = str(route_id).strip().lower()
            route_entry["origin"] = self.current_location
            route_entry["destination"] = destination
            routes.append(route_entry)
        routes.sort(key=lambda route: self._travel_destination_name(route))
        return routes

    def _travel_destination_name(self, route: dict) -> str:
        destination = str(route.get("destination", "")).strip().lower()
        location = self.world.locations.get(destination, {})
        hub_data = location.get("major_hub", {})
        if isinstance(hub_data, dict):
            hub_name = str(hub_data.get("name", "")).strip()
            if hub_name:
                return hub_name
        return str(location.get("name", destination)).strip() or destination.replace("_", " ").title()

    def _travel_mode_name(self, route: dict) -> str:
        mode = str(route.get("mode", "carriage")).strip().replace("_", " ")
        return mode.title() or "Carriage"

    def _travel_route_available(self, route: dict) -> bool:
        requirements = route.get("requirements", {})
        if not isinstance(requirements, dict) or not requirements:
            return True
        return self._unlock_conditions_met(requirements, unlocked_by_default=False)

    @staticmethod
    def _travel_route_visible(route: dict, available: bool) -> bool:
        if available:
            return True
        return bool(route.get("show_when_locked", True))

    def _travel_requirement_text(self, route: dict) -> str:
        note = str(route.get("requirement_note", "")).strip()
        return note or "Progress further through the realm before this route opens."

    def _resolve_travel_route(self, query: str) -> tuple[dict | None, str]:
        normalized_query = " ".join(str(query or "").strip().lower().split())
        if normalized_query.startswith("to "):
            normalized_query = normalized_query[3:].strip()
        if not normalized_query:
            return None, ""

        routes = [
            route
            for route in self._travel_routes_here()
            if self._travel_route_visible(route, self._travel_route_available(route))
        ]
        exact_match = None
        partial_matches = []
        for route in routes:
            destination = str(route.get("destination", "")).strip().lower()
            destination_name = self._travel_destination_name(route).lower()
            aliases = {
                destination,
                destination_name,
                destination_name.replace("-", " "),
            }
            if normalized_query in aliases:
                exact_match = route
                break
            if normalized_query and any(normalized_query in alias or alias in normalized_query for alias in aliases):
                partial_matches.append(route)

        if exact_match:
            return exact_match, ""
        if len(partial_matches) == 1:
            return partial_matches[0], ""
        if len(partial_matches) > 1:
            return None, "ambiguous"
        return None, "missing"

    def _travel_overencumbered(self) -> bool:
        carry_load = self.inventory.carry_load(self.player, self.world.items)
        return carry_load > self.player.carry_capacity()

    def _visible_travel_routes(self) -> list[dict]:
        visible = []
        for route in self._travel_routes_here():
            available = self._travel_route_available(route)
            if not self._travel_route_visible(route, available):
                continue
            route_entry = dict(route)
            route_entry["_available"] = available
            visible.append(route_entry)
        return visible

    def _resolve_road_encounter(self, route: dict) -> list[str]:
        chance = self.world.road_encounter_chance()
        if chance <= 0 or self.dice.roll_percent() > chance:
            return []

        encounter = self.encounters.roll_from_table(self.world.road_encounter_candidates(route))
        if not encounter:
            return []

        encounter_name = str(encounter.get("name", encounter.get("encounter_id", "Road Encounter"))).strip() or "Road Encounter"
        intro = str(encounter.get("intro", "")).strip()
        outcome = str(encounter.get("outcome", "")).strip()
        encounter_id = str(encounter.get("encounter_id", "")).strip().lower()
        category = str(encounter.get("category", "")).strip().lower()
        destination_id = str(route.get("destination", self.current_location)).strip().lower()
        destination_name = self.world.get_location(destination_id).get("name", destination_id)
        lines = []
        if intro:
            lines.append(intro)

        if category == "combat":
            enemy_id = str(encounter.get("enemy", "")).strip().lower()
            if not self.world.has_enemy(enemy_id):
                return []
            self.world.add_enemy(destination_id, enemy_id)
            self.world.set_active_road_encounter(
                encounter_id=encounter_id,
                name=encounter_name,
                route_id=str(route.get("route_id", "")).strip().lower(),
                location_id=destination_id,
                enemy_id=enemy_id,
            )
            enemy_name = self.world.enemy_name(enemy_id)
            if not outcome:
                outcome = f"The line reaches {destination_name}, but {enemy_name} is still in pursuit."
        else:
            reward_gold = max(0, int(encounter.get("reward_gold", 0) or 0))
            if reward_gold:
                self.player.gold += reward_gold

            reward_names = []
            reward_items = encounter.get("reward_items", [])
            if isinstance(reward_items, list):
                for item_id in reward_items:
                    normalized_item = str(item_id).strip().lower()
                    if not self.world.has_item(normalized_item):
                        continue
                    self.inventory.add_item(self.player, normalized_item)
                    reward_names.append(self.world.item_name(normalized_item))

            lines.extend(
                self._apply_social_rewards(
                    reputation_changes=encounter.get("reputation_changes", {}),
                    trust_changes=encounter.get("trust_changes", {}),
                    source=encounter_id or "road_encounter",
                )
            )

            rumor = str(encounter.get("rumor", "")).strip()
            if rumor:
                lines.append("Rumor learned: " + rumor)

            contract_hint_id = str(encounter.get("contract_hint", "")).strip().lower()
            if contract_hint_id:
                contract_title = str(
                    self.contracts.contracts.get(contract_hint_id, {}).get(
                        "title",
                        contract_hint_id.replace("_", " ").title(),
                    )
                ).strip()
                lines.append(f"Road lead: {contract_title} may be worth checking once you reach a board.")

            quest_hook = str(encounter.get("quest_hook", "")).strip()
            if quest_hook:
                lines.append("Quest hook: " + quest_hook)

            if not outcome:
                rewards = []
                if reward_gold:
                    rewards.append(f"{reward_gold} gold")
                if reward_names:
                    rewards.append(", ".join(reward_names))
                outcome = "You turn the encounter to your advantage."
                if rewards:
                    outcome += " Reward: " + "; ".join(rewards) + "."

        self._log_event(
            "road_encounter",
            encounter_id=encounter_id,
            encounter_name=encounter_name,
            category=category,
            route_id=str(route.get("route_id", "")).strip().lower(),
            origin_id=str(route.get("origin", self.current_location)).strip().lower(),
            origin_name=self.world.get_location(str(route.get("origin", self.current_location)).strip().lower()).get(
                "name",
                str(route.get("origin", self.current_location)).strip().lower(),
            ),
            location_id=destination_id,
            location_name=destination_name,
            outcome=outcome,
        )
        lines.append(Narrator.road_encounter_text(encounter_name, outcome))
        return lines

    def _transition_to_location(
        self,
        new_location: str,
        entry_lines: list[str],
        *,
        source: str,
        allow_random_events: bool,
    ) -> str:
        previous_location = self.current_location
        event_count_before = len(self.player.event_log)
        first_visit = not self.player.has_event("location_visited", "location_id", new_location)
        self.world.clear_transient_npcs(previous_location)
        self.current_dungeon_room = None
        self.current_location = new_location
        self._record_location_visit(self.current_location)
        location = self.world.get_location(self.current_location)
        location_name = location.get("name", self.current_location)
        lines = list(entry_lines)
        if self.world.has_dungeon(self.current_location):
            entry_room = self.world.dungeon_entry_room(self.current_location)
            if entry_room:
                self.current_dungeon_room = entry_room
                lines.append(f"You enter {location_name} and descend to {self.world.dungeon_room_name(self.current_location, entry_room)}.")
                lines.extend(self._ensure_dungeon_room_state())
        if first_visit:
            lines.append(f"Discovery: {location_name} is now added to your route journal.")
            lines.extend(self._grant_xp(2, source=f"exploration:{new_location}"))
        lines.extend(self._refresh_identity_unlocks(source=location_name))
        lines.extend(self._hub_arrival_lines(self.current_location))
        lines.extend(self._refresh_world_recognition(source=location_name))
        if self._town_activity_ids():
            lines.append("Town activity available: use 'activities' to rest, gather leads, or train.")
        rank_warning = self._location_rank_warning(self.current_location)
        if rank_warning:
            lines.append(rank_warning)
        if allow_random_events:
            lines.extend(self._resolve_random_encounter(self.current_location))
            lines.extend(self._resolve_random_world_event(self.current_location))
        lines.extend(self._trigger_regional_event(self.current_location, trigger="travel", source=source))
        lines.extend(self._trigger_dynamic_world_state(self.current_location, trigger="travel", source=source))
        lines.extend(self._advance_regional_events(source=f"travel:{source}"))
        lines.extend(self._resolve_location_events(self.current_location))
        if not self.player.is_alive():
            lines.append("Game over.")
            return "\n".join(lines)
        scene_context = self._build_scene_context()
        lines.extend(self.scene_composer.compose_entry_lines(scene_context))
        lines.extend(self._learn_available_recipes())
        lines.append(self._cmd_look())
        quest_messages = self.quests.on_location_enter(
            self.player,
            self.current_location,
            self.inventory,
            world=self.world,
            campaign_context=self.arc_context(),
        )
        lines.extend(quest_messages)
        lines.extend(self._apply_recent_quest_completions(self.current_location, location_name))
        transition_text = self._scene_transition_text(self.player.event_log[event_count_before:])
        if transition_text:
            lines.append(transition_text)
        return "\n".join(lines)

    def _cmd_routes(self) -> str:
        routes = self._visible_travel_routes()
        if not routes:
            return (
                "No Waycarter service is operating here. "
                "Try a major hub such as Market Square, Stormbreak, Valewood, Emberfall, Ironridge Square, or Vaultreach."
            )

        hub_name = self._travel_destination_name({"destination": self.current_location})
        lines = ["Waycarter Network", f"Origin: {hub_name}"]
        shown = 0
        for index, route in enumerate(routes, start=1):
            available = bool(route.get("_available", False))
            destination_name = self._travel_destination_name(route)
            mode_name = self._travel_mode_name(route)
            cost = max(0, int(route.get("cost", 0) or 0))
            line = f"{index}. {destination_name}: {mode_name}, {cost} gold"
            description = str(route.get("description", "")).strip()
            if description:
                line += f" | {description}"
            if not available:
                line += f" | Locked: {self._travel_requirement_text(route)}"
            lines.append(line)
            shown += 1
        if shown == 0:
            return (
                "No Waycarter service is operating here. "
                "Travel between major hubs is booked only through routes currently opened to you."
            )
        if self._travel_overencumbered():
            lines.append("You are carrying too much to book passage right now.")
        travel_warnings = self.world.regional_travel_warnings(self.current_location)
        for warning in travel_warnings:
            lines.append("Travel warning: " + warning)
        lines.append("Use 'travel <number>' or 'travel <hub>' to book a route.")
        return "\n".join(lines)

    def _cmd_travel(self, arg: str) -> str:
        if not arg.strip():
            return self._cmd_routes()

        routes = self._visible_travel_routes()
        if not routes:
            return (
                "No Waycarter service is operating here. "
                "Travel between major hubs is booked from active network posts."
            )
        if self._travel_overencumbered():
            carry_load = self.inventory.carry_load(self.player, self.world.items)
            return (
                f"You are carrying too much for paid passage ({carry_load}/{self.player.carry_capacity()}). "
                "Stow, sell, or use gear before trying to travel."
            )

        menu_index = self._menu_choice_index(arg, len(routes))
        if menu_index is not None:
            route = routes[menu_index]
            error = ""
        else:
            route, error = self._resolve_travel_route(arg)
        if error == "ambiguous":
            return "That destination matches more than one route. Use 'routes' to review the current ledger."
        if not route:
            return "No Waycarter route matches that destination from here. Use 'routes' to review available hubs."
        if not bool(route.get("_available", self._travel_route_available(route))):
            return self._travel_requirement_text(route)

        destination_name = self._travel_destination_name(route)
        cost = max(0, int(route.get("cost", 0) or 0))
        if self.player.gold < cost:
            return f"You need {cost} gold for passage to {destination_name}."

        self.player.gold -= cost
        destination = str(route.get("destination", "")).strip().lower()
        mode_name = self._travel_mode_name(route)
        description = str(route.get("description", "")).strip()
        self._log_event(
            "hub_travel",
            origin_id=self.current_location,
            origin_name=self.world.get_location(self.current_location).get("name", self.current_location),
            destination_id=destination,
            destination_name=destination_name,
            mode=mode_name,
            cost=cost,
        )
        intro_line = f"You book {mode_name.lower()} passage to {destination_name} for {cost} gold."
        if description:
            intro_line += " " + description
        road_lines = self._resolve_road_encounter(route)
        return self._transition_to_location(
            destination,
            [intro_line, *road_lines],
            source="travel_network",
            allow_random_events=False,
        )

    @staticmethod
    def _town_activity_label(activity_id: str) -> str:
        labels = {
            "tavern_rumor": "Listen for rumors",
            "hunter_gossip": "Talk to hunters",
            "drink_ale": "Drink ale",
            "market_browse": "Browse merchants",
            "market_gossip": "Hear gossip",
            "sparring": "Spar with local fighters",
        }
        return labels.get(activity_id, activity_id.replace("_", " ").title())

    def _town_activity_config(self) -> dict:
        config = getattr(self.world, "town_activities", {}).get(self.current_location, {})
        return config if isinstance(config, dict) else {}

    def _town_activity_ids(self) -> list[str]:
        config = self._town_activity_config()
        raw = config.get("activities", [])
        if not isinstance(raw, list):
            return []
        return [str(activity_id).strip().lower() for activity_id in raw if str(activity_id).strip()]

    def _town_activity_rumors(self, *, topic: str = "", limit: int = 2) -> list[str]:
        config = self._town_activity_config()
        pools = config.get("rumor_pools", [])
        if not isinstance(pools, list):
            return []

        entries = []
        for pool_id in pools:
            pool_entries = self.world.rumors.get(str(pool_id).strip().lower(), [])
            if not isinstance(pool_entries, list):
                continue
            for index, entry in enumerate(pool_entries):
                if not isinstance(entry, dict):
                    continue
                text = str(entry.get("text", "")).strip()
                if not text:
                    continue
                if topic and not self._topic_matches_entry(topic, entry):
                    continue
                entries.append((int(entry.get("priority", 0) or 0), index, text))

        entries.sort(key=lambda item: (-item[0], item[1], item[2]))
        seen = set()
        lines = []
        for _, _, text in entries:
            if text in seen:
                continue
            seen.add(text)
            lines.append(text)
            if len(lines) >= max(1, limit):
                break
        return lines

    def _resolve_town_activity(self, activity_id: str) -> str:
        if activity_id == "tavern_rumor":
            focus_cycle = ["bosses", "relics", "dungeons", "crisis"]
            focus_topic = focus_cycle[len(self.player.event_log) % len(focus_cycle)]
            rumor_lines = self._town_activity_rumors(topic=focus_topic, limit=2) or self._town_activity_rumors(limit=2)
            lines = ["You listen to the room and piece together useful leads."]
            if rumor_lines:
                lines.extend(f"- {line}" for line in rumor_lines)
            else:
                lines.append("- No useful rumors surface right now.")
            return "\n".join(lines)

        if activity_id == "hunter_gossip":
            rumor_lines = self._town_activity_rumors(topic="bosses", limit=1)
            rumor_lines.extend(self._town_activity_rumors(topic="crisis", limit=1))
            lines = ["Local hunters trade route notes, trophy stories, and threat warnings."]
            if rumor_lines:
                lines.extend(f"- {line}" for line in rumor_lines[:2])
            return "\n".join(lines)

        if activity_id == "drink_ale":
            hp_before = self.player.hp
            focus_before = self.player.focus
            self.player.hp = min(self.player.max_hp, self.player.hp + 1)
            self.player.focus = min(self.player.max_focus, self.player.focus + 1)
            recovered_hp = self.player.hp - hp_before
            recovered_focus = self.player.focus - focus_before
            return (
                f"You take a quiet drink and reset your breathing. "
                f"Recovered HP +{recovered_hp}, Focus +{recovered_focus}."
            )

        if activity_id == "market_browse":
            return self._cmd_buy("")

        if activity_id == "market_gossip":
            rumor_lines = self._town_activity_rumors(topic="dungeons", limit=1)
            rumor_lines.extend(self._town_activity_rumors(topic="relics", limit=1))
            lines = ["Merchants swap fast gossip between transactions."]
            if rumor_lines:
                lines.extend(f"- {line}" for line in rumor_lines[:2])
            else:
                lines.append("- The market talk stays on prices and weather.")
            return "\n".join(lines)

        if activity_id == "sparring":
            lines = ["You run controlled rounds in the yard and tighten your timing."]
            lines.extend(self._grant_xp(2, source="town_sparring"))
            return "\n".join(lines)

        return "That activity is not available here."

    def _cmd_activities(self, arg: str = "") -> str:
        activity_ids = self._town_activity_ids()
        if not activity_ids:
            return "No town activities are available here."

        config = self._town_activity_config()
        town_name = str(config.get("town_name", self.world.get_location(self.current_location).get("name", self.current_location))).strip()
        venue = str(config.get("venue", f"{town_name} Commons")).strip()

        options = activity_ids + ["leave"]
        if not arg.strip():
            lines = [venue]
            for index, activity_id in enumerate(activity_ids, start=1):
                lines.append(f"{index}. {self._town_activity_label(activity_id)}")
            lines.append(f"{len(options)}. Leave")
            lines.append("Use 'activities <number>' to choose.")
            return "\n".join(lines)

        query = " ".join(arg.strip().lower().split())
        menu_index = self._menu_choice_index(query, len(options))
        if menu_index is not None:
            selected = options[menu_index]
        else:
            selected = ""
            for activity_id in options:
                if query == activity_id or query == self._town_activity_label(activity_id).lower():
                    selected = activity_id
                    break
        if not selected:
            return f"Unknown activity. Use 'activities' to review options in {town_name}."
        if selected == "leave":
            return f"You step away from {venue}."
        return self._resolve_town_activity(selected)

    def _cmd_move(self, arg: str) -> str:
        if self._in_dungeon():
            return self._move_within_dungeon(arg)

        if not arg:
            exits = self.world.get_location(self.current_location).get("connected_locations", {})
            if not exits:
                return "No exits from here."
            return "Move where? Available exits: " + ", ".join(exits.keys())

        new_location = self.world.find_connected_location(self.current_location, arg)
        if not new_location:
            exits = self.world.get_location(self.current_location).get("connected_locations", {})
            if exits:
                return "You cannot go there from here. Available exits: " + ", ".join(exits.keys())
            return "You cannot go there from here."
        return self._transition_to_location(
            new_location,
            [
                Narrator.movement_text(
                    self.world.get_location(new_location).get("name", new_location),
                    self.world.get_enemies_at(new_location),
                    self.world.get_items_at(new_location),
                )
            ],
            source="move",
            allow_random_events=not self.world.has_dungeon(new_location),
        )

    def _cmd_fight(self, arg: str) -> str:
        enemy_id, error = self._find_enemy_here(arg)
        if error:
            return error

        enemy_data = self.world.enemies.get(enemy_id, {})
        enemy_name = self.world.enemy_name(enemy_id)
        player_hp_before = self.player.hp
        combat_modifiers = self.world.combat_rank_modifiers(self.current_location, enemy_id)
        enemy_hp_before = max(1, int(enemy_data.get("hp", 1)) + int(combat_modifiers.get("hp_bonus", 0)))
        event_count_before = len(self.player.event_log)
        result = self.combat.fight(
            self.player,
            enemy_id,
            self.world.enemies,
            self.world.items,
            combat_modifiers=combat_modifiers,
        )

        lines = [Narrator.combat_intro(enemy_name)]
        prepared_effect = self._prepared_effect_line()
        lines.append(
            Narrator.combat_header_text(
                enemy_name=enemy_name,
                player_hp=player_hp_before,
                player_max_hp=self.player.max_hp,
                player_focus=self.player.focus,
                player_max_focus=self.player.max_focus,
                enemy_hp=enemy_hp_before,
                enemy_max_hp=enemy_hp_before,
                enemy_summary=self._enemy_combat_summary(enemy_id),
                prepared_effect=prepared_effect,
            )
        )
        lines.append(Narrator.combat_options_text(self._combat_ability_lines(enemy_id)))
        lines.extend(result["log"])

        if result["victory"]:
            lines.extend(self._resolve_enemy_victory(enemy_id, enemy_name, result, enemy_data))
        elif result.get("enemy_fled"):
            self.world.remove_enemy(self.current_location, enemy_id)
            self._log_event(
                "enemy_fled",
                enemy_id=enemy_id,
                enemy_name=enemy_name,
                location_id=self.current_location,
                location_name=self.world.get_location(self.current_location).get("name", self.current_location),
            )
            lines.append(Narrator.enemy_fled_text(enemy_name))
        else:
            lines.append(Narrator.combat_result(False, enemy_name))
            self.running = False
            lines.append("Game over.")

        self.player.clear_combat_boosts()
        if self.running:
            lines.extend(self._post_action_world_tick("fight"))
        transition_text = self._scene_transition_text(self.player.event_log[event_count_before:])
        if transition_text:
            lines.append(transition_text)
        lines.append(
            Narrator.combat_footer_text(
                player_hp=self.player.hp,
                player_max_hp=self.player.max_hp,
                player_focus=self.player.focus,
                player_max_focus=self.player.max_focus,
                enemy_name=enemy_name,
                enemy_hp=result["enemy_hp"],
            )
        )
        return "\n".join(lines)

    def _cmd_take(self, arg: str) -> str:
        if self._in_dungeon():
            items_here = self.world.dungeon_room_items(self.current_location, self.current_dungeon_room or "")
        else:
            items_here = self.world.get_items_at(self.current_location)
        if not items_here:
            return "There are no items here."

        if arg:
            if self._in_dungeon():
                item_id = self.world.find_item_in_dungeon_room(self.current_location, self.current_dungeon_room or "", arg)
            else:
                item_id = self.world.find_item_at_location(self.current_location, arg)
            if not item_id:
                item_names = [self.world.item_name(iid) for iid in items_here]
                return "That item is not here. Items here: " + ", ".join(item_names)
        else:
            item_id = items_here[0]

        event_count_before = len(self.player.event_log)
        if self._in_dungeon():
            self.world.remove_item_from_dungeon_room(self.current_location, self.current_dungeon_room or "", item_id)
        else:
            self.world.remove_item(self.current_location, item_id)
        self.inventory.add_item(self.player, item_id)
        self._record_important_item_acquired(item_id, source="ground_pickup")

        item_name = self.world.item_name(item_id)
        lines = [Narrator.item_taken(item_name)]
        if item_id in self.world.relics:
            lines.append(f"Relic discovery logged: {item_name}.")
        lines.extend(
            self.quests.on_item_obtained(
                self.player,
                item_id,
                world=self.world,
                current_location=self.current_location,
                campaign_context=self.arc_context(),
            )
        )
        lines.extend(self._apply_contract_item_updates())
        carry_status = self.inventory.carry_status_line(self.player, self.world.items)
        if carry_status:
            lines.append(carry_status)
        lines.extend(self._post_action_world_tick("take"))
        transition_text = self._scene_transition_text(self.player.event_log[event_count_before:])
        if transition_text:
            lines.append(transition_text)
        return "\n".join(lines)

    def _cmd_inventory(self) -> str:
        carry_load = self.inventory.carry_load(self.player, self.world.items)
        lines = [
            "Inventory",
            f"HP: {self.player.hp}/{self.player.max_hp}",
            f"Focus: {self.player.focus}/{self.player.max_focus}",
            f"Defense: {self.player.defense_value(self.world.items)}",
            f"Gold: {self.player.gold}",
            f"Carry: {carry_load}/{self.player.carry_capacity()}",
        ]
        carry_status = self.inventory.carry_status_line(self.player, self.world.items)
        if carry_status:
            lines.append(carry_status)
        lines.extend(self.inventory.inventory_lines(self.player, self.world.items))
        return "\n".join(lines)

    def _cmd_gear(self) -> str:
        lines = self.inventory.gear_lines(self.player, self.world.items)
        lines.append(
            "Build impact: "
            f"Attack {self.player.attack_value(self.world.items)} | "
            f"Defense {self.player.defense_value(self.world.items)} | "
            f"Spell {self.player.spell_power(self.world.items)} | "
            f"Crit {self.player.crit_chance(self.world.items)}% | "
            f"Dodge {self.player.dodge_chance(self.world.items)}%"
        )
        lines.append("Use 'upgrade <item>' to improve a favored piece of gear.")
        return "\n".join(lines)

    def _cmd_character(self) -> str:
        context = self.character_context()
        context["level"] = self.player.level
        return Narrator.character_sheet_text(
            character_context=context,
            skills=self._skill_display_data(),
            abilities=self.abilities.available_to(self.player),
            current_hp=self.player.hp,
            current_focus=self.player.focus,
            xp=self.player.xp,
            xp_needed=self.player.xp_needed_for_next_level(),
        )

    def _cmd_stats(self) -> str:
        location_name = self.world.get_location(self.current_location).get("name", self.current_location)
        equipped_weapon = "none"
        if self.player.equipped_weapon:
            equipped_weapon = self.inventory.item_label(
                self.player.equipped_weapon,
                self.world.items,
                self.player.item_upgrade_level(self.player.equipped_weapon, self.world.items),
            )
        equipped_armor = "none"
        if getattr(self.player, "equipped_armor", None):
            equipped_armor = self.inventory.item_label(
                self.player.equipped_armor,
                self.world.items,
                self.player.item_upgrade_level(self.player.equipped_armor, self.world.items),
            )
        equipped_accessory = "none"
        if getattr(self.player, "equipped_accessory", None):
            equipped_accessory = self.inventory.item_label(
                self.player.equipped_accessory,
                self.world.items,
                self.player.item_upgrade_level(self.player.equipped_accessory, self.world.items),
            )

        active_quest_summary = "None"
        next_objective = self.quests.next_objective(self.player, campaign_context=self.arc_context())
        if next_objective:
            active_quest_summary = (
                f"{next_objective['title']} "
                f"({next_objective['have']}/{next_objective['need']})"
            )
        active_contract_summary = "None"
        next_contract = self.contracts.next_objective()
        if next_contract:
            active_contract_summary = f"{next_contract['title']} ({next_contract['objective_text']})"

        derived = self.player.derived_stats(self.world.items)
        carry_load = self.inventory.carry_load(self.player, self.world.items)
        carry_status = self.inventory.carry_status_line(self.player, self.world.items)
        prepared_effect = self._prepared_effect_line()
        title_summary = self._title_summary()
        title_line = ", ".join(title_summary["names"]) if title_summary["names"] else "none"

        return (
            "Player Stats\n"
            f"Name: {self.player.name}\n"
            f"Gender: {self.player.gender}\n"
            f"Race: {self.player.race}\n"
            f"Class: {self.player.player_class}\n"
            f"Background: {self.player.background}\n"
            f"Level: {self.player.level}\n"
            f"Hunter Guild: {self.player.hunter_guild_rank} ({self.player.hunter_guild_points} marks)\n"
            f"Titles: {title_line}\n"
            f"XP: {self.player.xp}/{self.player.xp_needed_for_next_level()}\n"
            f"Resources: HP {self.player.hp}/{self.player.max_hp} | Focus {self.player.focus}/{self.player.max_focus} | Gold {self.player.gold}\n"
            "Physical stats: "
            f"Strength {self.player.effective_stat_value('strength', self.world.items)} ({self.player.effective_stat_modifier('strength', self.world.items):+d}) | "
            f"Agility {self.player.effective_stat_value('agility', self.world.items)} ({self.player.effective_stat_modifier('agility', self.world.items):+d}) | "
            f"Vitality {self.player.effective_stat_value('vitality', self.world.items)} ({self.player.effective_stat_modifier('vitality', self.world.items):+d}) | "
            f"Endurance {self.player.effective_stat_value('endurance', self.world.items)} ({self.player.effective_stat_modifier('endurance', self.world.items):+d})\n"
            "Mental stats: "
            f"Mind {self.player.effective_stat_value('mind', self.world.items)} ({self.player.effective_stat_modifier('mind', self.world.items):+d}) | "
            f"Wisdom {self.player.effective_stat_value('wisdom', self.world.items)} ({self.player.effective_stat_modifier('wisdom', self.world.items):+d}) | "
            f"Charisma {self.player.effective_stat_value('charisma', self.world.items)} ({self.player.effective_stat_modifier('charisma', self.world.items):+d}) | "
            f"Luck {self.player.effective_stat_value('luck', self.world.items)} ({self.player.effective_stat_modifier('luck', self.world.items):+d})\n"
            "Derived: "
            f"Attack {derived['attack']} ({derived['attack_stat']}/{derived['weapon_skill']}) | "
            f"Accuracy {derived['accuracy']} | "
            f"Defense {derived['defense']} | "
            f"Dodge {derived['dodge_chance']}% | "
            f"Crit {derived['crit_chance']}% | "
            f"Resilience {derived['resilience']}\n"
            "Power: "
            f"Mana/Focus {derived['mana']} | "
            f"Spell {derived['spell_power']} | "
            f"Healing {derived['healing_power']} | "
            f"Magic Guard {derived['magic_guard']} | "
            f"Carry {carry_load}/{derived['carry_capacity']}\n"
            f"Location: {location_name}\n"
            f"Equipped weapon: {equipped_weapon}\n"
            f"Equipped armor: {equipped_armor}\n"
            f"Equipped accessory: {equipped_accessory}\n"
            + (carry_status + "\n" if carry_status else "")
            + f"Inventory pieces: {len(self.player.inventory)}\n"
            f"Abilities known: {', '.join(self._ability_name(ability_id) for ability_id in self.player.abilities) or 'none'}\n"
            f"Active quest: {active_quest_summary}\n"
            f"Active contract: {active_contract_summary}"
            + (f"\nPrepared effect: {prepared_effect}" if prepared_effect else "")
            + (f"\nBio: {self.player.bio}" if self.player.bio else "")
        )

    def _cmd_skills(self) -> str:
        return Narrator.skills_text(self._skill_display_data())

    def _cmd_abilities(self) -> str:
        text = Narrator.abilities_text(
            self.abilities.available_to(self.player),
            self.player.focus,
            self.player.max_focus,
        )
        enemies_here = self.world.get_enemies_at(self.current_location)
        if enemies_here:
            text += "\n" + Narrator.combat_options_text(self._combat_ability_lines(enemies_here[0]))
        prepared_effect = self._prepared_effect_line()
        if prepared_effect:
            text += "\nPrepared effect: " + prepared_effect
        return text

    def _cmd_recap(self) -> str:
        location_name = self.world.get_location(self.current_location).get("name", self.current_location)
        equipped_weapon = "none"
        if self.player.equipped_weapon:
            equipped_weapon = self.inventory.item_label(
                self.player.equipped_weapon,
                self.world.items,
                self.player.item_upgrade_level(self.player.equipped_weapon, self.world.items),
            )

        campaign_context = self.arc_context()
        quest_summary = self.quests.recap_summary(self.player, campaign_context=campaign_context)
        event_counts = self._event_counts()
        guild_summary = self._hunter_guild_progress_summary()
        title_summary = self._title_summary()
        recap_text = Narrator.recap_text(
            player_name=self.player.name,
            location_name=location_name,
            hp=self.player.hp,
            max_hp=self.player.max_hp,
            gold=self.player.gold,
            equipped_weapon=equipped_weapon,
            active_quests=quest_summary["active"],
            completed_quests=quest_summary["completed"],
            demo_complete=quest_summary["demo_complete"],
            event_counts=event_counts,
            recent_events=self.player.event_log[-3:],
            event_memory=self._event_memory(),
            chapter_progress=campaign_context,
            character_context=self._character_lore_context(),
            location_context=self._location_lore_context(),
            history_flags=self._history_flags(),
            world_reaction_lines=self._world_recognition_lines(),
            hunter_guild_summary=guild_summary,
            title_summary=title_summary,
        )
        contract_lines = self.contracts.active_contract_lines()[1:]
        if self.contracts.accepted or self.contracts.claimable:
            recap_text += "\n" + "\n".join(["Contracts"] + contract_lines)
        return recap_text

    def _cmd_story(self) -> str:
        location_name = self.world.get_location(self.current_location).get("name", self.current_location)
        campaign_context = self.arc_context()
        quest_summary = self.quests.story_summary(self.player, campaign_context=campaign_context)
        event_counts = self._event_counts()
        guild_summary = self._hunter_guild_progress_summary()
        title_summary = self._title_summary()

        shrine_guardian_status = None
        ruined_shrine = self.world.locations.get("ruined_shrine")
        if isinstance(ruined_shrine, dict):
            shrine_enemies = ruined_shrine.get("enemies", [])
            if "shrine_guardian" in shrine_enemies:
                if "shrine_guardian" in self.world.get_enemies_at("ruined_shrine"):
                    shrine_guardian_status = "undefeated"
                else:
                    shrine_guardian_status = "defeated"

        return Narrator.story_text(
            player_name=self.player.name,
            location_name=location_name,
            completed_quests=quest_summary["completed"],
            active_quests=quest_summary["active"],
            important_progress=quest_summary["important_progress"],
            shrine_guardian_status=shrine_guardian_status,
            event_counts=event_counts,
            recent_events=self.player.event_log[-5:],
            event_memory=self._event_memory(),
            chapter_progress=campaign_context,
            character_context=self._character_lore_context(),
            location_context=self._location_lore_context(),
            history_flags=self._history_flags(),
            world_reaction_lines=self._world_recognition_lines(),
            hunter_guild_summary=guild_summary,
            title_summary=title_summary,
        )

    def _event_counts(self) -> dict:
        return dict(self._event_memory().get("counts", {}))

    def _campaign_arc(self) -> dict:
        """Compute the current campaign arc from deterministic progress signals."""
        return self.campaign.current_arc(self.player, self.quests)

    def _chapter_progress(self) -> dict:
        """Backward-compatible alias for the current campaign arc context."""
        return self._campaign_arc()

    def arc_context(self) -> dict:
        return self._campaign_arc()

    def chapter_context(self) -> dict:
        return self.arc_context()

    def history_context(self) -> dict:
        return self._history_flags()

    def current_location_name(self) -> str:
        if self._in_dungeon():
            room_name = self.world.dungeon_room_name(self.current_location, self.current_dungeon_room or "")
            return f"{self.world.get_location(self.current_location).get('name', self.current_location)} - {room_name}"
        return self.world.get_location(self.current_location).get("name", self.current_location)

    def _character_lore_context(self) -> dict:
        race_details = Character.creation_option_details("race", self.player.race)
        class_details = Character.creation_option_details("class", self.player.player_class)
        background_details = Character.creation_option_details("background", self.player.background)
        return {
            "name": self.player.name,
            "race": self.player.race,
            "class": self.player.player_class,
            "background": self.player.background,
            "race_lore": Character.creation_lore("race", self.player.race),
            "class_lore": Character.creation_lore("class", self.player.player_class),
            "background_lore": Character.creation_lore("background", self.player.background),
            "race_homeland": race_details.get("homeland", ""),
            "class_summary": class_details.get("summary", ""),
            "background_summary": background_details.get("summary", ""),
        }

    def _location_lore_context(self) -> dict:
        location = self.world.get_location(self.current_location)
        states = self.world.get_location_states(self.current_location)
        location_memory = self.player.location_event_memory(self.current_location)
        dungeon = self.world.dungeon_profile(self.current_location) or {}
        hub_data = location.get("major_hub", {}) if isinstance(location.get("major_hub", {}), dict) else {}
        return {
            "location_name": location.get("name", self.current_location),
            "region": location.get("region", ""),
            "location_lore": location.get("lore", ""),
            "state_names": [state.get("name", state.get("state_id", "State")) for state in states],
            "dungeon_tier": dungeon.get("tier", ""),
            "dungeon_label": dungeon.get("label", ""),
            "dungeon_danger": dungeon.get("danger", ""),
            "dungeon_level_range": dungeon.get("level_range", []),
            "dungeon_families": dungeon.get("family_names", []),
            "dungeon_loot_band": dungeon.get("loot_band", ""),
            "dungeon_event_risk": dungeon.get("event_risk", ""),
            "npcs": self._visible_npc_names_at_location(self.current_location),
            "services": [str(service) for service in location.get("services", []) if str(service).strip()],
            "economy_note": str(location.get("economy_note", "")).strip(),
            "hub_name": str(hub_data.get("name", "")).strip(),
            "hub_progression_role": str(hub_data.get("progression_role", "")).strip(),
            "hub_faction_tie": str(hub_data.get("faction_tie", "")).strip(),
            "hub_race_tie": str(hub_data.get("race_tie", "")).strip(),
            "hub_class_tie": str(hub_data.get("class_tie", "")).strip(),
            "hub_travel_identity": str(hub_data.get("travel_identity", "")).strip(),
            "hub_campaign_role": str(hub_data.get("campaign_role", "")).strip(),
            "visit_count": location_memory.get("visit_count", 0),
            "defeated_enemies_here": [entry.get("name", "") for entry in location_memory.get("defeated_enemies", [])],
            "minibosses_here": [entry.get("name", "") for entry in location_memory.get("minibosses_defeated", [])],
            "world_states_started_here": [entry.get("name", "") for entry in location_memory.get("world_states_started", [])],
            "world_states_cleared_here": [entry.get("name", "") for entry in location_memory.get("world_states_cleared", [])],
            "recent_memory_events": [Narrator.event_line(event) for event in location_memory.get("recent_events", [])],
        }

    def _event_memory(self) -> dict:
        return self.player.event_memory()

    def _npc_memory_lines(self, npc_id: str) -> list[str]:
        location_name = self.world.get_location(self.current_location).get("name", self.current_location)
        location_memory = self.player.location_event_memory(self.current_location)
        lines = []

        visit_count = int(location_memory.get("visit_count", 0))
        if visit_count > 1:
            lines.append(f"Shared memory: you have returned to {location_name} {visit_count} times.")

        defeated_here = [entry.get("name", "Unknown threat") for entry in location_memory.get("defeated_enemies", [])]
        if defeated_here:
            lines.append("Local memory: your victories here include " + ", ".join(defeated_here[:2]) + ".")

        active_states = [state.get("name", state.get("state_id", "State")) for state in self.world.get_location_states(self.current_location)]
        if active_states:
            lines.append("Current pressure: " + ", ".join(active_states) + ".")

        npc_memory = self.player.ensure_npc_memory(npc_id, faction_id=self.world.get_npc(npc_id).get("faction", ""))
        quests_completed = npc_memory.get("quests_completed", [])
        if quests_completed:
            lines.append(f"They remember {len(quests_completed)} completed quest{'s' if len(quests_completed) != 1 else ''} tied to you.")

        return lines

    def _npc_memory_context(self, npc_id: str) -> dict:
        npc_data = self.world.get_npc(npc_id)
        memory = self.player.ensure_npc_memory(npc_id, faction_id=npc_data.get("faction", ""))
        return {
            "npc_name": self.world.npc_name(npc_id),
            "faction_name": self.factions.faction_name(memory.get("faction", "")) if memory.get("faction", "") else "Unaffiliated",
            "trust": int(memory.get("trust", 0)),
            "trust_tier": self.factions.tier_name(int(memory.get("trust", 0))),
            "quests_completed": len(memory.get("quests_completed", [])),
            "helped": int(memory.get("helped", 0)),
            "harmed": int(memory.get("harmed", 0)),
        }

    def _hub_arrival_lines(self, location_id: str) -> list[str]:
        location = self.world.get_location(location_id)
        hub_data = location.get("major_hub", {})
        if not isinstance(hub_data, dict) or not hub_data:
            return []

        location_memory = self.player.location_event_memory(location_id)
        if int(location_memory.get("visit_count", 0)) != 1:
            return []

        hub_name = str(hub_data.get("name", location.get("name", location_id))).strip() or location.get("name", location_id)
        lines = [f"Arrival: {hub_name} keeps its held line through ward, ledger, and people who still mean to preserve the realm."]

        region = str(location.get("region", "")).strip().lower()
        race_details = Character.creation_option_details("race", self.player.race)
        homeland = str(race_details.get("homeland", "")).strip().lower()
        if homeland and (region in homeland or hub_name.lower() in homeland):
            lines.append(f"Identity note: your {self.player.race.lower()} homeland ties make this place feel less like a rumor and more like a remembered ward-line.")

        class_name = str(self.player.player_class).strip()
        class_tie = str(hub_data.get("class_tie", "")).strip().lower()
        if class_name and class_name.lower() in class_tie:
            lines.append(f"Class note: {hub_name} reads your {class_name.lower()} training as work meant for this part of Valerion's line.")

        background = str(self.player.background).strip().lower()
        faction_tie = str(hub_data.get("faction_tie", "")).strip().lower()
        if "shrine" in background and "shrine" in faction_tie:
            lines.append("Background note: shrine voices here measure you by steadiness before they measure you by power.")
        elif "hunter" in background and any(word in region for word in ["forest", "coast", "vale"]):
            lines.append("Background note: the local roadcraft feels familiar, the kind of frontier work learned by watching what survives.")

        return lines

    def _world_recognition_lines(self, limit: int = 4) -> list[str]:
        lines = []
        rank = self.contracts.highest_unlocked_rank()
        if self.world.rank_value(rank) >= self.world.rank_value("D"):
            lines.append(f"Stonewatch's ledgers now mark you as {rank}-rank, and frontier service answers your name differently.")
        if Character.hunter_guild_rank_value(self.player.hunter_guild_rank) >= Character.hunter_guild_rank_value("Bronze"):
            lines.append(f"The Hunter Guild now posts you as {self.player.hunter_guild_rank}-rank field talent, and other hunters have started paying attention.")
        if self.player.has_event("miniboss_defeated", "enemy_id", "gorgos_the_sundered"):
            lines.append("Ironridge knows you as the one who slew Gorgos the Sundered and kept the pass from breaking.")
        if self.player.has_event("enemy_defeated", "enemy_id", "cinder_guardian"):
            lines.append("Emberfall's ward-keepers speak of the Cinder Guardian's fall as proof the ash line can still be held.")
        if self.player.has_event("quest_completed", "quest_id", "q005_sigil_for_the_caretaker"):
            lines.append("Shrine Keepers treat you as someone trusted to return old ward-duty instead of plundering it.")
        if self.player.reputation_value("merchant_guild") >= 20:
            lines.append("Merchant clerks along the held roads know your name well enough to offer straighter terms and quicker rumor.")
        if self.player.reputation_value("shrine_keepers") >= 20:
            lines.append("Shrine Keepers speak to you like someone who has chosen to keep faith with Valerion's warded duty.")
        return lines[:max(0, limit)]

    def _refresh_world_recognition(self, source: str) -> list[str]:
        recognitions = [
            {
                "key": "rank_d_known",
                "text": "Stonewatch's board clerks now know your rank and post your name among proven frontier hands.",
                "conditions": {"requires_rank": "D"},
            },
            {
                "key": "hunter_bronze_known",
                "text": "Hunter Guild clerks now mark you as Bronze standing, and rival hunters have started measuring themselves against your work.",
                "conditions": {"requires_hunter_guild_rank": "Bronze"},
            },
            {
                "key": "stormbreak_known",
                "text": "Stormbreak's harbor talk now counts you among the people who have stood on the coastward line of Valerion.",
                "conditions": {"requires_events": [{"type": "location_visited", "details": {"location_id": "stormbreak"}}]},
            },
            {
                "key": "gorgos_known",
                "text": "Word carries through Ironridge that you slew Gorgos the Sundered and held the mountain road intact.",
                "conditions": {"requires_events": [{"type": "miniboss_defeated", "details": {"enemy_id": "gorgos_the_sundered"}}]},
            },
            {
                "key": "caretaker_known",
                "text": "Shrine folk now speak of you as one trusted to carry an old sigil back into rightful keeping.",
                "conditions": {"requires_quests": ["q005_sigil_for_the_caretaker"]},
            },
        ]

        lines = []
        for recognition in recognitions:
            key = str(recognition.get("key", "")).strip().lower()
            if not key or self.player.has_event("world_recognition", "key", key):
                continue
            if not self._unlock_conditions_met(recognition.get("conditions", {}), unlocked_by_default=False):
                continue
            text = str(recognition.get("text", "")).strip()
            self._log_event(
                "world_recognition",
                key=key,
                text=text,
                source=source,
                location_id=self.current_location,
                location_name=self.current_location_name(),
            )
            lines.append("World note: " + text)
        return lines

    def character_context(self) -> dict:
        summary = self.player.character_summary()
        summary.update(self.player.derived_stats(self.world.items))
        summary["attack"] = self.player.attack_value(self.world.items)
        summary["stats"] = {
            stat_name: self.player.effective_stat_value(stat_name, self.world.items)
            for stat_name in self.player.DEFAULT_STATS
        }
        summary["skills"] = {
            skill_name: self.player.skill_value(skill_name, self.world.items)
            for skill_name in self.player.DEFAULT_SKILLS
        }
        summary["skill_proficiencies"] = {
            skill_name: self.player.skill_proficiency(skill_name, self.world.items)
            for skill_name in self.player.DEFAULT_SKILLS
        }
        summary["inventory"] = [self.world.item_name(item_id) for item_id in self.player.inventory]
        summary["abilities"] = [self._ability_name(ability_id) for ability_id in self.player.abilities]
        summary["equipped_weapon"] = (
            self.inventory.item_label(
                self.player.equipped_weapon,
                self.world.items,
                self.player.item_upgrade_level(self.player.equipped_weapon, self.world.items),
            )
            if self.player.equipped_weapon
            else ""
        )
        summary["equipped_armor"] = (
            self.inventory.item_label(
                self.player.equipped_armor,
                self.world.items,
                self.player.item_upgrade_level(self.player.equipped_armor, self.world.items),
            )
            if self.player.equipped_armor
            else ""
        )
        summary["equipped_accessory"] = (
            self.inventory.item_label(
                self.player.equipped_accessory,
                self.world.items,
                self.player.item_upgrade_level(self.player.equipped_accessory, self.world.items),
            )
            if self.player.equipped_accessory
            else ""
        )
        summary["race_lore"] = Character.creation_lore("race", self.player.race)
        summary["class_lore"] = Character.creation_lore("class", self.player.player_class)
        summary["background_lore"] = Character.creation_lore("background", self.player.background)
        return summary

    def _find_enemy_here(self, arg: str) -> tuple[str | None, str | None]:
        if self._in_dungeon():
            enemies_here = self.world.dungeon_room_enemies(self.current_location, self.current_dungeon_room or "")
        else:
            enemies_here = self.world.get_enemies_at(self.current_location)
        if not enemies_here:
            return None, "There are no enemies here."

        if arg:
            if self._in_dungeon():
                enemy_id = self.world.find_enemy_in_dungeon_room(self.current_location, self.current_dungeon_room or "", arg)
            else:
                enemy_id = self.world.find_enemy_at_location(self.current_location, arg)
            if not enemy_id:
                enemy_names = [self.world.enemy_name(eid) for eid in enemies_here]
                return None, "That enemy is not here. Enemies here: " + ", ".join(enemy_names)
            return enemy_id, None

        return enemies_here[0], None

    def _resolve_enemy_victory(self, enemy_id: str, enemy_name: str, result: dict, enemy_data: dict) -> list[str]:
        lines = [Narrator.combat_result(True, enemy_name)]
        if self._in_dungeon():
            self.world.remove_enemy_from_dungeon_room(self.current_location, self.current_dungeon_room or "", enemy_id)
        else:
            self.world.remove_enemy(self.current_location, enemy_id)
        cleared_road_encounter = self.world.clear_active_road_encounter(self.current_location, enemy_id)
        loot_ids = [str(item_id).strip().lower() for item_id in result.get("loot", []) if str(item_id).strip()]
        self._log_event(
            "enemy_defeated",
            enemy_id=enemy_id,
            enemy_name=enemy_name,
            location_id=self.current_location,
            location_name=self.world.get_location(self.current_location).get("name", self.current_location),
        )
        if self._enemy_is_boss(enemy_id, enemy_data, self.current_location):
            self._log_event(
                "miniboss_defeated",
                enemy_id=enemy_id,
                enemy_name=enemy_name,
                location_id=self.current_location,
                location_name=self.world.get_location(self.current_location).get("name", self.current_location),
            )
            relic_drop = self._roll_boss_relic_drop(enemy_id, enemy_name)
            if relic_drop:
                loot_ids.append(relic_drop)
                relic_data = self.world.relic_entry(relic_drop)
                lines.append(
                    Narrator.relic_drop_text(
                        self.world.item_name(relic_drop),
                        str(relic_data.get("lore", "")).strip(),
                        boss_name=enemy_name,
                    )
                )
        lines.extend(self._refresh_hunter_guild_rank(source=enemy_name))
        if cleared_road_encounter:
            encounter_name = str(cleared_road_encounter.get("name", "Road encounter")).strip()
            lines.append(f"Road cleared: {encounter_name} no longer threatens the route into {self.current_location_name()}.")

        for item_id in loot_ids:
            self.inventory.add_item(self.player, item_id)
            self._record_important_item_acquired(item_id, source="combat_loot")
        loot_names = [self.world.item_name(item_id) for item_id in loot_ids]
        lines.append(Narrator.loot_text(loot_names))
        relic_loot = [item_id for item_id in loot_ids if item_id in self.world.relics]
        for relic_id in relic_loot:
            lines.append(f"Relic discovery logged: {self.world.item_name(relic_id)}.")
        if loot_ids:
            carry_status = self.inventory.carry_status_line(self.player, self.world.items)
            if carry_status:
                lines.append(carry_status)

        reward_text = enemy_data.get("reward_text")
        if reward_text:
            lines.append(str(reward_text))

        reward_bonus = self.world.rank_reward_bonus(self.current_location, enemy_id)
        reward_gold = int(reward_bonus.get("gold", 0))
        if reward_gold > 0:
            self.player.gold += reward_gold
            lines.append(f"Rank payout: {reward_gold} gold.")

        for item_id in loot_ids:
            lines.extend(
                self.quests.on_item_obtained(
                    self.player,
                    item_id,
                    world=self.world,
                    current_location=self.current_location,
                    campaign_context=self.arc_context(),
                )
            )
        lines.extend(self._apply_contract_item_updates())

        lines.extend(self._grant_xp(result.get("xp_reward", 0), source=enemy_id))

        enemy_faction = str(enemy_data.get("faction", "")).strip().lower()
        if enemy_faction == "thieves_circle":
            lines.extend(
                self._apply_social_rewards(
                    reputation_changes={"kingdom_guard": 3, "thieves_circle": -5},
                    source=enemy_id,
                )
            )
        elif enemy_faction == "cult_of_ash":
            lines.extend(
                self._apply_social_rewards(
                    reputation_changes={"shrine_keepers": 4, "cult_of_ash": -6},
                    source=enemy_id,
                )
            )
        elif enemy_id == "wolf" or str(enemy_data.get("family", "")).strip().lower() == "wolves":
            lines.extend(
                self._apply_social_rewards(
                    reputation_changes={"forest_clans": 2},
                    source=enemy_id,
                )
            )

        lines.extend(self._resolve_world_states_after_combat(self.current_location, enemy_id))
        lines.extend(self._resolve_regional_events_after_combat(self.current_location, enemy_id))
        lines.extend(
            self.quests.on_enemy_defeated(
                self.player,
                enemy_id,
                self.current_location,
                self.inventory,
                world=self.world,
                campaign_context=self.arc_context(),
            )
        )
        lines.extend(self.contracts.on_enemy_defeated(self.player, enemy_id, self.current_location, self.world))
        lines.extend(
            self._apply_recent_quest_completions(
                self.current_location,
                self.world.get_location(self.current_location).get("name", self.current_location),
            )
        )
        lines.extend(
            self._apply_recent_contract_completions(
                self.current_location,
                self.world.get_location(self.current_location).get("name", self.current_location),
            )
        )
        lines.extend(self._refresh_identity_unlocks(source=enemy_name))
        lines.extend(self._refresh_titles(source=enemy_name))
        lines.extend(self._refresh_world_recognition(source=enemy_name))
        return lines

    def _cmd_history(self) -> str:
        return Narrator.history_text(
            self.player.event_log,
            event_memory=self._event_memory(),
            world_reaction_lines=self._world_recognition_lines(),
            hunter_guild_summary=self._hunter_guild_progress_summary(),
            title_summary=self._title_summary(),
        )

    def _cmd_world(self) -> str:
        return Narrator.world_text(self.world.world_state_lines(self.current_location))

    def _cmd_events(self) -> str:
        return Narrator.events_text(self.world.active_world_states(), self._recent_world_events(), self.current_location)

    def _cmd_reputation(self) -> str:
        return "\n".join(self.factions.reputation_lines(self.player))

    def _cmd_factions(self) -> str:
        return "\n".join(self.factions.faction_lines(self.player))

    def _cmd_relations(self) -> str:
        return Narrator.relations_text(self.factions.relations_lines(self.player, self.world.npcs))

    def _cmd_hint(self) -> str:
        location = self.world.get_location(self.current_location)
        location_name = location.get("name", self.current_location)
        exits = location.get("connected_locations", {})
        npcs_here = self._visible_npcs_at_location(self.current_location)
        enemies_here = self.world.get_enemies_at(self.current_location)
        offered_here = self.quests.available_quests(
            self.player,
            npcs_here,
            world=self.world,
            current_location=self.current_location,
            campaign_context=self.arc_context(),
        )

        next_objective = self.quests.next_objective(self.player, campaign_context=self.arc_context())
        if next_objective:
            title = next_objective["title"]
            objective = next_objective["objective"]
            ready_to_turn_in = next_objective["ready_to_turn_in"]
            turn_in = str(next_objective["turn_in"])
            turn_in_name = self.world.get_location(turn_in).get("name", turn_in)

            if ready_to_turn_in:
                if self.current_location == turn_in:
                    return Narrator.hint_text(
                        f"Your objective for '{title}' is complete. Stay here and continue exploring."
                    )
                direction = self.world.exit_direction_to(self.current_location, turn_in)
                if direction:
                    return Narrator.hint_text(
                        f"'{title}' is ready to turn in. Go {direction} to reach {turn_in_name}."
                    )
                return Narrator.hint_text(
                    f"'{title}' is ready to turn in. Head back to {turn_in_name}."
                )

            objective_type = objective.get("type")
            if objective_type == "defeat_enemy":
                target_location = str(objective.get("location", ""))
                target_enemy = str(objective.get("enemy", ""))
                target_enemy_name = self.world.enemy_name(target_enemy)
                target_location_name = self.world.get_location(target_location).get("name", target_location)
                if self.current_location == target_location:
                    if target_enemy in self.world.get_enemies_at(self.current_location):
                        return Narrator.hint_text(
                            f"For '{title}', fight {target_enemy_name} here using 'fight {target_enemy}'."
                        )
                    return Narrator.hint_text(
                        f"For '{title}', this area is clear. Try another nearby path."
                    )
                direction = self.world.exit_direction_to(self.current_location, target_location)
                if direction:
                    return Narrator.hint_text(
                        f"For '{title}', go {direction} toward {target_location_name}."
                    )
                return Narrator.hint_text(
                    f"For '{title}', travel to {target_location_name} and look for {target_enemy_name}."
                )

            if objective_type == "bring_item":
                target_item = str(objective.get("item", ""))
                target_item_name = self.world.item_name(target_item)
                if target_item in self.player.inventory:
                    if self.current_location == turn_in:
                        return Narrator.hint_text(
                            f"You have {target_item_name}. Stay in {turn_in_name} to complete '{title}'."
                        )
                    direction = self.world.exit_direction_to(self.current_location, turn_in)
                    if direction:
                        return Narrator.hint_text(
                            f"You have {target_item_name}. Go {direction} toward {turn_in_name} for '{title}'."
                        )
                    return Narrator.hint_text(
                        f"You have {target_item_name}. Return to {turn_in_name} for '{title}'."
                    )
                if target_item == "wolf_pelt":
                    direction = self.world.exit_direction_to(self.current_location, "deep_forest")
                    if self.current_location == "deep_forest":
                        return Narrator.hint_text(
                            "For this quest, defeat the Wild Wolf here to get a Wolf Pelt."
                        )
                    if direction:
                        return Narrator.hint_text(
                            f"For '{title}', go {direction} toward Deep Forest to find a Wolf Pelt."
                        )
                return Narrator.hint_text(f"For '{title}', keep searching for {target_item_name}.")

            if objective_type == "visit_location":
                target_location = str(objective.get("location", ""))
                target_location_name = self.world.get_location(target_location).get("name", target_location)
                if self.current_location == target_location:
                    return Narrator.hint_text(f"For '{title}', this place is the objective. Return to {turn_in_name} when ready.")
                direction = self.world.exit_direction_to(self.current_location, target_location)
                if direction:
                    return Narrator.hint_text(f"For '{title}', go {direction} toward {target_location_name}.")
                return Narrator.hint_text(f"For '{title}', travel to {target_location_name}.")

        contract_objective = self.contracts.next_objective()
        if contract_objective:
            title = contract_objective["title"]
            board_location = contract_objective["board_location"] or self.CONTRACT_BOARD_LOCATION
            board_name = self.world.get_location(board_location).get("name", board_location)
            if contract_objective["claimable"]:
                if self.current_location == board_location:
                    return Narrator.hint_text(f"'{title}' is ready to claim. Use 'claim {title}'.")
                direction = self.world.exit_direction_to(self.current_location, board_location)
                if direction:
                    return Narrator.hint_text(f"'{title}' is ready to claim. Go {direction} toward {board_name}.")
                return Narrator.hint_text(f"'{title}' is ready to claim. Return to {board_name}.")
            return Narrator.hint_text(
                f"Contract focus: {title}. {contract_objective['objective_text']}. Route: {contract_objective['location_hint']}."
            )

        if offered_here:
            first_title = offered_here[0][1].get("title", offered_here[0][0])
            if len(offered_here) == 1:
                return Narrator.hint_text(f"{first_title} is available here. Try 'accept {first_title}'.")
            return Narrator.hint_text("There are quests available here. Try 'quests' or 'accept <quest>'.")

        if "shrine_guardian" in enemies_here:
            return Narrator.hint_text(
                "The Shrine Guardian blocks your path. Use 'fight shrine guardian' when you are ready."
            )

        if self.current_location == "deep_forest":
            shrine_has_guardian = "shrine_guardian" in self.world.get_enemies_at("ruined_shrine")
            if shrine_has_guardian:
                direction = self.world.exit_direction_to(self.current_location, "ruined_shrine")
                if direction:
                    return Narrator.hint_text(
                        f"Ruined Shrine is nearby. Go {direction} to face the Shrine Guardian."
                    )

        if self.current_location == "forest_path":
            watchtower_has_enemy = bool(self.world.get_enemies_at("old_watchtower"))
            if watchtower_has_enemy:
                direction = self.world.exit_direction_to(self.current_location, "old_watchtower")
                if direction:
                    return Narrator.hint_text(
                        f"Old Watchtower still has danger. Go {direction} to investigate."
                    )

        if "merchant" in npcs_here:
            potion_cost = self.factions.price_for_service(
                self.player,
                "merchant_guild",
                "merchant",
                self.inventory.SHOP_PRICES["potion"],
            )
            return Narrator.hint_text(
                f"The Merchant is here. You can buy a Potion for {potion_cost} gold with 'buy potion'."
            )
        if "elder" in npcs_here:
            return Narrator.hint_text("The Elder is here. Try 'ask elder about the forest'.")
        if exits:
            first_direction = next(iter(exits.keys()))
            target_id = exits[first_direction]
            target_name = self.world.get_location(target_id).get("name", target_id)
            return Narrator.hint_text(
                f"Explore from {location_name}: try 'move {first_direction}' toward {target_name}."
            )
        return Narrator.hint_text("Nothing urgent right now; feel free to explore or check 'recap'.")

    def _cmd_about(self) -> str:
        return Narrator.about_text()

    def _cmd_rest(self) -> str:
        location = self.world.get_location(self.current_location)
        location_name = location.get("name", self.current_location)

        if self.current_location not in self.SAFE_REST_LOCATIONS:
            return Narrator.rest_not_safe_text(location_name)

        lines = []
        rest_cost = int(location.get("rest_cost", 0))
        if rest_cost > 0:
            rest_faction = str(location.get("rest_faction", "")).strip().lower()
            rest_npc = str(location.get("rest_npc", "")).strip().lower() or None
            if rest_faction:
                allowed, denial = self.factions.service_access(self.player, rest_faction, rest_npc)
                if not allowed:
                    return denial
                rest_cost = self.factions.price_for_service(self.player, rest_faction, rest_npc, rest_cost)
            if self.player.gold < rest_cost:
                return f"You need {rest_cost} gold to rest at {location_name}, but you only have {self.player.gold} gold."
            self.player.gold -= rest_cost
            lines.append(f"Room cost: {rest_cost} gold. Gold left: {self.player.gold}.")

        was_injured = self.player.hp < self.player.max_hp or self.player.focus < self.player.max_focus
        self.player.hp = self.player.max_hp
        self.player.focus = self.player.max_focus
        lines.append(
            Narrator.rest_text(
                location_name,
                self.player.hp,
                self.player.max_hp,
                self.player.focus,
                self.player.max_focus,
                was_injured,
            )
        )
        if self.world.get_location(self.current_location).get("region", "") == "Stonewatch":
            self.contracts.advance_board_refresh()
        lines.extend(self._post_action_world_tick("rest"))
        return "\n".join(lines)

    def _cmd_use(self, arg: str) -> str:
        if not arg:
            lines = self.inventory.inventory_lines(self.player, self.world.items)
            return "Use what? Choose an item from your backpack.\n" + "\n".join(lines)

        item_id = self.inventory.find_item_in_inventory(self.player, self.world.items, arg)
        if not item_id:
            lines = self.inventory.inventory_lines(self.player, self.world.items)
            return f"You do not have '{arg}'.\n" + "\n".join(lines)

        result = self.inventory.use_item(self.player, item_id, self.world.items)
        extra_lines = self._post_action_world_tick("use")
        if extra_lines:
            return result + "\n" + "\n".join(extra_lines)
        return result

    def _cmd_cast(self, arg: str) -> str:
        available = self.abilities.available_to(self.player)
        if not arg:
            lines = ["Cast what?", Narrator.abilities_text(available, self.player.focus, self.player.max_focus)]
            enemies_here = self.world.get_enemies_at(self.current_location)
            if enemies_here:
                lines.append(Narrator.combat_options_text(self._combat_ability_lines(enemies_here[0])))
            return "\n".join(lines)

        ability, target_text = self.abilities.parse_player_input(self.player, arg)
        if not ability:
            lines = ["You do not know that ability.", Narrator.abilities_text(available, self.player.focus, self.player.max_focus)]
            enemies_here = self.world.get_enemies_at(self.current_location)
            if enemies_here:
                lines.append(Narrator.combat_options_text(self._combat_ability_lines(enemies_here[0])))
            return "\n".join(lines)

        cost = int(ability.get("cost", 0))
        if self.player.focus < cost:
            return f"Not enough focus for {ability['name']}. Focus: {self.player.focus}/{self.player.max_focus}."

        event_count_before = len(self.player.event_log)
        effect = ability.get("effect", {})
        lines = []

        if ability.get("target") == "self":
            self.player.spend_focus(cost)
            healed = 0
            heal_amount = int(effect.get("heal", 0))
            if heal_amount > 0:
                healed = self.player.heal(heal_amount + self._ability_scale_bonus(effect))
            buff_summary = self._apply_ability_buff(ability, effect.get("buff", {}))

            if healed > 0:
                lines.append(
                    Narrator.ability_text(
                        ability["name"],
                        f"You recover {healed} HP. HP {self.player.hp}/{self.player.max_hp}. Focus {self.player.focus}/{self.player.max_focus}.",
                    )
                )
            elif buff_summary:
                lines.append(
                    Narrator.ability_text(
                        ability["name"],
                        f"You prepare for the next fight: {buff_summary}. Focus {self.player.focus}/{self.player.max_focus}.",
                    )
                )
            else:
                lines.append(
                    Narrator.ability_text(
                        ability["name"],
                        f"You steady yourself, but your HP is already full. Focus {self.player.focus}/{self.player.max_focus}.",
                    )
                )
            lines.extend(self._post_action_world_tick("cast"))
            transition_text = self._scene_transition_text(self.player.event_log[event_count_before:])
            if transition_text:
                lines.append(transition_text)
            return "\n".join(lines)

        enemy_id, error = self._find_enemy_here(target_text)
        if error:
            return error

        enemy_data = self.world.enemies.get(enemy_id, {})
        enemy_name = self.world.enemy_name(enemy_id)
        enemy_hp_before = int(enemy_data.get("hp", 1))
        self.player.spend_focus(cost)
        buff_summary = self._apply_ability_buff(ability, effect.get("buff", {}))
        opening_result = None
        opening_damage = 0

        if int(effect.get("damage", 0)) > 0:
            opening_result = self._resolve_opening_ability_attack(ability, enemy_id, enemy_data)
            if opening_result["hit"]:
                opening_damage = opening_result["damage"]
                crit_text = " Critical hit." if opening_result["critical"] else ""
                lines.append(
                    Narrator.ability_text(
                        ability["name"],
                        f"You roll {opening_result['roll']['die']} + {opening_result['roll']['modifier']} = {opening_result['roll']['total']} "
                        f"against {enemy_name} DEF {opening_result['enemy_defense']} and hit for {opening_damage} opening damage.{crit_text} "
                        f"Focus {self.player.focus}/{self.player.max_focus}.",
                    )
                )
            else:
                lines.append(
                    Narrator.ability_text(
                        ability["name"],
                        f"You roll {opening_result['roll']['die']} + {opening_result['roll']['modifier']} = {opening_result['roll']['total']} "
                        f"against {enemy_name} DEF {opening_result['enemy_defense']} and miss. Focus {self.player.focus}/{self.player.max_focus}.",
                    )
                )
        elif buff_summary:
            lines.append(
                Narrator.ability_text(
                    ability["name"],
                    f"You prepare against {enemy_name}: {buff_summary}. Focus {self.player.focus}/{self.player.max_focus}.",
                )
            )

        if effect.get("reveal_enemy"):
            profile = self.combat.preview_enemy(enemy_id, enemy_data)
            family = str(profile.get("family", "unknown")).replace("_", " ")
            class_type = str(profile.get("class_type", "foe")).replace("_", " ")
            level = int(profile.get("level", 1))
            abilities = [str(ability.get("name", "")).strip() for ability in profile.get("abilities", [])]
            ability_text = ", ".join(abilities) if abilities else "none"
            lines.append(
                Narrator.ability_text(
                    ability["name"],
                    f"{enemy_name} reads as {family}, {class_type}, level {level}. "
                    f"HP {enemy_hp_before}, DEF {int(enemy_data.get('defense', 10))}, ATK {int(enemy_data.get('attack', 1))}. "
                    f"Abilities: {ability_text}.",
                )
            )

        enemy_hp_after = max(0, enemy_hp_before - opening_damage)

        if enemy_hp_after <= 0:
            result = {
                "victory": True,
                "loot": enemy_data.get("loot", []),
                "xp_reward": int(enemy_data.get("xp", max(5, enemy_hp_before * 5))),
                "enemy_hp": 0,
            }
            lines.extend(self._resolve_enemy_victory(enemy_id, enemy_name, result, enemy_data))
        else:
            player_hp_before = self.player.hp
            result = self.combat.fight(
                self.player,
                enemy_id,
                self.world.enemies,
                self.world.items,
                starting_enemy_hp=enemy_hp_after,
            )
            prepared_effect = self._prepared_effect_line()
            lines.append(
                Narrator.combat_header_text(
                    enemy_name=enemy_name,
                    player_hp=player_hp_before,
                    player_max_hp=self.player.max_hp,
                    player_focus=self.player.focus,
                    player_max_focus=self.player.max_focus,
                    enemy_hp=enemy_hp_after,
                    enemy_max_hp=enemy_hp_before,
                    enemy_summary=self._enemy_combat_summary(enemy_id),
                    prepared_effect=prepared_effect,
                )
            )
            lines.append(Narrator.combat_options_text(self._combat_ability_lines(enemy_id)))
            lines.extend(result["log"])
            if result["victory"]:
                lines.extend(self._resolve_enemy_victory(enemy_id, enemy_name, result, enemy_data))
            elif result.get("enemy_fled"):
                self.world.remove_enemy(self.current_location, enemy_id)
                self._log_event(
                    "enemy_fled",
                    enemy_id=enemy_id,
                    enemy_name=enemy_name,
                    location_id=self.current_location,
                    location_name=self.world.get_location(self.current_location).get("name", self.current_location),
                )
                lines.append(Narrator.enemy_fled_text(enemy_name))
            else:
                lines.append(Narrator.combat_result(False, enemy_name))
                self.running = False
                lines.append("Game over.")

        self.player.clear_combat_boosts()
        if self.running:
            lines.extend(self._post_action_world_tick("cast"))
        transition_text = self._scene_transition_text(self.player.event_log[event_count_before:])
        if transition_text:
            lines.append(transition_text)
        lines.append(
            Narrator.combat_footer_text(
                player_hp=self.player.hp,
                player_max_hp=self.player.max_hp,
                player_focus=self.player.focus,
                player_max_focus=self.player.max_focus,
                enemy_name=enemy_name,
                enemy_hp=result["enemy_hp"],
            )
        )
        return "\n".join(lines)

    def _cmd_quests(self) -> str:
        return "Quest Log\n" + "\n".join(
            self.quests.list_quests(
                self.player,
                self._visible_npcs_at_location(self.current_location),
                world=self.world,
                current_location=self.current_location,
                campaign_context=self.arc_context(),
            )
        )

    def _board_available_contracts(self) -> list[tuple[str, dict]]:
        return self.contracts.available_contracts(self.player, self.CONTRACT_BOARD_LOCATION)

    def _board_claimable_contracts(self) -> list[tuple[str, dict]]:
        claimable = []
        for contract_id in sorted(self.contracts.claimable):
            contract = self.contracts.contracts.get(contract_id, {})
            if str(contract.get("board_location", "")).strip().lower() != self.CONTRACT_BOARD_LOCATION:
                continue
            claimable.append((contract_id, contract))
        return claimable

    def _cmd_board(self) -> str:
        if not self._contract_board_here():
            return "Stonewatch's contract board is posted in Market Square."
        self.contracts.sync_active_targets(self.player, self.world)
        location_name = self.world.get_location(self.current_location).get("name", self.current_location)
        lines = self._apply_recent_contract_completions(self.current_location, location_name)
        guild_summary = self._hunter_guild_progress_summary()
        lines.append(
            f"Hunter Guild standing: {guild_summary['rank']} ({guild_summary['points']} marks)"
            + (
                f" | {guild_summary['needed']} marks to {self._hunter_guild_rank_from_points(guild_summary['next_threshold'])[0]}"
                if guild_summary.get("next_threshold") is not None
                else " | Top field standing reached"
            )
        )
        lines.extend(self.contracts.board_lines(self.player, self.CONTRACT_BOARD_LOCATION))
        available = self._board_available_contracts()
        focused_contract_ids = self.world.regional_contract_focus(self.CONTRACT_BOARD_LOCATION)
        if focused_contract_ids:
            focus_titles = []
            for contract_id in focused_contract_ids:
                contract_data = self.contracts.contracts.get(contract_id, {})
                title = str(contract_data.get("title", contract_id)).strip()
                if title and title not in focus_titles:
                    focus_titles.append(title)
            if focus_titles:
                lines.append("Crisis Priority: " + ", ".join(focus_titles))
        if available:
            lines.append("Accept Menu")
            for index, (contract_id, contract) in enumerate(available, start=1):
                title = str(contract.get("title", contract_id)).strip()
                rank = str(contract.get("rank", "?")).strip().upper()
                lines.append(f"{index}. [{rank}-Rank] {title}")
        claimable = self._board_claimable_contracts()
        if claimable:
            lines.append("Claim Menu")
            for index, (contract_id, contract) in enumerate(claimable, start=1):
                title = str(contract.get("title", contract_id)).strip()
                rank = str(contract.get("rank", "?")).strip().upper()
                lines.append(f"{index}. [{rank}-Rank] {title}")
        if available or claimable:
            lines.append("Use 'accept <number|name>' or 'claim <number|name>'.")
        return "\n".join(lines)

    def _cmd_contracts(self) -> str:
        self.contracts.sync_active_targets(self.player, self.world)
        location_name = self.world.get_location(self.current_location).get("name", self.current_location)
        lines = self._apply_recent_contract_completions(self.current_location, location_name)
        lines.extend(self.contracts.active_contract_lines())
        return "\n".join(lines)

    def _cmd_journal(self) -> str:
        return "\n".join(
            self.quests.journal_lines(
                self.player,
                npc_ids=self._visible_npcs_at_location(self.current_location),
                world=self.world,
                current_location=self.current_location,
                campaign_context=self.arc_context(),
            )
        )

    def _cmd_claim(self, arg: str) -> str:
        if not self._contract_board_here():
            return "You need to be at the Stonewatch contract board in Market Square to claim payment."
        query = arg.strip()
        claimable_contracts = self._board_claimable_contracts()
        if not query and claimable_contracts:
            lines = ["Claim Menu"]
            for index, (contract_id, contract) in enumerate(claimable_contracts, start=1):
                title = str(contract.get("title", contract_id)).strip()
                rank = str(contract.get("rank", "?")).strip().upper()
                lines.append(f"{index}. [{rank}-Rank] {title}")
            lines.append("Use 'claim <number|name>'.")
            return "\n".join(lines)
        menu_index = self._menu_choice_index(query, len(claimable_contracts))
        if menu_index is not None:
            query = str(claimable_contracts[menu_index][0])
        claimed, lines, contract_id, reward_items = self.contracts.claim_contract(self.player, query, self.inventory)
        if not claimed or not contract_id:
            return "\n".join(lines)
        contract_data = self.contracts.contracts.get(contract_id, {})
        self._log_event(
            "contract_claimed",
            contract_id=contract_id,
            contract_title=contract_data.get("title", contract_id),
            location_id=self.current_location,
            location_name=self.world.get_location(self.current_location).get("name", self.current_location),
        )
        lines.extend(self._apply_contract_social_effects(contract_id))
        for reward_item_id in reward_items:
            self._record_important_item_acquired(str(reward_item_id), source="contract_reward")
        resolved_regional = self.world.resolve_regional_event_by_contract(contract_id)
        for resolved in resolved_regional:
            if not isinstance(resolved, dict):
                continue
            event_id = str(resolved.get("event_id", "")).strip().lower()
            event_name = str(resolved.get("name", event_id)).strip() or event_id
            event_location_id = str(resolved.get("location_id", self.current_location)).strip().lower()
            event_location_name = str(resolved.get("location_name", self.world.get_location(event_location_id).get("name", event_location_id))).strip()
            resolution_reason = str(resolved.get("resolution_reason", f"claimed_{contract_id}")).strip()
            outcome = str(resolved.get("resolved_summary", "Regional pressure settles after contract success.")).strip()
            self._log_event(
                "regional_event_resolved",
                event_id=event_id,
                event_name=event_name,
                region_id=str(resolved.get("region_id", "")).strip().lower(),
                region_name=str(resolved.get("region_name", "")).strip(),
                stage=int(resolved.get("stage", 1) or 1),
                source="contract_claim",
                location_id=event_location_id,
                location_name=event_location_name,
                resolution_reason=resolution_reason,
                outcome=outcome,
            )
            lines.append(Narrator.world_event_text(event_name, event_location_name, outcome))
            lines.extend(self._regional_resolution_social_effects(resolved, source=resolution_reason))
        lines.extend(self._refresh_hunter_guild_rank(source="contract claim"))
        lines.extend(self._refresh_identity_unlocks(source="Hunters Guild progression"))
        lines.extend(self._refresh_titles(source="Hunters Guild progression"))
        lines.extend(self._refresh_world_recognition(source="Hunters Guild progression"))
        return "\n".join(lines)

    def _npc_service_lines(self, npc_id: str, npc_data: dict) -> list[str]:
        services = []
        stock = npc_data.get("shop_inventory", [])
        faction_id = str(npc_data.get("faction", "")).strip().lower()
        if faction_id:
            services.append(
                f"standing {self.factions.faction_name(faction_id)} {self.factions.standing_text(self.player, faction_id)}"
            )
            services.append(self.factions.service_terms_text(self.player, faction_id, npc_id))
        if isinstance(stock, list) and stock:
            services.append("buy, sell")
        if npc_id in self.UPGRADE_SERVICE_NPCS:
            services.append("upgrade")
        craft_station = self.CRAFTING_SERVICE_NPCS.get(npc_id, "")
        if craft_station and craft_station in self._current_crafting_stations():
            services.append(f"craft ({craft_station})")

        location = self.world.get_location(self.current_location)
        rest_npc = str(location.get("rest_npc", "")).strip().lower()
        rest_cost = int(location.get("rest_cost", 0))
        if npc_id == rest_npc:
            if rest_cost > 0:
                price = self.factions.price_for_service(
                    self.player,
                    str(location.get("rest_faction", "")).strip().lower(),
                    npc_id,
                    rest_cost,
                )
                services.append(f"rest ({price} gold)")
            else:
                services.append("rest")

        if not services:
            return []
        return ["Services: " + ", ".join(services) + "."]

    def _cmd_talk(self, arg: str) -> str:
        location = self.world.get_location(self.current_location)
        npcs_here = self._visible_npcs_at_location(self.current_location)
        display_npcs_here = [self.TALKABLE_NPCS.get(npc_id, npc_id.title()) for npc_id in npcs_here]

        if not arg:
            if display_npcs_here:
                return "Talk to whom? NPCs here: " + ", ".join(display_npcs_here)
            return "Talk to whom? There is no one here to talk to."

        npc_query = self._extract_talkable_npc(arg) or self._strip_leading_article(arg.strip()).lower()
        if npc_query not in self.TALKABLE_NPCS:
            return "Unknown NPC. You can talk to: " + ", ".join(self.TALKABLE_NPCS.values()) + "."

        if npc_query not in npcs_here:
            if display_npcs_here:
                return f"{self.TALKABLE_NPCS[npc_query]} is not here. NPCs here: " + ", ".join(display_npcs_here)
            return f"{self.TALKABLE_NPCS[npc_query]} is not here. There is no one here to talk to."

        if npc_query == "traveler":
            lines = self._resolve_traveler_state(self.current_location)
            if self.world.has_location_state(self.current_location, "traveler_in_need"):
                lines.append("The Traveler winces and asks for a bandage.")
            else:
                lines.append("The Traveler gives a tired nod and continues on down the road.")
            lines.extend(self._post_action_world_tick("talk"))
            return "\n".join(lines)

        npc_data = self.world.get_npc(npc_query)
        npc_name = self.world.npc_name(npc_query)
        role = npc_data.get("role", "Wanderer")
        dialogue_set = npc_data.get("dialogue_set", {})
        if isinstance(dialogue_set, dict) and str(dialogue_set.get("default", "")).strip():
            dialogue = str(dialogue_set.get("default", "")).strip()
        else:
            dialogue = npc_data.get("dialogue", f"{npc_name} has little to say right now.")
        dialogue_note = self.world.npc_dialogue_note(self.current_location, npc_query)
        if dialogue_note:
            dialogue = f"{dialogue} {dialogue_note}"
        social_note = self.factions.dialogue_note(self.player, npc_query, npc_data)
        if social_note:
            dialogue = f"{dialogue} {social_note}"
        offers = self.quests.quest_offer_lines(
            self.player,
            npc_query,
            world=self.world,
            current_location=self.current_location,
            campaign_context=self.arc_context(),
        )
        service_lines = self._npc_service_lines(npc_query, npc_data)
        memory_lines = self._npc_memory_lines(npc_query)
        reaction_entries = self._npc_authored_entries(npc_query, "reactions", limit=2)
        reaction_lines = [entry["text"] for entry in reaction_entries]
        if reaction_entries:
            dialogue = reaction_entries[0]["text"]
            location = self.world.get_location(self.current_location)
            reaction_spread = Narrator.npc_reaction_spread_text(
                location.get("name", self.current_location),
                str(location.get("region", "")).strip(),
            )
            if reaction_spread:
                memory_lines = [reaction_spread] + memory_lines
        rumor_lines = self._npc_authored_lines(npc_query, "rumors", limit=1)
        self._mark_rival_hunter_seen(npc_query)
        dialogue_text = Narrator.npc_dialogue_text(
            npc_name,
            role,
            dialogue,
            offers,
            service_lines=service_lines,
            memory_lines=memory_lines,
            reaction_lines=reaction_lines,
            rumor_lines=rumor_lines,
        )
        quest_lines = self.quests.on_npc_talk(
            self.player,
            npc_query,
            self.current_location,
            self.inventory,
            world=self.world,
            campaign_context=self.arc_context(),
        )
        if quest_lines:
            lines = [dialogue_text]
            lines.extend(quest_lines)
            lines.extend(self._apply_recent_quest_completions(self.current_location, location.get("name", self.current_location)))
            return "\n".join(lines)
        return dialogue_text

    def _cmd_ask(self, arg: str) -> str:
        usage = "Use format: ask <npc> about <topic>"
        if not arg:
            return "Ask whom about what?\n" + usage

        raw = arg.strip()
        split_key = " about "
        lowered = raw.lower()
        if split_key not in lowered:
            return "I could not parse that request.\n" + usage

        split_index = lowered.index(split_key)
        npc_query = self._extract_talkable_npc(raw[:split_index]) or self._strip_leading_article(raw[:split_index].strip()).lower()
        topic = self._strip_leading_article(raw[split_index + len(split_key):].strip())

        if not npc_query or not topic:
            return "Ask needs both an NPC and a topic.\n" + usage

        if npc_query not in self.TALKABLE_NPCS:
            return "Unknown NPC. You can ask: " + ", ".join(self.TALKABLE_NPCS.values()) + "."

        location = self.world.get_location(self.current_location)
        npcs_here = self._visible_npcs_at_location(self.current_location)
        display_npcs_here = [self.TALKABLE_NPCS.get(npc_id, npc_id.title()) for npc_id in npcs_here]
        if npc_query not in npcs_here:
            if display_npcs_here:
                return (
                    f"{self.TALKABLE_NPCS[npc_query]} is not here, so you cannot ask right now. "
                    "NPCs here: " + ", ".join(display_npcs_here)
                )
            return f"{self.TALKABLE_NPCS[npc_query]} is not here, and there is no one to ask."

        reply_text = Narrator.ask_text(
            npc_query,
            topic,
            self._history_flags(),
            npc_memory=self._npc_memory_context(npc_query),
        )
        npc_data = self.world.get_npc(npc_query)
        npc_name = self.world.npc_name(npc_query)
        role = str(npc_data.get("role", "Wanderer")).strip() or "Wanderer"
        reaction_entries = self._npc_authored_entries(npc_query, "reactions", topic=topic, limit=2)
        reaction_lines = [entry["text"] for entry in reaction_entries]
        rumor_lines = self._npc_authored_lines(npc_query, "rumors", topic=topic, limit=2)
        self._mark_rival_hunter_seen(npc_query)
        if reaction_lines or rumor_lines:
            generic_reply = reply_text.endswith("has nothing to say about that right now.")
            base_reply = "" if generic_reply else reply_text
            if reaction_entries:
                base_reply = reaction_entries[0]["text"]
            return Narrator.npc_topic_text(
                npc_name,
                role,
                topic,
                base_reply,
                reaction_lines=reaction_lines,
                rumor_lines=rumor_lines,
            )
        return reply_text

    def _cmd_accept(self, arg: str) -> str:
        query = arg.strip()
        if self._contract_board_here():
            board_available = self._board_available_contracts()
            if not query and board_available:
                lines = ["Accept Menu"]
                for index, (contract_id, contract) in enumerate(board_available, start=1):
                    title = str(contract.get("title", contract_id)).strip()
                    rank = str(contract.get("rank", "?")).strip().upper()
                    lines.append(f"{index}. [{rank}-Rank] {title}")
                lines.append("Use 'accept <number|name>'.")
                return "\n".join(lines)
            menu_index = self._menu_choice_index(query, len(board_available))
            if menu_index is not None:
                query = str(board_available[menu_index][0])
            contract_accepted, contract_lines, contract_id = self.contracts.accept_contract(
                self.player,
                query,
                self.CONTRACT_BOARD_LOCATION,
                self.world,
            )
            if contract_accepted and contract_id:
                contract_data = self.contracts.contracts.get(contract_id, {})
                self._log_event(
                    "contract_accepted",
                    contract_id=contract_id,
                    contract_title=contract_data.get("title", contract_id),
                    location_id=self.current_location,
                    location_name=self.world.get_location(self.current_location).get("name", self.current_location),
                )
                return "\n".join(contract_lines)

        npcs_here = self._visible_npcs_at_location(self.current_location)
        quest_options = self.quests.available_quests(
            self.player,
            npcs_here,
            world=self.world,
            current_location=self.current_location,
            campaign_context=self.arc_context(),
        )
        if not query and quest_options:
            lines = ["Accept Menu"]
            for index, (quest_id, quest) in enumerate(quest_options, start=1):
                title = str(quest.get("title", quest_id)).strip()
                lines.append(f"{index}. {title}")
            lines.append("Use 'accept <number|name>'.")
            return "\n".join(lines)
        menu_index = self._menu_choice_index(query, len(quest_options))
        if menu_index is not None:
            query = str(quest_options[menu_index][0])
        accepted, lines, quest_id = self.quests.accept_quest(
            self.player,
            query,
            npcs_here,
            self.inventory,
            world=self.world,
            current_location=self.current_location,
            campaign_context=self.arc_context(),
        )
        if accepted and quest_id:
            quest_data = self.quests.quests.get(quest_id, {})
            self._log_event(
                "quest_accepted",
                quest_id=quest_id,
                quest_title=quest_data.get("title", quest_id),
                location_id=self.current_location,
                location_name=self.world.get_location(self.current_location).get("name", self.current_location),
            )
            giver = str(quest_data.get("giver", "")).strip().lower()
            if giver:
                lines.extend(self._change_npc_trust(giver, 2, source=quest_id))
            lines.extend(self._post_action_world_tick("accept"))
        return "\n".join(lines)

    @staticmethod
    def _strip_leading_article(text: str) -> str:
        normalized = text.strip()
        for prefix in ("the ", "a ", "an "):
            if normalized.lower().startswith(prefix):
                return normalized[len(prefix):].strip()
        return normalized

    @staticmethod
    def _menu_choice_index(arg: str, count: int) -> int | None:
        raw = str(arg or "").strip()
        if not raw.isdigit():
            return None
        index = int(raw) - 1
        if 0 <= index < count:
            return index
        return None

    @staticmethod
    def _normalize_free_text(text: str) -> str:
        return " ".join(text.strip().lower().split())

    def _extract_talkable_npc(self, text: str) -> str | None:
        normalized = self._normalize_free_text(text)
        normalized = self._strip_leading_article(normalized)

        fillers = (
            "to ",
            "with ",
            "at ",
        )
        for filler in fillers:
            if normalized.startswith(filler):
                normalized = normalized[len(filler):].strip()

        for npc_id, npc_name in self.TALKABLE_NPCS.items():
            npc_name_lower = npc_name.lower()
            if normalized == npc_id or normalized == npc_name_lower:
                return npc_id
            if normalized.startswith(f"{npc_id} "):
                return npc_id
            if normalized.startswith(f"{npc_name_lower} "):
                return npc_id
            for alias in self.NPC_ALIASES.get(npc_id, ()):
                if normalized == alias or normalized.startswith(f"{alias} "):
                    return npc_id

        return None

    def _cmd_greet(self, arg: str) -> str:
        if not arg.strip():
            return Narrator.do_greet_text("")

        npc_query = self._extract_talkable_npc(arg)
        if not npc_query:
            return "You can greet: " + ", ".join(self.TALKABLE_NPCS.values()) + "."

        npcs_here = self._visible_npcs_at_location(self.current_location)
        display_npcs_here = [self.TALKABLE_NPCS.get(npc_id, npc_id.title()) for npc_id in npcs_here]
        if npc_query not in npcs_here:
            if display_npcs_here:
                return f"{self.TALKABLE_NPCS[npc_query]} is not here right now. NPCs here: " + ", ".join(display_npcs_here)
            return f"{self.TALKABLE_NPCS[npc_query]} is not here right now."

        return Narrator.do_greet_text(self.TALKABLE_NPCS[npc_query])

    def _cmd_listen(self, arg: str = "") -> str:
        focus = self._strip_leading_article(self._normalize_free_text(arg))
        if focus in {"", "area", "around", "around here", "room", "location", "here", "surroundings"}:
            focus = "area"

        location = self.world.get_location(self.current_location)
        npcs_here = self._visible_npcs_at_location(self.current_location)
        if focus and focus != "area":
            npc_query = self._extract_talkable_npc(focus)
            if npc_query and npc_query in npcs_here:
                return self._cmd_talk(npc_query)
            if self.inventory.find_item_in_inventory(self.player, self.world.items, focus):
                return self._cmd_inspect(focus)
            if self.world.find_item_at_location(self.current_location, focus):
                return self._cmd_inspect(focus)
            if self.world.is_current_location_query(self.current_location, focus):
                focus = "area"

        return Narrator.do_listen_text(
            location_name=location.get("name", self.current_location),
            enemies_here=bool(self.world.get_enemies_at(self.current_location)),
            npcs_here=bool(npcs_here),
            history_flags=self._history_flags(),
            focus=focus,
        )

    def _dispatch_parsed_intent(self, parsed: IntentParseResult, raw_text: str) -> str:
        action_output = self.action_router.route(self, parsed, raw_text)
        if action_output is not None:
            return action_output

        if parsed.intent == "observe":
            return self._cmd_look()

        if parsed.intent == "inspect":
            if not parsed.target:
                return "What do you want to inspect?"
            return self._cmd_inspect(parsed.target)

        if parsed.intent == "study":
            if not parsed.target:
                return "What do you want to study?"
            return self._cmd_inspect(parsed.target)

        if parsed.intent == "greet":
            return self._cmd_greet(parsed.target)

        if parsed.intent == "listen":
            return self._cmd_listen(parsed.target)

        if parsed.intent == "ask":
            npc_query = self._extract_talkable_npc(parsed.target)
            if parsed.topic:
                if not npc_query:
                    return f"Ask whom about {parsed.topic}?\nUse format: ask <npc> about <topic>"
                return self._cmd_ask(f"{npc_query} about {parsed.topic}")
            if npc_query:
                return self._cmd_talk(npc_query)
            return "Ask whom about what?\nUse format: ask <npc> about <topic>"

        if parsed.intent == "restricted":
            return Narrator.do_guardrail_text(raw_text)

        return Narrator.do_free_text(raw_text)

    def _maybe_process_free_text(self, raw_command: str) -> str | None:
        normalized = self._normalize_free_text(raw_command)
        if not normalized:
            return ""

        first_word = normalized.split(maxsplit=1)[0]
        if self._in_dungeon() and first_word in self.COMMAND_NAMES:
            return None
        if first_word in self.NLP_COMMAND_TRIGGERS:
            parsed = self.intent_parser.parse(raw_command)
            if parsed.intent != "unknown":
                if first_word in self.ACTION_COMMAND_TRIGGERS and " " not in normalized:
                    return None
                return self._dispatch_parsed_intent(parsed, raw_command)
            return None

        if first_word not in self.COMMAND_NAMES:
            parsed = self.intent_parser.parse(raw_command)
            return self._dispatch_parsed_intent(parsed, raw_command)

        return None

    def _cmd_do(self, arg: str) -> str:
        action = " ".join(arg.strip().split())
        if not action:
            return "Do what? Try a short action like: do greet the elder."

        parsed = self.intent_parser.parse(action)
        return self._dispatch_parsed_intent(parsed, action)

    def _local_shop_npcs(self) -> list[dict]:
        shops = []
        for npc_id in self._visible_npcs_at_location(self.current_location):
            npc_data = self.world.get_npc(npc_id)
            stock = npc_data.get("shop_inventory", [])
            buy_types = npc_data.get("buy_types", [])
            if not isinstance(stock, list):
                stock = []
            if not isinstance(buy_types, list):
                buy_types = []
            if not stock and not buy_types:
                continue
            shops.append(
                {
                    "npc_id": npc_id,
                    "name": self.world.npc_name(npc_id),
                    "faction": str(npc_data.get("faction", "")).strip().lower(),
                    "stock": [str(item_id).strip().lower() for item_id in stock if str(item_id).strip()],
                    "buy_types": [str(item_type).strip().lower() for item_type in buy_types if str(item_type).strip()],
                }
            )
        return shops

    def _shop_stock_lines(self, shop: dict) -> list[str]:
        lines = []
        faction_id = str(shop.get("faction", "")).strip().lower()
        if faction_id:
            lines.append(
                f"Standing: {self.factions.faction_name(faction_id)} {self.factions.standing_text(self.player, faction_id)}"
            )
            lines.append(f"Terms: {self.factions.service_terms_text(self.player, faction_id, shop['npc_id'])}")
        for item_id in shop["stock"]:
            base_cost = self.inventory.item_price(item_id, self.world.items)
            price = self.factions.price_for_service(self.player, shop["faction"], shop["npc_id"], base_cost)
            lines.append(self.inventory.item_shop_line(item_id, self.world.items, price))
        return lines

    def _buy_menu_options(self, shops: list[dict]) -> list[dict]:
        options = []
        for shop in shops:
            if not shop.get("stock"):
                continue
            allowed, denial = self.factions.service_access(self.player, shop["faction"], shop["npc_id"])
            if not allowed:
                continue
            for item_id in shop["stock"]:
                base_cost = self.inventory.item_price(item_id, self.world.items)
                price = self.factions.price_for_service(
                    self.player,
                    shop["faction"],
                    shop["npc_id"],
                    base_cost,
                )
                options.append(
                    {
                        "shop": shop,
                        "item_id": item_id,
                        "price": price,
                    }
                )
        return options

    def _shop_buys_item(self, shop: dict, item_id: str) -> bool:
        if item_id in shop.get("stock", []):
            return True
        item_type = str(self.world.items.get(item_id, {}).get("type", "")).strip().lower()
        return bool(item_type and item_type in shop.get("buy_types", []))

    def _sellable_inventory_lines(self, shops: list[dict]) -> list[str]:
        lines = []
        for item_id in self.player.inventory:
            for shop in shops:
                if not self._shop_buys_item(shop, item_id):
                    continue
                value = self.inventory.sell_price(item_id, self.world.items)
                lines.append(f"- {self.world.item_name(item_id)} to {shop['name']} for {value} gold")
                break
        return lines

    def _sell_menu_options(self, shops: list[dict]) -> list[dict]:
        options = []
        seen = set()
        for item_id in self.player.inventory:
            if item_id in seen:
                continue
            for shop in shops:
                if not self._shop_buys_item(shop, item_id):
                    continue
                options.append({"item_id": item_id, "shop": shop})
                seen.add(item_id)
                break
        return options

    def _upgradable_inventory_lines(self) -> list[str]:
        lines = []
        seen = set()
        for item_id in self.player.inventory:
            if item_id in seen:
                continue
            seen.add(item_id)
            item = self.world.items.get(item_id, {})
            max_level = self.player.max_item_upgrade_level(item)
            if max_level <= 0:
                continue
            label = self.inventory.item_label(item_id, self.world.items, self.player.item_upgrade_level(item_id, self.world.items))
            lines.append(f"- {label}: {self.inventory.upgrade_cost_text(self.player, item_id, self.world.items)}")
        return lines

    def _upgrade_menu_options(self) -> list[str]:
        options = []
        seen = set()
        for item_id in self.player.inventory:
            if item_id in seen:
                continue
            seen.add(item_id)
            item = self.world.items.get(item_id, {})
            if self.player.max_item_upgrade_level(item) <= 0:
                continue
            options.append(item_id)
        return options

    def _current_crafting_stations(self) -> set[str]:
        stations = {"field"}
        stations.update(self.CRAFTING_STATIONS.get(self.current_location, set()))
        return stations

    def _learn_available_recipes(self) -> list[str]:
        learned = self.crafting.learn_recipes_for_stations(
            self.player,
            self.world.recipes,
            self._current_crafting_stations(),
        )
        if not learned:
            return []
        learned_names = [self.crafting.recipe_name(recipe_id, self.world.recipes, self.world.items) for recipe_id in learned]
        return ["Recipe unlocked: " + ", ".join(learned_names) + "."]

    def _craft_menu_options(self) -> list[str]:
        return self.crafting.known_recipe_ids(self.player, self.world.recipes)

    def _cmd_buy(self, arg: str) -> str:
        shops = self._local_shop_npcs()
        if not shops:
            return "You cannot buy here: no vendor is offering goods in this location."

        query = arg.strip()
        menu_options = self._buy_menu_options(shops)
        if not query:
            if not menu_options:
                return "You cannot buy here: local vendors are not offering goods right now."
            lines = ["Buy Menu"]
            for index, option in enumerate(menu_options, start=1):
                item_id = option["item_id"]
                label = self.inventory.item_label(item_id, self.world.items)
                lines.append(f"{index}. {label} from {option['shop']['name']} ({option['price']} gold)")
            lines.append("Use 'buy <number|item>'.")
            return "\n".join(lines)

        selected_shop = None
        item_id = None
        menu_index = self._menu_choice_index(query, len(menu_options))
        if menu_index is not None:
            option = menu_options[menu_index]
            selected_shop = option["shop"]
            item_id = option["item_id"]
        for shop in shops:
            if selected_shop and item_id:
                break
            resolved = self.inventory.resolve_shop_item(self.world.items, arg, stock=shop["stock"])
            if not resolved:
                continue
            selected_shop = shop
            item_id = resolved
            break

        if not selected_shop or not item_id:
            lines = ["Nothing here matches that purchase request.", self._cmd_buy("")]
            return "\n".join(lines)

        allowed, denial = self.factions.service_access(
            self.player,
            selected_shop["faction"],
            selected_shop["npc_id"],
        )
        if not allowed:
            return denial

        base_cost = self.inventory.item_price(item_id, self.world.items)
        price = self.factions.price_for_service(
            self.player,
            selected_shop["faction"],
            selected_shop["npc_id"],
            base_cost,
        )
        sold, message = self.inventory.buy_item(
            self.player,
            item_id,
            self.world.items,
            cost_override=price,
            seller_name=selected_shop["name"],
            stock=selected_shop["stock"],
        )
        if sold:
            self._record_important_item_acquired(item_id, source="shop_purchase")
            lines = [message]
            lines.extend(
                self._apply_social_rewards(
                    reputation_changes={selected_shop["faction"]: 1} if selected_shop["faction"] else None,
                    trust_changes={selected_shop["npc_id"]: 1},
                    source=f"buy_{item_id}",
                )
            )
            if self.world.has_location_state(self.current_location, "merchant_caravan"):
                caravan_lines = self._clear_location_state(self.current_location, "merchant_caravan", reason="trade_complete")
                if caravan_lines:
                    lines.extend(caravan_lines)
            extra_lines = self._post_action_world_tick("buy")
            if extra_lines:
                lines.extend(extra_lines)
            return "\n".join(lines)
        return message

    def _cmd_sell(self, arg: str) -> str:
        shops = self._local_shop_npcs()
        if not shops:
            return "You cannot sell here: no local vendor is trading for goods in this location."

        if not self.player.inventory:
            return "You have nothing to sell."

        query = arg.strip()
        menu_options = self._sell_menu_options(shops)
        if not query:
            if not menu_options:
                return "No local vendor wants anything from your backpack right now."
            lines = ["Sell Menu"]
            for index, option in enumerate(menu_options, start=1):
                item_id = option["item_id"]
                value = self.inventory.sell_price(item_id, self.world.items)
                label = self.inventory.item_label(
                    item_id,
                    self.world.items,
                    self.player.item_upgrade_level(item_id, self.world.items),
                )
                lines.append(f"{index}. {label} to {option['shop']['name']} ({value} gold)")
            lines.append("Use 'sell <number|item>'.")
            return "\n".join(lines)

        menu_index = self._menu_choice_index(query, len(menu_options))
        if menu_index is not None:
            item_id = str(menu_options[menu_index]["item_id"])
        else:
            item_id = self.inventory.find_item_in_inventory(self.player, self.world.items, arg)
        if not item_id:
            lines = self.inventory.inventory_lines(self.player, self.world.items)
            return f"You do not have '{arg}'.\n" + "\n".join(lines)

        selected_shop = None
        for shop in shops:
            if self._shop_buys_item(shop, item_id):
                selected_shop = shop
                break

        if not selected_shop:
            return "No local vendor is willing to buy that item here."

        allowed, denial = self.factions.service_access(
            self.player,
            selected_shop["faction"],
            selected_shop["npc_id"],
        )
        if not allowed:
            return denial

        sold, message = self.inventory.sell_item(
            self.player,
            item_id,
            self.world.items,
            value_override=self.inventory.sell_price(item_id, self.world.items),
            buyer_name=selected_shop["name"],
        )
        if sold:
            lines = [message]
            lines.extend(
                self._apply_social_rewards(
                    reputation_changes={selected_shop["faction"]: 1} if selected_shop["faction"] else None,
                    trust_changes={selected_shop["npc_id"]: 1},
                    source=f"sell_{item_id}",
                )
            )
            extra_lines = self._post_action_world_tick("sell")
            if extra_lines:
                lines.extend(extra_lines)
            return "\n".join(lines)
        return message

    def _cmd_recipes(self) -> str:
        lines = []
        lines.extend(self._learn_available_recipes())
        lines.extend(
            self.crafting.recipes_lines(
                self.player,
                self.world.recipes,
                self.world.items,
                self._current_crafting_stations(),
            )
        )
        return "\n".join(lines)

    def _cmd_craft(self, arg: str) -> str:
        learned_lines = self._learn_available_recipes()
        query = arg.strip()
        menu_options = self._craft_menu_options()
        if not arg:
            if not menu_options:
                recipe_lines = self.crafting.recipes_lines(
                    self.player,
                    self.world.recipes,
                    self.world.items,
                    self._current_crafting_stations(),
                )
                return "\n".join(learned_lines + recipe_lines)
            lines = ["Craft Menu"]
            for index, recipe_id in enumerate(menu_options, start=1):
                recipe = self.world.recipes.get(recipe_id, {})
                recipe_name = self.crafting.recipe_name(recipe_id, self.world.recipes, self.world.items)
                costs = ", ".join(self.crafting.recipe_cost_parts(recipe, self.world.items)) or "no cost"
                status = self.crafting.recipe_status(
                    self.player,
                    recipe_id,
                    self.world.recipes,
                    self.world.items,
                    self._current_crafting_stations(),
                )
                if status["craftable"]:
                    status_text = "ready"
                elif not status["in_station"]:
                    status_text = f"needs {self.crafting.station_name(status['station'])}"
                else:
                    status_text = "missing " + ", ".join(status["missing"])
                lines.append(f"{index}. {recipe_name}: {costs} | {status_text}")
            lines.append("Use 'craft <number|item>'.")
            return "\n".join(learned_lines + lines)

        menu_index = self._menu_choice_index(query, len(menu_options))
        if menu_index is not None:
            recipe_id = menu_options[menu_index]
        else:
            recipe_id = self.crafting.resolve_recipe(self.player, arg, self.world.recipes, self.world.items)
        if not recipe_id:
            recipe_lines = self.crafting.recipes_lines(
                self.player,
                self.world.recipes,
                self.world.items,
                self._current_crafting_stations(),
            )
            return f"You do not know a recipe for '{arg}'.\n" + "\n".join(recipe_lines)

        crafted, message, output_item_id = self.crafting.craft(
            self.player,
            recipe_id,
            self.world.recipes,
            self.world.items,
            self._current_crafting_stations(),
        )
        if not crafted:
            return message

        lines = learned_lines + [message]
        if output_item_id:
            self._record_important_item_acquired(output_item_id, source="crafting")
            lines.extend(
                self.quests.on_item_obtained(
                    self.player,
                    output_item_id,
                    world=self.world,
                    current_location=self.current_location,
                    campaign_context=self.arc_context(),
                )
            )
            lines.extend(self._apply_contract_item_updates())
        extra_lines = self._post_action_world_tick("craft")
        if extra_lines:
            lines.extend(extra_lines)
        return "\n".join(lines)

    def _cmd_upgrade(self, arg: str) -> str:
        query = arg.strip()
        menu_options = self._upgrade_menu_options()
        if not query:
            if not menu_options:
                return "You are not carrying any gear that can be upgraded right now."
            lines = ["Upgrade Menu"]
            for index, item_id in enumerate(menu_options, start=1):
                label = self.inventory.item_label(
                    item_id,
                    self.world.items,
                    self.player.item_upgrade_level(item_id, self.world.items),
                )
                lines.append(f"{index}. {label}: {self.inventory.upgrade_cost_text(self.player, item_id, self.world.items)}")
            lines.append("Use 'upgrade <number|item>'.")
            return "\n".join(lines)

        menu_index = self._menu_choice_index(query, len(menu_options))
        if menu_index is not None:
            item_id = menu_options[menu_index]
        else:
            item_id = self.inventory.find_item_in_inventory(self.player, self.world.items, arg)
        if not item_id:
            return f"You do not have '{arg}'."

        upgraded, message = self.inventory.upgrade_item(self.player, item_id, self.world.items)
        if not upgraded:
            return message

        lines = [message]
        lines.extend(
            self.quests.on_item_obtained(
                self.player,
                item_id,
                world=self.world,
                current_location=self.current_location,
                campaign_context=self.arc_context(),
            )
        )
        lines.extend(self._apply_contract_item_updates())
        return "\n".join(lines)

    def _save_data(self) -> dict:
        location_name = self.world.get_location(self.current_location).get("name", self.current_location)
        return {
            "slot_meta": {
                "slot_id": self.current_slot,
                "character_name": self.player.name,
                "race": self.player.race,
                "player_class": self.player.player_class,
                "level": self.player.level,
                "current_location": self.current_location,
                "current_location_name": location_name,
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "playtime_seconds": self._current_playtime_seconds(),
            },
            "player": self.player.to_dict(),
            "current_location": self.current_location,
            "current_dungeon_room": self.current_dungeon_room,
            "quests": self.quests.to_dict(),
            "contracts": self.contracts.to_dict(),
            "world_state": self.world.state_to_dict(),
        }

    def _cmd_save(self, arg: str = "") -> str:
        slot_id = self._normalize_slot_id(arg)
        if arg.strip():
            if not slot_id:
                return "Save where? Use 'save <slot>'."
            self._set_active_slot(slot_id)
        self._ensure_save_storage()
        data = self._save_data()
        try:
            self.save_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as exc:
            return f"Could not save game: {exc}"
        self.playtime_seconds = int(data.get("slot_meta", {}).get("playtime_seconds", self.playtime_seconds))
        self.session_started_at = time.time()
        return f"Game saved to {self.save_path}."

    def _cmd_load(self, arg: str = "") -> str:
        slot_id = self._normalize_slot_id(arg)
        if arg.strip():
            if not slot_id:
                return "Load which slot? Use 'load <slot>'."
            self._set_active_slot(slot_id)
        self._ensure_save_storage()
        data, error = self._read_save_file(self.save_path)
        if error:
            return error
        assert data is not None

        # Reset world and engines to avoid carrying over runtime changes.
        self.world = World(self.data_dir)
        self._load_npc_registry()
        self.combat = CombatEngine()
        self.abilities = AbilityEngine()
        self.dice = DiceEngine()
        self.encounters = EncounterEngine()
        self.factions = FactionEngine(self.world.factions)
        self.campaign = CampaignEngine(self.world.arcs)
        self.crafting = CraftingEngine()
        self.inventory = InventoryEngine()
        self.quests = QuestEngine(self.world.quests, self.world.items)
        self.contracts = ContractEngine(self.world.contracts, self.world.items)

        self.player = Character.from_dict(data.get("player", {}))
        self._sync_social_state()
        slot_meta = data.get("slot_meta", {})
        if isinstance(slot_meta, dict):
            normalized_slot = self._normalize_slot_id(slot_meta.get("slot_id", self.current_slot))
            if normalized_slot:
                self.current_slot = normalized_slot
        self.save_path = self._slot_path(self.current_slot) if self.save_path.parent == self.save_dir else self.save_path
        self.playtime_seconds = max(0, int(slot_meta.get("playtime_seconds", 0) or 0)) if isinstance(slot_meta, dict) else 0
        self.session_started_at = time.time()

        saved_location = str(data.get("current_location", self.world.starting_location))
        if saved_location not in self.world.locations:
            self.current_location = self.world.starting_location
            location_note = " Saved location was invalid, so you were moved to the starting area."
        else:
            self.current_location = saved_location
            location_note = ""
        self.current_dungeon_room = None
        saved_room = str(data.get("current_dungeon_room", "")).strip().lower()
        if saved_room and self.world.has_dungeon(self.current_location) and self.world.dungeon_room(self.current_location, saved_room):
            self.current_dungeon_room = saved_room

        quests_data = data.get("quests", {})
        if isinstance(quests_data, dict):
            self.quests.load_from_dict(quests_data)

        contracts_data = data.get("contracts", {})
        if isinstance(contracts_data, dict):
            self.contracts.load_from_dict(contracts_data)

        world_state = data.get("world_state", {})
        if isinstance(world_state, dict):
            self.world.load_state_from_dict(world_state)

        self._backfill_quest_progress_events()
        self._backfill_world_progress_events()
        self._record_location_visit(self.current_location)
        self.contracts.sync_active_targets(self.player, self.world)
        self._refresh_hunter_guild_rank(source="load")
        self._refresh_titles(notify=False, source="load")
        self._refresh_identity_unlocks(notify=False)

        location_name = self.world.get_location(self.current_location).get("name", self.current_location)
        self._apply_recent_contract_completions(self.current_location, location_name)
        reminder = Narrator.load_reminder_text(
            location_name,
            self.chapter_context(),
            self.history_context(),
        )
        return f"Game loaded from {self.save_path}. Current location: {location_name}.{location_note}\n{reminder}"

    @staticmethod
    def _cmd_help() -> str:
        return (
            "Valerion Commands\n"
            "look               - Describe the current location.\n"
            "inspect <target>   - Focus on an item, NPC, or your surroundings, including item upgrade details.\n"
            "search <target>    - List visible items, enemies, NPCs, and exits.\n"
            "map                - Outline every location and its exits.\n"
            "move <exit>        - Travel to a connected area (e.g. move forest).\n"
            "fight [enemy]      - Engage a nearby enemy (defaults to the first).\n"
            "take [item]        - Pick up a nearby item.\n"
            "talk <npc>         - Converse with an NPC who is present.\n"
            "ask <npc> about <topic> - Ask a present NPC about a topic.\n"
            "accept <name>      - Accept a quest offer or board contract (number or name) in your current location.\n"
            "board              - Read the Stonewatch contract board in Market Square.\n"
            "contracts          - Review active and claimable board contracts.\n"
            "claim <contract>   - Claim payment for a finished board contract at Market Square (number or name).\n"
            "routes             - Review Waycarter Network routes from the current major hub.\n"
            "travel <hub>       - Pay for guarded passage between major hubs (number or hub name).\n"
            "activities [option]- Open local town activities for rumors, gossip, sparring, and downtime.\n"
            "do <free text>     - Optional wrapper for safe narrative input like observe, ask, or listen.\n"
            "free text          - You can also type lines like 'look around', 'go to the forest', or 'attack the slime'.\n"
            "buy <item>         - Purchase from a local vendor (number or item name).\n"
            "sell <item>        - Sell a carried item to a willing local vendor (number or item name).\n"
            "recipes            - Review known crafting recipes and their costs.\n"
            "craft <item>       - Craft a known recipe (number or item name) with required materials/station.\n"
            "upgrade <item>     - Improve a carried weapon/armor/accessory (number or item name).\n"
            "\n"
            "inventory          - See HP, focus, carry load, carried items, and gear.\n"
            "gear               - Show equipped items, upgrade levels, and build impact.\n"
            "character          - Show a compact full character sheet.\n"
            "sheet              - Alias for `character`.\n"
            "stats              - Snapshot core stats, derived combat values, and active quest/contract focus.\n"
            "skills             - Show skill totals, proficiencies, and linked core stats.\n"
            "abilities          - List your class abilities, spells, and current focus.\n"
            "recap              - Recap your location, resources, quests, and contracts.\n"
            "story              - Tell the story of your adventure so far.\n"
            "history            - Show a timeline of important adventure events.\n"
            "world              - Show active world-state changes by location.\n"
            "events             - Show active and recent world events.\n"
            "reputation         - Show faction reputation scores and tiers.\n"
            "factions           - Show faction descriptions and your standing.\n"
            "relations          - Show trust and memory for important NPCs.\n"
            "hint               - Get a next-step suggestion.\n"
            "rest               - Heal fully in Village Square, the Shop, or an Inn.\n"
            "use <item>         - Consume a potion or equip a weapon.\n"
            "cast <ability>     - Spend focus on a known spell or class ability.\n"
            "quests             - Show raw quest progress and completion.\n"
            "journal            - Read completed quest records only.\n"
            "about              - Explain engine rules vs AI narration.\n"
            "\n"
            "save [slot]        - Persist your run to the current or named save slot.\n"
            "load [slot]        - Resume from the current or named save slot.\n"
            "slots              - List save slots and their character summaries.\n"
            "delete <slot>      - Delete a save slot file.\n"
            "help               - Show this command list again.\n"
            "quit               - Exit Valerion."
        )
