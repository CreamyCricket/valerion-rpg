from dataclasses import dataclass, field
from typing import ClassVar, Optional


@dataclass
class Character:
    """Represents the player profile, deterministic combat values, and persistent progress."""

    DEFAULT_FACTION_REPUTATION: ClassVar[dict[str, int]] = {
        "kingdom_guard": 0,
        "merchant_guild": 0,
        "thieves_circle": 0,
        "shrine_keepers": 0,
        "forest_clans": 0,
        "cult_of_ash": 0,
    }
    DEFAULT_STATS: ClassVar[dict[str, int]] = {
        "strength": 10,
        "agility": 10,
        "vitality": 10,
        "endurance": 10,
        "mind": 10,
        "wisdom": 10,
        "charisma": 10,
        "luck": 10,
    }
    DEFAULT_SKILLS: ClassVar[dict[str, int]] = {
        "swordsmanship": 0,
        "archery": 0,
        "defense": 0,
        "spellcasting": 0,
        "stealth": 0,
        "survival": 0,
        "lore": 0,
        "persuasion": 0,
    }
    SKILL_STAT_MAP: ClassVar[dict[str, str]] = {
        "swordsmanship": "strength",
        "archery": "agility",
        "defense": "endurance",
        "spellcasting": "mind",
        "stealth": "agility",
        "survival": "wisdom",
        "lore": "wisdom",
        "persuasion": "charisma",
        "athletics": "endurance",
        "arcana": "mind",
        "lockpicking": "agility",
    }
    SKILL_ALIASES: ClassVar[dict[str, str]] = {
        "athletics": "defense",
        "arcana": "spellcasting",
        "lockpicking": "stealth",
    }
    ABILITY_ALIASES: ClassVar[dict[str, str]] = {
        "second_wind": "guard_stance",
        "spark": "firebolt",
        "mend": "healing_light",
        "cunning_strike": "backstab",
    }
    CLASS_ATTACK_STATS: ClassVar[dict[str, str]] = {
        "warrior": "strength",
        "ranger": "agility",
        "mage": "mind",
        "rogue": "agility",
    }
    DEFAULT_COMBAT_BOOSTS: ClassVar[dict[str, int]] = {
        "attack_bonus": 0,
        "damage_bonus": 0,
        "defense_bonus": 0,
        "dodge_bonus": 0,
        "crit_bonus": 0,
        "spell_bonus": 0,
        "heal_bonus": 0,
        "enemy_attack_penalty": 0,
        "enemy_defense_penalty": 0,
    }
    MAX_LOOT_LOG: ClassVar[int] = 20
    GENDERS: ClassVar[list[dict[str, str]]] = [
        {"id": "woman", "name": "Woman", "lore": "Seen as you choose to present yourself in the world."},
        {"id": "man", "name": "Man", "lore": "Seen as you choose to present yourself in the world."},
        {"id": "nonbinary", "name": "Nonbinary", "lore": "Seen as you choose to present yourself in the world."},
        {"id": "other", "name": "Other", "lore": "A personal identity that matters because it is yours."},
    ]
    RACES: ClassVar[dict[str, dict]] = {
        "human": {
            "name": "Human",
            "lore": "Humans spread along the roads between village and town, known less for one gift than for surviving change faster than anyone expects.",
            "stats": {"strength": 1, "charisma": 1},
            "skills": {"persuasion": 1},
            "gold": 2,
            "summary": "+1 Strength, +1 Charisma, +1 Persuasion, +2 Gold",
        },
        "elf": {
            "name": "Elf",
            "lore": "Elves keep long memory and sharp senses, moving through old woodland paths with a patience most younger peoples never quite learn.",
            "stats": {"agility": 2, "wisdom": 1},
            "skills": {"archery": 1, "stealth": 1},
            "focus": 1,
            "summary": "+2 Agility, +1 Wisdom, +1 Archery, +1 Stealth, +1 Focus",
        },
        "dwarf": {
            "name": "Dwarf",
            "lore": "Dwarves are people of stonework, forge smoke, and plain promises, carrying a reputation for endurance that can feel like stubbornness from the outside.",
            "stats": {"strength": 1, "vitality": 1, "endurance": 1},
            "max_hp": 2,
            "skills": {"defense": 1},
            "summary": "+1 Strength, +1 Vitality, +1 Endurance, +2 Max HP, +1 Defense",
        },
        "ashenborn": {
            "name": "Ashenborn",
            "lore": "Ashenborn descend from lands touched by old fire and sacred collapse, marked by restless instincts and an uneasy closeness to forgotten power.",
            "stats": {"mind": 1, "wisdom": 1, "luck": 1},
            "skills": {"spellcasting": 1, "stealth": 1},
            "focus": 1,
            "summary": "+1 Mind, +1 Wisdom, +1 Luck, +1 Spellcasting, +1 Stealth, +1 Focus",
        },
    }
    CLASSES: ClassVar[dict[str, dict]] = {
        "warrior": {
            "name": "Warrior",
            "lore": "Warriors are taught that fear can be survived if the stance holds, the line stays steady, and the work gets finished.",
            "stats": {"strength": 2, "vitality": 1, "endurance": 1},
            "max_hp": 3,
            "base_attack": 1,
            "skills": {"swordsmanship": 2, "defense": 1},
            "abilities": ["power_strike", "guard_stance"],
            "items": ["rusty_sword", "leather_vest", "bandage"],
            "equip": "rusty_sword",
            "equip_armor": "leather_vest",
            "summary": "+2 Strength, +1 Vitality, +1 Endurance, +3 Max HP, +1 Attack, +2 Swordsmanship, +1 Defense, Power Strike, Guard Stance, Rusty Sword, Leather Vest, Bandage",
        },
        "ranger": {
            "name": "Ranger",
            "lore": "Rangers live by noticing the bent grass, the wrong birdsong, and the shape of danger before it reaches sword range.",
            "stats": {"agility": 2, "endurance": 1, "luck": 1},
            "skills": {"archery": 2, "survival": 1, "stealth": 1},
            "abilities": ["aimed_shot", "track_prey"],
            "items": ["short_bow", "herb", "bandage"],
            "equip": "short_bow",
            "summary": "+2 Agility, +1 Endurance, +1 Luck, +2 Archery, +1 Survival, +1 Stealth, Aimed Shot, Track Prey, Short Bow, Herb, Bandage",
        },
        "mage": {
            "name": "Mage",
            "lore": "Mages learn restraint before power, trained to keep thought, symbol, and will aligned before they dare call on force.",
            "stats": {"mind": 2, "wisdom": 2},
            "skills": {"spellcasting": 2, "lore": 1},
            "focus": 4,
            "abilities": ["firebolt", "frost_shard", "healing_light"],
            "items": ["apprentice_staff", "mana_tonic", "potion"],
            "equip": "apprentice_staff",
            "summary": "+2 Mind, +2 Wisdom, +2 Spellcasting, +1 Lore, +4 Focus, Firebolt, Frost Shard, Healing Light, Apprentice Staff, Mana Tonic, Potion",
        },
        "rogue": {
            "name": "Rogue",
            "lore": "Rogues survive in the spaces between law and trouble, relying on timing, nerve, and knowing which risk is worth taking.",
            "stats": {"agility": 2, "charisma": 1, "luck": 1},
            "skills": {"stealth": 2, "persuasion": 1, "swordsmanship": 1},
            "gold": 3,
            "abilities": ["backstab", "smoke_step"],
            "items": ["road_knife", "bandage"],
            "equip": "road_knife",
            "summary": "+2 Agility, +1 Charisma, +1 Luck, +2 Stealth, +1 Persuasion, +1 Swordsmanship, +3 Gold, Backstab, Smoke Step, Road Knife, Bandage",
        },
    }
    BACKGROUNDS: ClassVar[dict[str, dict]] = {
        "village_born": {
            "name": "Village-born",
            "lore": "You were raised where everyone notices who returns at dusk, and where every lost road or failed harvest becomes everybody's problem.",
            "stats": {"vitality": 1, "charisma": 1},
            "skills": {"persuasion": 1},
            "gold": 4,
            "items": ["ration"],
            "faction_reputation": {"merchant_guild": 2},
            "summary": "+1 Vitality, +1 Charisma, +1 Persuasion, +4 Gold, Travel Ration, +2 Merchant Guild reputation",
        },
        "watcher": {
            "name": "Watcher",
            "lore": "You learned early to read road dust, tree lines, and distant movement, because warning a settlement half a minute sooner can matter.",
            "stats": {"agility": 1, "wisdom": 1},
            "skills": {"archery": 1, "survival": 1},
            "items": ["ration"],
            "faction_reputation": {"kingdom_guard": 3},
            "summary": "+1 Agility, +1 Wisdom, +1 Archery, +1 Survival, Travel Ration, +3 Kingdom Guard reputation",
        },
        "shrine_touched": {
            "name": "Shrine-touched",
            "lore": "Something in the old shrines answered you once, and ever since then ruined altars and sacred marks have felt a little too familiar.",
            "stats": {"mind": 1, "wisdom": 1},
            "skills": {"lore": 1, "spellcasting": 1},
            "focus": 1,
            "items": ["mana_tonic"],
            "faction_reputation": {"shrine_keepers": 3},
            "summary": "+1 Mind, +1 Wisdom, +1 Lore, +1 Spellcasting, +1 Focus, Mana Tonic, +3 Shrine Keepers reputation",
        },
        "wanderer": {
            "name": "Wanderer",
            "lore": "You belong more to the road than to any one roof, shaped by crossings, campfires, and the habit of leaving before luck turns.",
            "stats": {"endurance": 1, "luck": 1},
            "skills": {"survival": 1, "stealth": 1},
            "items": ["herb", "ration"],
            "faction_reputation": {"forest_clans": 3},
            "summary": "+1 Endurance, +1 Luck, +1 Survival, +1 Stealth, Herb, Travel Ration, +3 Forest Clans reputation",
        },
    }
    LEVEL_GROWTH: ClassVar[dict[str, list[dict[str, int]]]] = {
        "warrior": [{"strength": 1}, {"vitality": 1}, {"endurance": 1}],
        "ranger": [{"agility": 1}, {"endurance": 1}, {"luck": 1}],
        "mage": [{"mind": 1}, {"wisdom": 1}, {"mind": 1, "wisdom": 1}],
        "rogue": [{"agility": 1}, {"charisma": 1}, {"luck": 1}],
    }
    LEVEL_SKILL_GROWTH: ClassVar[dict[str, list[str]]] = {
        "warrior": ["swordsmanship", "defense"],
        "ranger": ["archery", "survival", "stealth"],
        "mage": ["spellcasting", "lore"],
        "rogue": ["stealth", "persuasion", "swordsmanship"],
    }
    ITEM_UPGRADE_CAPS: ClassVar[dict[str, int]] = {
        "common": 2,
        "uncommon": 2,
        "rare": 3,
        "epic": 3,
        "relic": 4,
    }

    name: str = "Hero"
    gender: str = "Other"
    race: str = "Human"
    player_class: str = "Warrior"
    background: str = "Village-born"
    bio: str = ""
    max_hp: int = 20
    hp: int = 20
    max_focus: int = 6
    focus: int = 6
    base_attack: int = 3
    level: int = 1
    xp: int = 0
    inventory: list[str] = field(default_factory=list)
    item_upgrades: dict[str, int] = field(default_factory=dict)
    equipped_weapon: Optional[str] = None
    equipped_armor: Optional[str] = None
    equipped_accessory: Optional[str] = None
    gold: int = 0
    stats: dict[str, int] = field(default_factory=lambda: dict(Character.DEFAULT_STATS))
    skills: dict[str, int] = field(default_factory=lambda: dict(Character.DEFAULT_SKILLS))
    abilities: list[str] = field(default_factory=list)
    combat_boosts: dict[str, int] = field(default_factory=lambda: dict(Character.DEFAULT_COMBAT_BOOSTS))
    combat_boost_name: str = ""
    combat_boost_summary: str = ""
    faction_reputation: dict[str, int] = field(default_factory=lambda: dict(Character.DEFAULT_FACTION_REPUTATION))
    npc_memory: dict[str, dict] = field(default_factory=dict)
    event_log: list[dict] = field(default_factory=list)
    loot_log: list[dict] = field(default_factory=list)
    """A persistent log of deterministic events that narration/quests read."""

    def __post_init__(self) -> None:
        self.name = self._clean_text(self.name, default="Hero", max_length=40)
        self.gender = self.normalize_gender(self.gender)
        self.race = self.option_name("race", self.race)
        self.player_class = self.option_name("class", self.player_class)
        self.background = self.option_name("background", self.background)
        self.bio = self._clean_text(self.bio, default="", max_length=180)
        self.base_attack = max(1, int(self.base_attack))
        self.max_hp = max(1, int(self.max_hp))
        self.hp = max(0, int(self.hp))
        self.max_focus = max(0, int(self.max_focus))
        self.focus = max(0, int(self.focus))
        self.stats = self._normalized_stats(self.stats)
        self.skills = self._normalized_skills(self.skills)
        self.abilities = self._normalized_abilities(self.abilities)
        self.combat_boosts = self._normalized_combat_boosts(self.combat_boosts)
        self.combat_boost_name = self._clean_text(self.combat_boost_name, default="", max_length=60)
        self.combat_boost_summary = self._clean_text(self.combat_boost_summary, default="", max_length=140)
        self.inventory = [str(item_id).strip().lower() for item_id in self.inventory if str(item_id).strip()]
        self.item_upgrades = self._normalized_item_upgrades(self.item_upgrades, self.inventory)
        self.equipped_weapon = str(self.equipped_weapon).strip().lower() if self.equipped_weapon else None
        self.equipped_armor = str(self.equipped_armor).strip().lower() if self.equipped_armor else None
        self.equipped_accessory = str(self.equipped_accessory).strip().lower() if self.equipped_accessory else None
        if self.equipped_weapon not in self.inventory:
            self.equipped_weapon = None
        if self.equipped_armor not in self.inventory:
            self.equipped_armor = None
        if self.equipped_accessory not in self.inventory:
            self.equipped_accessory = None
        self.loot_log = self._normalized_loot_log(self.loot_log)

    @staticmethod
    def _safe_int(value, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _normalize_key(value: str) -> str:
        return str(value).strip().lower().replace("-", "_").replace(" ", "_")

    @staticmethod
    def _clean_text(value: str, default: str, max_length: int) -> str:
        cleaned = " ".join(str(value or "").split())
        if not cleaned:
            cleaned = default
        return cleaned[:max_length]

    @classmethod
    def _catalog(cls, category: str):
        normalized = cls._normalize_key(category)
        if normalized == "race":
            return cls.RACES
        if normalized in {"class", "player_class"}:
            return cls.CLASSES
        if normalized == "background":
            return cls.BACKGROUNDS
        return {}

    @classmethod
    def _normalized_stats(cls, stats: dict | None) -> dict[str, int]:
        normalized = dict(cls.DEFAULT_STATS)
        if isinstance(stats, dict):
            for stat_name in cls.DEFAULT_STATS:
                normalized[stat_name] = max(1, cls._safe_int(stats.get(stat_name), normalized[stat_name]))
        return normalized

    @classmethod
    def _normalize_skill_key(cls, skill_name: str) -> str:
        normalized = cls._normalize_key(skill_name)
        return cls.SKILL_ALIASES.get(normalized, normalized)

    @classmethod
    def _normalized_skills(cls, skills: dict | None) -> dict[str, int]:
        normalized = dict(cls.DEFAULT_SKILLS)
        if isinstance(skills, dict):
            for skill_name, amount in skills.items():
                target = cls._normalize_skill_key(skill_name)
                if target not in normalized:
                    continue
                normalized[target] = max(0, cls._safe_int(amount, normalized[target]))
        return normalized

    @classmethod
    def _normalized_abilities(cls, abilities: list | None) -> list[str]:
        normalized = []
        if isinstance(abilities, list):
            for ability_id in abilities:
                ability_key = cls._normalize_key(ability_id)
                ability_key = cls.ABILITY_ALIASES.get(ability_key, ability_key)
                if ability_key and ability_key not in normalized:
                    normalized.append(ability_key)
        return normalized

    @classmethod
    def _normalized_combat_boosts(cls, boosts: dict | None) -> dict[str, int]:
        normalized = dict(cls.DEFAULT_COMBAT_BOOSTS)
        if isinstance(boosts, dict):
            for key in normalized:
                normalized[key] = cls._safe_int(boosts.get(key), normalized[key])
        return normalized

    @classmethod
    def _normalized_loot_log(cls, loot_log: list | None) -> list[dict]:
        normalized = []
        if isinstance(loot_log, list):
            for entry in loot_log[-cls.MAX_LOOT_LOG:]:
                if not isinstance(entry, dict):
                    continue
                item_id = cls._normalize_key(entry.get("item_id", ""))
                if not item_id:
                    continue
                normalized.append(
                    {
                        "item_id": item_id,
                        "source": cls._normalize_key(entry.get("source", "loot")) or "loot",
                    }
                )
        return normalized

    @classmethod
    def _normalized_item_upgrades(cls, item_upgrades: dict | None, inventory: list[str] | None = None) -> dict[str, int]:
        normalized = {}
        allowed = {str(item_id).strip().lower() for item_id in (inventory or []) if str(item_id).strip()}
        if isinstance(item_upgrades, dict):
            for item_id, level in item_upgrades.items():
                normalized_item = cls._normalize_key(item_id)
                if not normalized_item:
                    continue
                if inventory is not None and normalized_item not in allowed:
                    continue
                normalized_level = max(0, cls._safe_int(level, 0))
                if normalized_level > 0:
                    normalized[normalized_item] = normalized_level
        return normalized

    @staticmethod
    def _stat_modifier_for_value(value: int) -> int:
        return (max(1, int(value)) - 10) // 2

    @classmethod
    def _max_hp_bonus_for_stats(cls, stats: dict[str, int] | None) -> int:
        normalized = cls._normalized_stats(stats)
        vitality_mod = max(0, cls._stat_modifier_for_value(normalized.get("vitality", 10)))
        endurance_mod = max(0, cls._stat_modifier_for_value(normalized.get("endurance", 10)))
        return (vitality_mod * 2) + endurance_mod

    @classmethod
    def _focus_bonus_for_stats(cls, stats: dict[str, int] | None) -> int:
        normalized = cls._normalized_stats(stats)
        mind_mod = max(0, cls._stat_modifier_for_value(normalized.get("mind", 10)))
        wisdom_mod = max(0, cls._stat_modifier_for_value(normalized.get("wisdom", 10)))
        endurance_mod = max(0, cls._stat_modifier_for_value(normalized.get("endurance", 10)))
        return mind_mod + wisdom_mod + (endurance_mod // 2)

    @classmethod
    def creation_options(cls, category: str) -> list[dict]:
        catalog = cls._catalog(category)
        return [
            {
                "id": option_id,
                "name": str(option.get("name", option_id.replace("_", " ").title())),
                "lore": str(option.get("lore", "")),
                "summary": str(option.get("summary", "")),
            }
            for option_id, option in catalog.items()
        ]

    @classmethod
    def creation_option_details(cls, category: str, value: str) -> dict:
        normalized = cls.normalize_choice(category, value)
        option = cls._catalog(category).get(normalized, {})
        return {
            "id": normalized,
            "name": str(option.get("name", normalized.replace("_", " ").title())),
            "lore": str(option.get("lore", "")),
            "summary": str(option.get("summary", "")),
            "stats": {str(key): int(amount) for key, amount in option.get("stats", {}).items()},
            "skills": {str(key): int(amount) for key, amount in option.get("skills", {}).items()},
            "items": [str(item_id) for item_id in option.get("items", [])],
            "abilities": [str(ability_id) for ability_id in option.get("abilities", [])],
            "gold": int(option.get("gold", 0)),
            "max_hp": int(option.get("max_hp", 0)),
            "focus": int(option.get("focus", 0)),
            "base_attack": int(option.get("base_attack", 0)),
            "faction_reputation": {
                str(key): int(amount) for key, amount in option.get("faction_reputation", {}).items()
            },
        }

    @classmethod
    def option_name(cls, category: str, value: str) -> str:
        normalized = cls._normalize_key(value)
        catalog = cls._catalog(category)
        option = catalog.get(normalized)
        if option:
            return str(option.get("name", normalized.replace("_", " ").title()))
        if category == "gender":
            return cls.normalize_gender(value)
        return str(value).strip().title() or "Unknown"

    @classmethod
    def normalize_choice(cls, category: str, value: str) -> str:
        normalized = cls._normalize_key(value)
        catalog = cls._catalog(category)
        if normalized in catalog:
            return normalized
        return next(iter(catalog.keys()), "")

    @classmethod
    def normalize_gender(cls, value: str) -> str:
        normalized = cls._normalize_key(value)
        for option in cls.GENDERS:
            if normalized == option["id"]:
                return option["name"]
        return "Other"

    @classmethod
    def gender_options(cls) -> list[dict]:
        return [dict(option) for option in cls.GENDERS]

    @classmethod
    def create_from_profile(
        cls,
        name: str,
        gender: str,
        race: str,
        player_class: str,
        background: str,
        bio: str = "",
    ):
        normalized_race = cls.normalize_choice("race", race)
        normalized_class = cls.normalize_choice("class", player_class)
        normalized_background = cls.normalize_choice("background", background)
        character = cls(
            name=name,
            gender=gender,
            race=cls.option_name("race", normalized_race),
            player_class=cls.option_name("class", normalized_class),
            background=cls.option_name("background", normalized_background),
            bio=bio,
        )
        character.apply_creation_profile(normalized_race, normalized_class, normalized_background)
        return character

    def apply_creation_profile(self, race_id: str, class_id: str, background_id: str) -> None:
        self.max_hp = 20
        self.hp = 20
        self.max_focus = 6
        self.focus = 6
        self.base_attack = 3
        self.gold = 0
        self.inventory = []
        self.equipped_weapon = None
        self.equipped_armor = None
        self.stats = dict(self.DEFAULT_STATS)
        self.skills = dict(self.DEFAULT_SKILLS)
        self.abilities = []
        self.combat_boosts = dict(self.DEFAULT_COMBAT_BOOSTS)
        self.combat_boost_name = ""
        self.combat_boost_summary = ""
        self.faction_reputation = dict(self.DEFAULT_FACTION_REPUTATION)

        self._apply_template(self.RACES[self.normalize_choice("race", race_id)])
        self._apply_template(self.CLASSES[self.normalize_choice("class", class_id)])
        self._apply_template(self.BACKGROUNDS[self.normalize_choice("background", background_id)])
        self._apply_stat_resource_bonuses(previous_stats=self.DEFAULT_STATS)
        self.hp = self.max_hp
        self.focus = self.max_focus

    def _apply_template(self, template: dict) -> None:
        self.max_hp += int(template.get("max_hp", 0))
        self.max_focus += int(template.get("focus", 0))
        self.base_attack += int(template.get("base_attack", 0))
        self.gold += int(template.get("gold", 0))

        for stat_name, amount in template.get("stats", {}).items():
            normalized_stat = self._normalize_key(stat_name)
            if normalized_stat not in self.stats:
                continue
            self.stats[normalized_stat] = max(1, self.stats[normalized_stat] + int(amount))

        for skill_name, amount in template.get("skills", {}).items():
            normalized_skill = self._normalize_skill_key(skill_name)
            if normalized_skill not in self.skills:
                continue
            self.skills[normalized_skill] = self.skill_proficiency(normalized_skill) + int(amount)

        for ability_id in template.get("abilities", []):
            normalized_ability = self._normalize_key(ability_id)
            if normalized_ability and normalized_ability not in self.abilities:
                self.abilities.append(normalized_ability)

        for faction_id, amount in template.get("faction_reputation", {}).items():
            normalized_faction = self._normalize_key(faction_id)
            self.faction_reputation[normalized_faction] = self.reputation_value(normalized_faction) + int(amount)

        for item_id in template.get("items", []):
            normalized_item = self._normalize_key(item_id)
            if normalized_item:
                self.inventory.append(normalized_item)

        equip_item = self._normalize_key(template.get("equip", ""))
        if equip_item and equip_item in self.inventory:
            self.equipped_weapon = equip_item
        equip_armor = self._normalize_key(template.get("equip_armor", ""))
        if equip_armor and equip_armor in self.inventory:
            self.equipped_armor = equip_armor

    def _apply_stat_resource_bonuses(self, previous_stats: dict[str, int] | None = None) -> None:
        previous_stats = self._normalized_stats(previous_stats)
        old_hp_bonus = self._max_hp_bonus_for_stats(previous_stats)
        new_hp_bonus = self._max_hp_bonus_for_stats(self.stats)
        old_focus_bonus = self._focus_bonus_for_stats(previous_stats)
        new_focus_bonus = self._focus_bonus_for_stats(self.stats)

        self.max_hp = max(1, self.max_hp + (new_hp_bonus - old_hp_bonus))
        self.max_focus = max(0, self.max_focus + (new_focus_bonus - old_focus_bonus))

    @classmethod
    def creation_summary(cls, category: str, value: str) -> str:
        normalized = cls.normalize_choice(category, value)
        option = cls._catalog(category).get(normalized, {})
        return str(option.get("summary", ""))

    @classmethod
    def creation_lore(cls, category: str, value: str) -> str:
        normalized = cls.normalize_choice(category, value)
        option = cls._catalog(category).get(normalized, {})
        return str(option.get("lore", ""))

    def character_summary(self) -> dict:
        return {
            "name": self.name,
            "gender": self.gender,
            "race": self.race,
            "class": self.player_class,
            "background": self.background,
            "bio": self.bio,
            "race_summary": self.creation_summary("race", self.race),
            "class_summary": self.creation_summary("class", self.player_class),
            "background_summary": self.creation_summary("background", self.background),
            "max_hp": self.max_hp,
            "max_focus": self.max_focus,
            "base_attack": self.base_attack,
            "defense": 10,
            "gold": self.gold,
            "equipped_weapon": self.equipped_weapon.replace("_", " ").title() if self.equipped_weapon else "",
            "equipped_armor": self.equipped_armor.replace("_", " ").title() if self.equipped_armor else "",
            "prepared_ability": self.combat_boost_name,
            "prepared_ability_summary": self.combat_boost_summary,
            "stats": dict(self.stats),
            "skills": {skill_name: self.skill_value(skill_name) for skill_name in self.DEFAULT_SKILLS},
            "skill_proficiencies": {skill_name: self.skill_proficiency(skill_name) for skill_name in self.DEFAULT_SKILLS},
            "abilities": list(self.abilities),
        }

    @classmethod
    def creation_preview(cls, profile: dict | None) -> dict:
        profile = profile or {}
        character = cls.create_from_profile(
            name=str(profile.get("name", "Hero")),
            gender=str(profile.get("gender", "other")),
            race=str(profile.get("race", "human")),
            player_class=str(profile.get("player_class", "warrior")),
            background=str(profile.get("background", "village_born")),
            bio=str(profile.get("bio", "")),
        )
        summary = character.character_summary()
        summary["inventory"] = [item_id.replace("_", " ").title() for item_id in character.inventory]
        summary["abilities"] = [ability_id.replace("_", " ").title() for ability_id in character.abilities]
        summary.update(character.derived_stats({}))
        summary["race_lore"] = cls.creation_lore("race", character.race)
        summary["class_lore"] = cls.creation_lore("class", character.player_class)
        summary["background_lore"] = cls.creation_lore("background", character.background)
        summary["race_details"] = cls.creation_option_details("race", character.race)
        summary["class_details"] = cls.creation_option_details("class", character.player_class)
        summary["background_details"] = cls.creation_option_details("background", character.background)
        return summary

    def is_alive(self) -> bool:
        return self.hp > 0

    def heal(self, amount: int) -> int:
        old_hp = self.hp
        self.hp = min(self.max_hp, self.hp + max(0, int(amount)))
        return self.hp - old_hp

    def restore_focus(self, amount: int) -> int:
        old_focus = self.focus
        self.focus = min(self.max_focus, self.focus + max(0, int(amount)))
        return self.focus - old_focus

    def spend_focus(self, amount: int) -> bool:
        amount = max(0, int(amount))
        if self.focus < amount:
            return False
        self.focus -= amount
        return True

    def stat_value(self, stat_name: str) -> int:
        normalized = self._normalize_key(stat_name)
        return max(1, int(self.stats.get(normalized, self.DEFAULT_STATS.get(normalized, 10))))

    def effective_stat_value(self, stat_name: str, items_data: dict | None = None) -> int:
        normalized = self._normalize_key(stat_name)
        base_value = self.stat_value(normalized)
        if not items_data:
            return base_value
        return max(1, base_value + self.equipped_stat_bonus(items_data, normalized))

    def stat_modifier(self, stat_name: str) -> int:
        return (self.stat_value(stat_name) - 10) // 2

    def effective_stat_modifier(self, stat_name: str, items_data: dict | None = None) -> int:
        return (self.effective_stat_value(stat_name, items_data) - 10) // 2

    def equipped_item_ids(self) -> list[str]:
        item_ids = []
        for item_id in (self.equipped_weapon, self.equipped_armor, self.equipped_accessory):
            if item_id and item_id in self.inventory and item_id not in item_ids:
                item_ids.append(item_id)
        return item_ids

    def equipped_items(self, items_data: dict) -> list[dict]:
        return [self.effective_item_data(item_id, items_data) for item_id in self.equipped_item_ids()]

    @classmethod
    def item_upgrade_profile(cls, item_data: dict) -> dict:
        if not isinstance(item_data, dict):
            return {}

        explicit = item_data.get("upgrade_bonus", {})
        if isinstance(explicit, dict) and explicit:
            profile = {}
            for key, value in explicit.items():
                normalized_key = cls._normalize_key(key)
                if normalized_key in {"stat_bonuses", "skill_bonuses"} and isinstance(value, dict):
                    profile[normalized_key] = {
                        cls._normalize_skill_key(sub_key) if normalized_key == "skill_bonuses" else cls._normalize_key(sub_key): int(amount)
                        for sub_key, amount in value.items()
                        if int(amount)
                    }
                else:
                    profile[normalized_key] = int(value)
            return profile

        item_type = cls._normalize_key(item_data.get("type", ""))
        if item_type == "weapon":
            return {"attack_bonus": 1}
        if item_type == "armor":
            return {"defense_bonus": 1}
        return {}

    @classmethod
    def max_item_upgrade_level(cls, item_data: dict) -> int:
        profile = cls.item_upgrade_profile(item_data)
        if not profile:
            return 0
        rarity = cls._normalize_key(item_data.get("rarity", "common"))
        return max(0, int(cls.ITEM_UPGRADE_CAPS.get(rarity, 2)))

    def item_upgrade_level(self, item_id: str, items_data: dict | None = None) -> int:
        normalized_item = self._normalize_key(item_id)
        level = max(0, self._safe_int(self.item_upgrades.get(normalized_item), 0))
        if items_data and normalized_item in items_data:
            level = min(level, self.max_item_upgrade_level(items_data.get(normalized_item, {})))
        return level

    def set_item_upgrade_level(self, item_id: str, level: int, items_data: dict | None = None) -> None:
        normalized_item = self._normalize_key(item_id)
        normalized_level = max(0, self._safe_int(level, 0))
        if items_data and normalized_item in items_data:
            normalized_level = min(normalized_level, self.max_item_upgrade_level(items_data.get(normalized_item, {})))
        if normalized_level <= 0:
            self.item_upgrades.pop(normalized_item, None)
            return
        self.item_upgrades[normalized_item] = normalized_level

    def effective_item_data(self, item_id: str, items_data: dict) -> dict:
        normalized_item = self._normalize_key(item_id)
        base_item = dict(items_data.get(normalized_item, {}))
        if not base_item:
            return {}

        upgrade_level = self.item_upgrade_level(normalized_item, items_data)
        if upgrade_level <= 0:
            return base_item

        profile = self.item_upgrade_profile(base_item)
        if not profile:
            return base_item

        for key, per_level in profile.items():
            if key == "stat_bonuses" and isinstance(per_level, dict):
                existing = dict(base_item.get("stat_bonuses", {}))
                for stat_name, amount in per_level.items():
                    existing[stat_name] = self._safe_int(existing.get(stat_name), 0) + (int(amount) * upgrade_level)
                base_item["stat_bonuses"] = existing
                continue
            if key == "skill_bonuses" and isinstance(per_level, dict):
                existing = dict(base_item.get("skill_bonuses", {}))
                for skill_name, amount in per_level.items():
                    normalized_skill = self._normalize_skill_key(skill_name)
                    existing[normalized_skill] = self._safe_int(existing.get(normalized_skill), 0) + (int(amount) * upgrade_level)
                base_item["skill_bonuses"] = existing
                continue

            existing_value = self._safe_int(base_item.get(key), 0)
            if key == "attack_bonus" and not existing_value:
                existing_value = self._item_effect_bonus(base_item, "attack_plus_")
            elif key == "defense_bonus" and not existing_value:
                existing_value = self._item_effect_bonus(base_item, "defense_plus_")
            base_item[key] = existing_value + (int(per_level) * upgrade_level)

        return base_item

    def equipped_numeric_bonus(self, items_data: dict, bonus_key: str) -> int:
        total = 0
        for item_id in self.equipped_item_ids():
            item = self.effective_item_data(item_id, items_data)
            total += self._safe_int(item.get(bonus_key), 0)
        return total

    def equipped_stat_bonus(self, items_data: dict, stat_name: str) -> int:
        normalized = self._normalize_key(stat_name)
        total = 0
        for item_id in self.equipped_item_ids():
            item = self.effective_item_data(item_id, items_data)
            bonuses = item.get("stat_bonuses", {})
            if not isinstance(bonuses, dict):
                continue
            total += self._safe_int(bonuses.get(normalized), 0)
        return total

    def equipped_skill_bonus(self, items_data: dict, skill_name: str) -> int:
        normalized = self._normalize_skill_key(skill_name)
        total = 0
        for item_id in self.equipped_item_ids():
            item = self.effective_item_data(item_id, items_data)
            bonuses = item.get("skill_bonuses", {})
            if not isinstance(bonuses, dict):
                continue
            total += self._safe_int(bonuses.get(normalized), 0)
        return total

    def attack_stat_name(self, items_data: dict) -> str:
        if self.equipped_weapon and self.equipped_weapon in self.inventory:
            item = items_data.get(self.equipped_weapon, {})
            configured = self._normalize_key(item.get("attack_stat", ""))
            if configured in self.DEFAULT_STATS:
                return configured
        class_id = self.normalize_choice("class", self.player_class)
        return self.CLASS_ATTACK_STATS.get(class_id, "strength")

    def weapon_skill_name(self, items_data: dict) -> str:
        if self.equipped_weapon and self.equipped_weapon in self.inventory:
            weapon_id = self._normalize_key(self.equipped_weapon)
            weapon = items_data.get(weapon_id, {})
            attack_stat = self._normalize_key(weapon.get("attack_stat", ""))
            if attack_stat == "mind":
                return "spellcasting"
            if "bow" in weapon_id:
                return "archery"
            return "swordsmanship"
        class_id = self.normalize_choice("class", self.player_class)
        if class_id == "ranger":
            return "archery"
        if class_id == "mage":
            return "spellcasting"
        return "swordsmanship"

    @classmethod
    def _item_effect_bonus(cls, item_data: dict, prefix: str) -> int:
        effect = str(item_data.get("effect", ""))
        if effect.startswith(prefix):
            try:
                return int(effect.split("_")[-1])
            except ValueError:
                return 0
        return 0

    def weapon_bonus(self, items_data: dict) -> int:
        if not self.equipped_weapon or self.equipped_weapon not in self.inventory:
            return 0
        weapon = self.effective_item_data(self.equipped_weapon, items_data)
        explicit_bonus = self._safe_int(weapon.get("attack_bonus"), 0)
        if explicit_bonus:
            return explicit_bonus
        return self._item_effect_bonus(weapon, "attack_plus_")

    def armor_bonus(self, items_data: dict) -> int:
        if not self.equipped_armor or self.equipped_armor not in self.inventory:
            return 0
        armor = self.effective_item_data(self.equipped_armor, items_data)
        explicit_bonus = self._safe_int(armor.get("defense_bonus"), 0)
        if explicit_bonus:
            return explicit_bonus
        return self._item_effect_bonus(armor, "defense_plus_")

    def spell_power(self, items_data: dict | None = None) -> int:
        return max(
            0,
            self.effective_stat_modifier("mind", items_data)
            + max(0, self.effective_stat_modifier("wisdom", items_data))
            + (self.skill_proficiency("spellcasting", items_data) // 2)
            + self.equipped_numeric_bonus(items_data or {}, "spell_power_bonus")
            + self.combat_boosts["spell_bonus"],
        )

    def healing_power(self, items_data: dict | None = None) -> int:
        return max(
            0,
            max(0, self.effective_stat_modifier("wisdom", items_data))
            + (self.skill_proficiency("lore", items_data) // 2)
            + (self.skill_proficiency("spellcasting", items_data) // 2)
            + self.equipped_numeric_bonus(items_data or {}, "healing_power_bonus")
            + self.combat_boosts["heal_bonus"],
        )

    def magic_guard(self, items_data: dict | None = None) -> int:
        return (
            max(0, self.effective_stat_modifier("wisdom", items_data))
            + (self.skill_proficiency("lore", items_data) // 2)
            + self.equipped_numeric_bonus(items_data or {}, "magic_guard_bonus")
        )

    def resilience_value(self, items_data: dict | None = None) -> int:
        return (
            max(0, self.effective_stat_modifier("vitality", items_data))
            + max(0, self.effective_stat_modifier("endurance", items_data))
            + (self.skill_proficiency("defense", items_data) // 2)
            + (max(0, self.effective_stat_modifier("wisdom", items_data)) // 2)
        )

    def dodge_score(self, items_data: dict | None = None) -> int:
        return (
            max(0, self.effective_stat_modifier("agility", items_data))
            + (self.skill_proficiency("stealth", items_data) // 2)
            + self.equipped_numeric_bonus(items_data or {}, "dodge_bonus")
            + self.combat_boosts["dodge_bonus"]
        )

    def dodge_chance(self, items_data: dict | None = None) -> int:
        return min(30, (self.dodge_score(items_data) * 4) + max(0, self.effective_stat_modifier("luck", items_data)))

    def crit_chance(self, items_data: dict | None = None, stat_name: str = "") -> int:
        attack_stat = stat_name or self.attack_stat_name(items_data or {})
        agility_bonus = max(0, self.effective_stat_modifier("agility", items_data))
        attack_bonus = max(0, self.effective_stat_modifier(attack_stat, items_data))
        luck_bonus = max(0, self.effective_stat_modifier("luck", items_data))
        return min(
            25,
            4 + (agility_bonus * 2) + (attack_bonus * 2) + luck_bonus + self.equipped_numeric_bonus(items_data or {}, "crit_bonus") + self.combat_boosts["crit_bonus"],
        )

    def crit_threshold(self, items_data: dict | None = None, stat_name: str = "") -> int:
        chance = self.crit_chance(items_data or {}, stat_name=stat_name)
        steps = max(1, chance // 5)
        return max(15, 21 - steps)

    @staticmethod
    def critical_damage(damage: int) -> int:
        damage = max(1, int(damage))
        return damage + max(2, damage // 2)

    def carry_capacity(self) -> int:
        return 8 + (max(0, self.stat_modifier("strength")) * 2) + max(0, self.stat_modifier("endurance")) + self.level

    def attack_roll_modifier(self, items_data: dict, stat_name: str = "", bonus: int = 0) -> int:
        attack_stat = stat_name or self.attack_stat_name(items_data)
        attack_skill = self.weapon_skill_name(items_data)
        return max(
            1,
            self.base_attack
            + self.weapon_bonus(items_data)
            + max(0, self.effective_stat_modifier(attack_stat, items_data))
            + (self.skill_proficiency(attack_skill, items_data) // 2)
            + self.combat_boosts["attack_bonus"]
            + int(bonus),
        )

    def attack_value(self, items_data: dict) -> int:
        attack_stat = self.attack_stat_name(items_data)
        attack_skill = self.weapon_skill_name(items_data)
        attack = (
            self.base_attack
            + self.weapon_bonus(items_data)
            + max(0, self.effective_stat_modifier(attack_stat, items_data))
            + (self.skill_proficiency(attack_skill, items_data) // 2)
            + self.combat_boosts["damage_bonus"]
        )
        return max(1, attack)

    def defense_value(self, items_data: dict) -> int:
        defense = (
            10
            + max(0, self.effective_stat_modifier("endurance", items_data))
            + self.armor_bonus(items_data)
            + (self.skill_proficiency("defense", items_data) // 2)
            + self.dodge_score(items_data)
            + (self.magic_guard(items_data) // 2)
            + self.combat_boosts["defense_bonus"]
        )
        return max(1, defense)

    def skill_proficiency(self, skill_name: str, items_data: dict | None = None) -> int:
        normalized = self._normalize_skill_key(skill_name)
        total = max(0, int(self.skills.get(normalized, 0)))
        if items_data:
            total += self.equipped_skill_bonus(items_data, normalized)
        return max(0, total)

    def skill_value(self, skill_name: str, items_data: dict | None = None) -> int:
        normalized = self._normalize_key(skill_name)
        mapped_skill = self._normalize_skill_key(normalized)
        if mapped_skill not in self.DEFAULT_SKILLS and normalized not in self.SKILL_STAT_MAP:
            return 0
        stat_name = self.SKILL_STAT_MAP.get(normalized, self.SKILL_STAT_MAP.get(mapped_skill, "mind"))
        return self.skill_proficiency(mapped_skill, items_data) + self.effective_stat_modifier(stat_name, items_data)

    def apply_combat_boost(self, name: str, summary: str = "", **changes: int) -> None:
        boosts = dict(self.combat_boosts)
        for key, amount in changes.items():
            if key not in boosts:
                continue
            boosts[key] += int(amount)
        self.combat_boosts = self._normalized_combat_boosts(boosts)
        self.combat_boost_name = self._clean_text(name, default=self.combat_boost_name, max_length=60)
        self.combat_boost_summary = self._clean_text(summary, default=self.combat_boost_summary, max_length=140)

    def clear_combat_boosts(self) -> None:
        self.combat_boosts = dict(self.DEFAULT_COMBAT_BOOSTS)
        self.combat_boost_name = ""
        self.combat_boost_summary = ""

    def has_combat_boosts(self) -> bool:
        return any(self.combat_boosts.values())

    def derived_stats(self, items_data: dict) -> dict[str, int | str]:
        attack_stat = self.attack_stat_name(items_data)
        weapon_skill = self.weapon_skill_name(items_data)
        return {
            "max_hp": self.max_hp,
            "mana": self.max_focus,
            "focus": self.max_focus,
            "attack": self.attack_value(items_data),
            "accuracy": self.attack_roll_modifier(items_data),
            "defense": self.defense_value(items_data),
            "dodge_chance": self.dodge_chance(items_data),
            "crit_chance": self.crit_chance(items_data),
            "resilience": self.resilience_value(items_data),
            "spell_power": self.spell_power(items_data),
            "healing_power": self.healing_power(items_data),
            "magic_guard": self.magic_guard(items_data),
            "carry_capacity": self.carry_capacity(),
            "attack_stat": attack_stat.title(),
            "weapon_skill": weapon_skill.title(),
        }

    @staticmethod
    def _clamp_social_score(value: int) -> int:
        return max(-100, min(100, int(value)))

    def reputation_value(self, faction_id: str) -> int:
        normalized = self._normalize_key(faction_id)
        return self._clamp_social_score(self.faction_reputation.get(normalized, 0))

    def adjust_reputation(self, faction_id: str, amount: int) -> int:
        normalized = self._normalize_key(faction_id)
        current = self.reputation_value(normalized)
        updated = self._clamp_social_score(current + int(amount))
        self.faction_reputation[normalized] = updated
        return updated

    def ensure_npc_memory(self, npc_id: str, faction_id: str = "") -> dict:
        normalized_npc = self._normalize_key(npc_id)
        normalized_faction = self._normalize_key(faction_id)
        memory = self.npc_memory.get(normalized_npc)
        if not isinstance(memory, dict):
            memory = {}

        quests_completed = memory.get("quests_completed", [])
        if not isinstance(quests_completed, list):
            quests_completed = []

        memory = {
            "faction": memory.get("faction", normalized_faction),
            "quests_completed": [str(quest_id) for quest_id in quests_completed],
            "helped": max(0, self._safe_int(memory.get("helped"), 0)),
            "harmed": max(0, self._safe_int(memory.get("harmed"), 0)),
            "trust": self._clamp_social_score(self._safe_int(memory.get("trust"), 0)),
        }
        if normalized_faction and not memory["faction"]:
            memory["faction"] = normalized_faction
        self.npc_memory[normalized_npc] = memory
        return memory

    def npc_trust(self, npc_id: str) -> int:
        memory = self.ensure_npc_memory(npc_id)
        return self._clamp_social_score(memory.get("trust", 0))

    def adjust_npc_trust(self, npc_id: str, amount: int, faction_id: str = "") -> int:
        memory = self.ensure_npc_memory(npc_id, faction_id=faction_id)
        memory["trust"] = self._clamp_social_score(memory.get("trust", 0) + int(amount))
        return memory["trust"]

    def record_npc_help(self, npc_id: str, faction_id: str = "", trust_delta: int = 0) -> dict:
        memory = self.ensure_npc_memory(npc_id, faction_id=faction_id)
        memory["helped"] = int(memory.get("helped", 0)) + 1
        if trust_delta:
            memory["trust"] = self._clamp_social_score(memory.get("trust", 0) + int(trust_delta))
        return memory

    def record_npc_harm(self, npc_id: str, faction_id: str = "", trust_delta: int = 0) -> dict:
        memory = self.ensure_npc_memory(npc_id, faction_id=faction_id)
        memory["harmed"] = int(memory.get("harmed", 0)) + 1
        if trust_delta:
            memory["trust"] = self._clamp_social_score(memory.get("trust", 0) + int(trust_delta))
        return memory

    def record_npc_quest_completed(self, npc_id: str, quest_id: str, faction_id: str = "", trust_delta: int = 0) -> dict:
        memory = self.ensure_npc_memory(npc_id, faction_id=faction_id)
        normalized_quest = self._normalize_key(quest_id)
        quests_completed = memory.get("quests_completed", [])
        if normalized_quest and normalized_quest not in quests_completed:
            quests_completed.append(normalized_quest)
        memory["quests_completed"] = quests_completed
        if trust_delta:
            memory["trust"] = self._clamp_social_score(memory.get("trust", 0) + int(trust_delta))
        return memory

    def xp_needed_for_next_level(self) -> int:
        return 100 + ((self.level - 1) * 150)

    def _level_growth_pattern(self) -> list[dict[str, int]]:
        class_id = self.normalize_choice("class", self.player_class)
        return self.LEVEL_GROWTH.get(class_id, [{"vitality": 1}])

    def _level_skill_pattern(self) -> list[str]:
        class_id = self.normalize_choice("class", self.player_class)
        return self.LEVEL_SKILL_GROWTH.get(class_id, ["defense"])

    def gain_xp(self, amount: int) -> list[dict]:
        amount = max(0, int(amount))
        self.xp += amount
        level_ups = []

        while self.xp >= self.xp_needed_for_next_level():
            self.xp -= self.xp_needed_for_next_level()
            self.level += 1
            self.max_hp += 3
            self.max_focus += 1
            self.base_attack += 1
            previous_stats = dict(self.stats)

            growth_pattern = self._level_growth_pattern()
            growth_index = (self.level - 2) % len(growth_pattern)
            stat_increase = growth_pattern[growth_index]
            for stat_name, increase in stat_increase.items():
                if stat_name in self.stats:
                    self.stats[stat_name] = max(1, self.stats[stat_name] + int(increase))

            self._apply_stat_resource_bonuses(previous_stats=previous_stats)

            skill_pattern = self._level_skill_pattern()
            skill_name = skill_pattern[(self.level - 2) % len(skill_pattern)]
            self.skills[skill_name] = self.skill_proficiency(skill_name) + 1

            self.hp = self.max_hp
            self.focus = self.max_focus
            level_ups.append(
                {
                    "level": self.level,
                    "max_hp": self.max_hp,
                    "max_focus": self.max_focus,
                    "base_attack": self.base_attack,
                    "stats": dict(self.stats),
                    "skills": dict(self.skills),
                }
            )

        return level_ups

    def record_event(self, event_type: str, details: dict | None = None) -> None:
        normalized_type = self._normalize_key(event_type)
        if not normalized_type:
            return
        if details is None:
            details = {}
        if not isinstance(details, dict):
            details = {"value": str(details)}
        sanitized_details = {str(key): value for key, value in details.items()}
        self.event_log.append(
            {
                "index": len(self.event_log) + 1,
                "type": normalized_type,
                "details": sanitized_details,
            }
        )

    def has_event(self, event_type: str, detail_key: str | None = None, detail_value=None) -> bool:
        normalized_type = self._normalize_key(event_type)
        for event in self.event_log:
            if event.get("type") != normalized_type:
                continue
            if detail_key is None:
                return True
            details = event.get("details", {})
            if isinstance(details, dict) and details.get(detail_key) == detail_value:
                return True
        return False

    @staticmethod
    def _append_memory_entry(entries: list[dict], seen: set[str], entry_id: str, entry_name: str) -> None:
        normalized_id = str(entry_id).strip().lower()
        if not normalized_id or normalized_id in seen:
            return
        seen.add(normalized_id)
        entries.append({"id": normalized_id, "name": str(entry_name).strip() or normalized_id.replace("_", " ").title()})

    def event_memory(self) -> dict:
        memory = {
            "counts": {
                "locations_visited": 0,
                "enemies_defeated": 0,
                "quests_completed": 0,
                "minibosses_defeated": 0,
                "important_items_acquired": 0,
                "world_states_started": 0,
                "world_states_cleared": 0,
            },
            "visited_locations": [],
            "defeated_enemies": [],
            "completed_quests": [],
            "minibosses_defeated": [],
            "important_items_acquired": [],
            "world_states_started": [],
            "world_states_cleared": [],
            "recent_events": [dict(event) for event in self.event_log[-5:] if isinstance(event, dict)],
            "latest_event": dict(self.event_log[-1]) if self.event_log else None,
        }

        seen = {
            "visited_locations": set(),
            "defeated_enemies": set(),
            "completed_quests": set(),
            "minibosses_defeated": set(),
            "important_items_acquired": set(),
            "world_states_started": set(),
            "world_states_cleared": set(),
        }

        for event in self.event_log:
            if not isinstance(event, dict):
                continue
            event_type = str(event.get("type", "")).strip().lower()
            details = event.get("details", {})
            if not isinstance(details, dict):
                details = {}

            if event_type == "location_visited":
                memory["counts"]["locations_visited"] += 1
                self._append_memory_entry(
                    memory["visited_locations"],
                    seen["visited_locations"],
                    details.get("location_id", ""),
                    details.get("location_name", details.get("location_id", "")),
                )
            elif event_type == "enemy_defeated":
                memory["counts"]["enemies_defeated"] += 1
                self._append_memory_entry(
                    memory["defeated_enemies"],
                    seen["defeated_enemies"],
                    details.get("enemy_id", ""),
                    details.get("enemy_name", details.get("enemy_id", "")),
                )
            elif event_type == "quest_completed":
                memory["counts"]["quests_completed"] += 1
                self._append_memory_entry(
                    memory["completed_quests"],
                    seen["completed_quests"],
                    details.get("quest_id", ""),
                    details.get("quest_title", details.get("quest_id", "")),
                )
            elif event_type == "miniboss_defeated":
                memory["counts"]["minibosses_defeated"] += 1
                self._append_memory_entry(
                    memory["minibosses_defeated"],
                    seen["minibosses_defeated"],
                    details.get("enemy_id", ""),
                    details.get("enemy_name", details.get("enemy_id", "")),
                )
            elif event_type == "important_item_acquired":
                memory["counts"]["important_items_acquired"] += 1
                self._append_memory_entry(
                    memory["important_items_acquired"],
                    seen["important_items_acquired"],
                    details.get("item_id", ""),
                    details.get("item_name", details.get("item_id", "")),
                )
            elif event_type == "world_state_started":
                memory["counts"]["world_states_started"] += 1
                self._append_memory_entry(
                    memory["world_states_started"],
                    seen["world_states_started"],
                    details.get("state_id", ""),
                    details.get("event_name", details.get("state_id", "")),
                )
            elif event_type == "world_state_cleared":
                memory["counts"]["world_states_cleared"] += 1
                self._append_memory_entry(
                    memory["world_states_cleared"],
                    seen["world_states_cleared"],
                    details.get("state_id", ""),
                    details.get("event_name", details.get("state_id", "")),
                )

        return memory

    def location_event_memory(self, location_id: str) -> dict:
        normalized_location = self._normalize_key(location_id)
        memory = {
            "visit_count": 0,
            "defeated_enemies": [],
            "minibosses_defeated": [],
            "world_states_started": [],
            "world_states_cleared": [],
            "recent_events": [],
        }
        seen = {
            "defeated_enemies": set(),
            "minibosses_defeated": set(),
            "world_states_started": set(),
            "world_states_cleared": set(),
        }

        for event in self.event_log:
            if not isinstance(event, dict):
                continue
            event_type = str(event.get("type", "")).strip().lower()
            details = event.get("details", {})
            if not isinstance(details, dict):
                details = {}
            if self._normalize_key(details.get("location_id", "")) != normalized_location:
                continue

            memory["recent_events"].append(dict(event))
            if event_type == "location_visited":
                memory["visit_count"] += 1
            elif event_type == "enemy_defeated":
                self._append_memory_entry(
                    memory["defeated_enemies"],
                    seen["defeated_enemies"],
                    details.get("enemy_id", ""),
                    details.get("enemy_name", details.get("enemy_id", "")),
                )
            elif event_type == "miniboss_defeated":
                self._append_memory_entry(
                    memory["minibosses_defeated"],
                    seen["minibosses_defeated"],
                    details.get("enemy_id", ""),
                    details.get("enemy_name", details.get("enemy_id", "")),
                )
            elif event_type == "world_state_started":
                self._append_memory_entry(
                    memory["world_states_started"],
                    seen["world_states_started"],
                    details.get("state_id", ""),
                    details.get("event_name", details.get("state_id", "")),
                )
            elif event_type == "world_state_cleared":
                self._append_memory_entry(
                    memory["world_states_cleared"],
                    seen["world_states_cleared"],
                    details.get("state_id", ""),
                    details.get("event_name", details.get("state_id", "")),
                )

        memory["recent_events"] = memory["recent_events"][-3:]
        return memory

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "gender": self.gender,
            "race": self.race,
            "player_class": self.player_class,
            "background": self.background,
            "bio": self.bio,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "focus": self.focus,
            "max_focus": self.max_focus,
            "base_attack": self.base_attack,
            "level": self.level,
            "xp": self.xp,
            "gold": self.gold,
            "inventory": list(self.inventory),
            "item_upgrades": dict(self.item_upgrades),
            "equipped_weapon": self.equipped_weapon,
            "equipped_armor": self.equipped_armor,
            "equipped_accessory": self.equipped_accessory,
            "stats": dict(self.stats),
            "skills": dict(self.skills),
            "abilities": list(self.abilities),
            "combat_boosts": dict(self.combat_boosts),
            "combat_boost_name": self.combat_boost_name,
            "combat_boost_summary": self.combat_boost_summary,
            "faction_reputation": dict(self.faction_reputation),
            "npc_memory": {
                npc_id: {
                    "faction": str(memory.get("faction", "")),
                    "quests_completed": [str(quest_id) for quest_id in memory.get("quests_completed", [])],
                    "helped": max(0, int(memory.get("helped", 0))),
                    "harmed": max(0, int(memory.get("harmed", 0))),
                    "trust": self._clamp_social_score(memory.get("trust", 0)),
                }
                for npc_id, memory in self.npc_memory.items()
                if isinstance(memory, dict)
            },
            "event_log": [dict(event) for event in self.event_log if isinstance(event, dict)],
        }

    @classmethod
    def from_dict(cls, data: dict):
        max_hp = max(1, cls._safe_int(data.get("max_hp"), 20))
        hp = min(max(0, cls._safe_int(data.get("hp"), max_hp)), max_hp)
        max_focus = max(0, cls._safe_int(data.get("max_focus"), 6))
        focus = min(max(0, cls._safe_int(data.get("focus"), max_focus)), max_focus)
        base_attack = max(1, cls._safe_int(data.get("base_attack"), 3))
        level = max(1, cls._safe_int(data.get("level"), 1))
        xp = max(0, cls._safe_int(data.get("xp"), 0))
        gold = max(0, cls._safe_int(data.get("gold"), 0))

        inventory_raw = data.get("inventory", [])
        inventory = [str(item_id) for item_id in inventory_raw] if isinstance(inventory_raw, list) else []
        item_upgrades = cls._normalized_item_upgrades(data.get("item_upgrades", {}), inventory)

        equipped_weapon = data.get("equipped_weapon")
        if equipped_weapon is not None:
            equipped_weapon = str(equipped_weapon)
        if equipped_weapon not in inventory:
            equipped_weapon = None

        equipped_armor = data.get("equipped_armor")
        if equipped_armor is not None:
            equipped_armor = str(equipped_armor)
        if equipped_armor not in inventory:
            equipped_armor = None

        equipped_accessory = data.get("equipped_accessory")
        if equipped_accessory is not None:
            equipped_accessory = str(equipped_accessory)
        if equipped_accessory not in inventory:
            equipped_accessory = None

        name = cls._clean_text(data.get("name", "Hero"), default="Hero", max_length=40)
        gender = cls.normalize_gender(data.get("gender", "Other"))
        race = cls.option_name("race", data.get("race", "Human"))
        player_class = cls.option_name("class", data.get("player_class", data.get("class", "Warrior")))
        background = cls.option_name("background", data.get("background", "Village-born"))
        bio = cls._clean_text(data.get("bio", ""), default="", max_length=180)

        fallback_profile = cls.create_from_profile(
            name=name,
            gender=gender,
            race=race,
            player_class=player_class,
            background=background,
            bio=bio,
        )

        stats_raw = data.get("stats", {})
        if isinstance(stats_raw, dict):
            merged_stats = dict(fallback_profile.stats)
            for stat_name, amount in stats_raw.items():
                normalized_stat = cls._normalize_key(stat_name)
                if normalized_stat in merged_stats:
                    merged_stats[normalized_stat] = max(1, cls._safe_int(amount, merged_stats[normalized_stat]))
            stats = cls._normalized_stats(merged_stats)
        else:
            stats = dict(fallback_profile.stats)

        skills_raw = data.get("skills", {})
        if isinstance(skills_raw, dict):
            merged_skills = dict(fallback_profile.skills)
            for skill_name, amount in skills_raw.items():
                normalized_skill = cls._normalize_skill_key(skill_name)
                if normalized_skill in merged_skills:
                    merged_skills[normalized_skill] = max(0, cls._safe_int(amount, merged_skills[normalized_skill]))
            skills = cls._normalized_skills(merged_skills)
        else:
            skills = dict(fallback_profile.skills)

        abilities = cls._normalized_abilities(data.get("abilities", fallback_profile.abilities))
        if not abilities:
            abilities = list(fallback_profile.abilities)
        for starter_ability in fallback_profile.abilities:
            if starter_ability not in abilities:
                abilities.append(starter_ability)

        if "max_hp" not in data:
            max_hp = fallback_profile.max_hp
            hp = max_hp
        if "max_focus" not in data:
            max_focus = fallback_profile.max_focus
            focus = max_focus

        combat_boosts = cls._normalized_combat_boosts(data.get("combat_boosts", {}))
        combat_boost_name = cls._clean_text(data.get("combat_boost_name", ""), default="", max_length=60)
        combat_boost_summary = cls._clean_text(data.get("combat_boost_summary", ""), default="", max_length=140)

        faction_raw = data.get("faction_reputation", {})
        faction_reputation = dict(cls.DEFAULT_FACTION_REPUTATION)
        if isinstance(faction_raw, dict):
            for faction_id, default_value in cls.DEFAULT_FACTION_REPUTATION.items():
                faction_reputation[faction_id] = cls._clamp_social_score(
                    cls._safe_int(faction_raw.get(faction_id), default_value)
                )

        npc_memory_raw = data.get("npc_memory", {})
        npc_memory = {}
        if isinstance(npc_memory_raw, dict):
            for npc_id, memory in npc_memory_raw.items():
                if not isinstance(memory, dict):
                    continue
                quests_completed = memory.get("quests_completed", [])
                if not isinstance(quests_completed, list):
                    quests_completed = []
                npc_memory[str(npc_id).strip().lower()] = {
                    "faction": str(memory.get("faction", "")).strip().lower(),
                    "quests_completed": [str(quest_id).strip().lower() for quest_id in quests_completed if str(quest_id).strip()],
                    "helped": max(0, cls._safe_int(memory.get("helped"), 0)),
                    "harmed": max(0, cls._safe_int(memory.get("harmed"), 0)),
                    "trust": cls._clamp_social_score(cls._safe_int(memory.get("trust"), 0)),
                }

        event_log_data = data.get("event_log", [])
        event_log = []
        if isinstance(event_log_data, list):
            for raw_event in event_log_data:
                if not isinstance(raw_event, dict):
                    continue
                event_type = str(raw_event.get("type", "")).strip().lower()
                if not event_type:
                    continue
                details = raw_event.get("details", {})
                if not isinstance(details, dict):
                    details = {}
                event_log.append(
                    {
                        "index": len(event_log) + 1,
                        "type": event_type,
                        "details": {str(key): value for key, value in details.items()},
                    }
                )

        return cls(
            name=name,
            gender=gender,
            race=race,
            player_class=player_class,
            background=background,
            bio=bio,
            max_hp=max_hp,
            hp=hp,
            max_focus=max_focus,
            focus=focus,
            base_attack=base_attack,
            level=level,
            xp=xp,
            inventory=inventory,
            item_upgrades=item_upgrades,
            equipped_weapon=equipped_weapon,
            equipped_armor=equipped_armor,
            equipped_accessory=equipped_accessory,
            gold=gold,
            stats=stats,
            skills=skills,
            abilities=abilities,
            combat_boosts=combat_boosts,
            combat_boost_name=combat_boost_name,
            combat_boost_summary=combat_boost_summary,
            faction_reputation=faction_reputation,
            npc_memory=npc_memory,
            event_log=event_log,
        )
