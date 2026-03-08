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
        "mind": 10,
        "vitality": 10,
    }
    DEFAULT_SKILLS: ClassVar[dict[str, int]] = {
        "athletics": 0,
        "survival": 0,
        "lore": 0,
        "persuasion": 0,
        "arcana": 0,
        "stealth": 0,
    }
    SKILL_STAT_MAP: ClassVar[dict[str, str]] = {
        "athletics": "strength",
        "survival": "vitality",
        "lore": "mind",
        "persuasion": "mind",
        "arcana": "mind",
        "stealth": "agility",
        "lockpicking": "agility",
    }
    SKILL_ALIASES: ClassVar[dict[str, str]] = {
        "lockpicking": "stealth",
    }
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
            "stats": {"strength": 1, "mind": 1},
            "skills": {"persuasion": 1},
            "gold": 2,
            "summary": "+1 Strength, +1 Mind, +1 Persuasion, +2 Gold",
        },
        "elf": {
            "name": "Elf",
            "lore": "Elves keep long memory and sharp senses, moving through old woodland paths with a patience most younger peoples never quite learn.",
            "stats": {"agility": 1, "mind": 1},
            "skills": {"stealth": 1, "survival": 1},
            "focus": 1,
            "summary": "+1 Agility, +1 Mind, +1 Stealth, +1 Survival, +1 Focus",
        },
        "dwarf": {
            "name": "Dwarf",
            "lore": "Dwarves are people of stonework, forge smoke, and plain promises, carrying a reputation for endurance that can feel like stubbornness from the outside.",
            "stats": {"strength": 1, "vitality": 2},
            "max_hp": 2,
            "skills": {"athletics": 1},
            "summary": "+1 Strength, +2 Vitality, +2 Max HP, +1 Athletics",
        },
        "ashenborn": {
            "name": "Ashenborn",
            "lore": "Ashenborn descend from lands touched by old fire and sacred collapse, marked by restless instincts and an uneasy closeness to forgotten power.",
            "stats": {"agility": 1, "mind": 1},
            "skills": {"arcana": 1, "stealth": 1},
            "focus": 1,
            "summary": "+1 Agility, +1 Mind, +1 Arcana, +1 Stealth, +1 Focus",
        },
    }
    CLASSES: ClassVar[dict[str, dict]] = {
        "warrior": {
            "name": "Warrior",
            "lore": "Warriors are taught that fear can be survived if the stance holds, the line stays steady, and the work gets finished.",
            "stats": {"strength": 2, "vitality": 1},
            "max_hp": 3,
            "base_attack": 1,
            "skills": {"athletics": 1},
            "abilities": ["second_wind"],
            "items": ["rusty_sword", "bandage"],
            "equip": "rusty_sword",
            "summary": "+2 Strength, +1 Vitality, +3 Max HP, +1 Attack, Second Wind, Rusty Sword, Bandage",
        },
        "ranger": {
            "name": "Ranger",
            "lore": "Rangers live by noticing the bent grass, the wrong birdsong, and the shape of danger before it reaches sword range.",
            "stats": {"agility": 2, "vitality": 1},
            "skills": {"survival": 1, "stealth": 1},
            "abilities": ["aimed_shot"],
            "items": ["herb", "bandage"],
            "summary": "+2 Agility, +1 Vitality, +1 Survival, +1 Stealth, Aimed Shot, Herb, Bandage",
        },
        "mage": {
            "name": "Mage",
            "lore": "Mages learn restraint before power, trained to keep thought, symbol, and will aligned before they dare call on force.",
            "stats": {"mind": 3},
            "skills": {"lore": 1, "arcana": 2},
            "focus": 4,
            "abilities": ["spark", "mend"],
            "items": ["potion"],
            "summary": "+3 Mind, +1 Lore, +2 Arcana, +4 Focus, Spark, Mend, Potion",
        },
        "rogue": {
            "name": "Rogue",
            "lore": "Rogues survive in the spaces between law and trouble, relying on timing, nerve, and knowing which risk is worth taking.",
            "stats": {"agility": 2, "mind": 1},
            "skills": {"stealth": 2, "persuasion": 1},
            "gold": 3,
            "abilities": ["cunning_strike"],
            "items": ["bandage"],
            "summary": "+2 Agility, +1 Mind, +2 Stealth, +1 Persuasion, +3 Gold, Cunning Strike, Bandage",
        },
    }
    BACKGROUNDS: ClassVar[dict[str, dict]] = {
        "village_born": {
            "name": "Village-born",
            "lore": "You were raised where everyone notices who returns at dusk, and where every lost road or failed harvest becomes everybody's problem.",
            "stats": {"vitality": 1},
            "skills": {"persuasion": 1},
            "gold": 5,
            "faction_reputation": {"merchant_guild": 2},
            "summary": "+1 Vitality, +1 Persuasion, +5 Gold, +2 Merchant Guild reputation",
        },
        "watcher": {
            "name": "Watcher",
            "lore": "You learned early to read road dust, tree lines, and distant movement, because warning a settlement half a minute sooner can matter.",
            "stats": {"agility": 1},
            "skills": {"athletics": 1, "survival": 1},
            "faction_reputation": {"kingdom_guard": 3},
            "summary": "+1 Agility, +1 Athletics, +1 Survival, +3 Kingdom Guard reputation",
        },
        "shrine_touched": {
            "name": "Shrine-touched",
            "lore": "Something in the old shrines answered you once, and ever since then ruined altars and sacred marks have felt a little too familiar.",
            "stats": {"mind": 1},
            "skills": {"lore": 1, "arcana": 1},
            "focus": 1,
            "faction_reputation": {"shrine_keepers": 3},
            "summary": "+1 Mind, +1 Lore, +1 Arcana, +1 Focus, +3 Shrine Keepers reputation",
        },
        "wanderer": {
            "name": "Wanderer",
            "lore": "You belong more to the road than to any one roof, shaped by crossings, campfires, and the habit of leaving before luck turns.",
            "stats": {"agility": 1},
            "skills": {"survival": 1, "stealth": 1},
            "items": ["herb"],
            "faction_reputation": {"forest_clans": 3},
            "summary": "+1 Agility, +1 Survival, +1 Stealth, Herb, +3 Forest Clans reputation",
        },
    }
    LEVEL_GROWTH: ClassVar[dict[str, list[dict[str, int]]]] = {
        "warrior": [{"strength": 1}, {"vitality": 1}],
        "ranger": [{"agility": 1}, {"vitality": 1}],
        "mage": [{"mind": 1}, {"mind": 1, "vitality": 1}],
        "rogue": [{"agility": 1}, {"mind": 1}],
    }
    LEVEL_SKILL_GROWTH: ClassVar[dict[str, list[str]]] = {
        "warrior": ["athletics", "survival"],
        "ranger": ["survival", "stealth"],
        "mage": ["arcana", "lore"],
        "rogue": ["stealth", "persuasion"],
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
    equipped_weapon: Optional[str] = None
    equipped_armor: Optional[str] = None
    gold: int = 0
    stats: dict[str, int] = field(default_factory=lambda: dict(Character.DEFAULT_STATS))
    skills: dict[str, int] = field(default_factory=lambda: dict(Character.DEFAULT_SKILLS))
    abilities: list[str] = field(default_factory=list)
    faction_reputation: dict[str, int] = field(default_factory=lambda: dict(Character.DEFAULT_FACTION_REPUTATION))
    npc_memory: dict[str, dict] = field(default_factory=dict)
    event_log: list[dict] = field(default_factory=list)
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
        self.hp = min(max(0, int(self.hp)), self.max_hp)
        self.max_focus = max(0, int(self.max_focus))
        self.focus = min(max(0, int(self.focus)), self.max_focus)
        self.stats = self._normalized_stats(self.stats)
        self.skills = self._normalized_skills(self.skills)
        self.abilities = self._normalized_abilities(self.abilities)

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
                if ability_key and ability_key not in normalized:
                    normalized.append(ability_key)
        return normalized

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
        self.faction_reputation = dict(self.DEFAULT_FACTION_REPUTATION)

        self._apply_template(self.RACES[self.normalize_choice("race", race_id)])
        self._apply_template(self.CLASSES[self.normalize_choice("class", class_id)])
        self._apply_template(self.BACKGROUNDS[self.normalize_choice("background", background_id)])
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
            "max_hp": self.max_hp,
            "max_focus": self.max_focus,
            "base_attack": self.base_attack,
            "defense": 10,
            "gold": self.gold,
            "stats": dict(self.stats),
            "skills": {skill_name: self.skill_value(skill_name) for skill_name in self.DEFAULT_SKILLS},
            "abilities": list(self.abilities),
        }

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

    def stat_modifier(self, stat_name: str) -> int:
        return (self.stat_value(stat_name) - 10) // 2

    def attack_value(self, items_data: dict) -> int:
        attack = self.base_attack + max(0, self.stat_modifier("strength"))
        if not self.equipped_weapon or self.equipped_weapon not in self.inventory:
            return max(1, attack)

        weapon = items_data.get(self.equipped_weapon, {})
        effect = weapon.get("effect", "")
        if effect.startswith("attack_plus_"):
            try:
                attack += int(effect.split("_")[-1])
            except ValueError:
                pass
        return max(1, attack)

    def defense_value(self, items_data: dict) -> int:
        defense = 10 + max(0, self.stat_modifier("vitality"))
        if not self.equipped_armor or self.equipped_armor not in self.inventory:
            return max(1, defense)

        armor = items_data.get(self.equipped_armor, {})
        effect = str(armor.get("effect", ""))
        if effect.startswith("defense_plus_"):
            try:
                defense += int(effect.split("_")[-1])
            except ValueError:
                pass
        return max(1, defense)

    def skill_proficiency(self, skill_name: str) -> int:
        normalized = self._normalize_skill_key(skill_name)
        return max(0, int(self.skills.get(normalized, 0)))

    def skill_value(self, skill_name: str) -> int:
        normalized = self._normalize_key(skill_name)
        mapped_skill = self._normalize_skill_key(normalized)
        if mapped_skill not in self.DEFAULT_SKILLS and normalized not in self.SKILL_STAT_MAP:
            return 0
        stat_name = self.SKILL_STAT_MAP.get(normalized, self.SKILL_STAT_MAP.get(mapped_skill, "mind"))
        return self.skill_proficiency(mapped_skill) + self.stat_modifier(stat_name)

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
        return self.LEVEL_SKILL_GROWTH.get(class_id, ["survival"])

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

            growth_pattern = self._level_growth_pattern()
            growth_index = (self.level - 2) % len(growth_pattern)
            stat_increase = growth_pattern[growth_index]
            for stat_name, increase in stat_increase.items():
                if stat_name in self.stats:
                    self.stats[stat_name] = max(1, self.stats[stat_name] + int(increase))

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
            "equipped_weapon": self.equipped_weapon,
            "equipped_armor": self.equipped_armor,
            "stats": dict(self.stats),
            "skills": dict(self.skills),
            "abilities": list(self.abilities),
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

        stats = cls._normalized_stats(data.get("stats", fallback_profile.stats))

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

        if "max_focus" not in data:
            max_focus = fallback_profile.max_focus
            focus = max_focus

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
            equipped_weapon=equipped_weapon,
            equipped_armor=equipped_armor,
            gold=gold,
            stats=stats,
            skills=skills,
            abilities=abilities,
            faction_reputation=faction_reputation,
            npc_memory=npc_memory,
            event_log=event_log,
        )
