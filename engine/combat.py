from engine.dice import DiceEngine
from player.character import Character


class CombatEngine:
    """Resolves deterministic combat, including enemy family abilities."""

    PLAYER_DEFENSE = 10
    DEFAULT_ENEMY_DEFENSE = 10
    DEFAULT_ENEMY_STATS = {
        "strength": 10,
        "agility": 10,
        "vitality": 10,
        "endurance": 10,
        "mind": 10,
        "wisdom": 10,
        "charisma": 10,
        "luck": 10,
    }
    DEFAULT_ENEMY_SKILLS = {
        "swordsmanship": 0,
        "archery": 0,
        "defense": 0,
        "spellcasting": 0,
        "stealth": 0,
        "survival": 0,
        "lore": 0,
        "persuasion": 0,
    }
    FAMILY_ALIASES = {
        "oozes": "slimes",
        "raiders": "bandits",
    }
    FAMILY_LIBRARY = {
        "wolves": {
            "stat_focus": ["agility", "wisdom"],
            "allowed_abilities": ["bite", "howl", "pack_attack"],
            "behavior_tendencies": ["hunter", "aggressive"],
        },
        "bandits": {
            "stat_focus": ["strength", "agility"],
            "allowed_abilities": ["slash", "dirty_trick", "ambush", "jab", "cheap_shot", "scatter"],
            "behavior_tendencies": ["aggressive", "cowardly"],
        },
        "spiders": {
            "stat_focus": ["agility", "luck"],
            "allowed_abilities": ["venom_bite", "web_trap", "pounce"],
            "behavior_tendencies": ["hunter", "defensive"],
        },
        "slimes": {
            "stat_focus": ["vitality", "endurance"],
            "allowed_abilities": ["corrosive_splash", "divide", "engulf"],
            "behavior_tendencies": ["defensive"],
        },
        "shrine_creatures": {
            "stat_focus": ["mind", "wisdom"],
            "allowed_abilities": ["grave_touch", "ash_bolt", "warding_hex"],
            "behavior_tendencies": ["defensive", "aggressive"],
        },
        "cultists": {
            "stat_focus": ["mind", "wisdom"],
            "allowed_abilities": ["grave_touch", "ash_bolt", "warding_hex"],
            "behavior_tendencies": ["aggressive", "defensive"],
        },
        "forest_beasts": {
            "stat_focus": ["strength", "vitality"],
            "allowed_abilities": ["maul", "pounce", "thick_hide", "crushing_blow"],
            "behavior_tendencies": ["aggressive", "hunter"],
        },
        "abyss_beasts": {
            "stat_focus": ["strength", "vitality"],
            "allowed_abilities": ["maul", "thick_hide", "crushing_blow", "pounce"],
            "behavior_tendencies": ["aggressive", "hunter"],
        },
        "ruin_guardians": {
            "stat_focus": ["strength", "vitality"],
            "allowed_abilities": ["heavy_strike", "stone_defense", "stomp"],
            "behavior_tendencies": ["defensive"],
        },
        "ash_heralds": {
            "stat_focus": ["mind", "wisdom"],
            "allowed_abilities": ["grave_touch", "ash_bolt", "warding_hex"],
            "behavior_tendencies": ["aggressive", "defensive"],
        },
    }
    TYPE_LIBRARY = {
        "hunter": {"attack_stat": "agility", "skill_focus": ["survival", "stealth"], "allowed_abilities": ["bite"], "preferred_abilities": ["bite"]},
        "pack_hunter": {"attack_stat": "agility", "skill_focus": ["survival", "defense"], "allowed_abilities": ["bite", "howl"], "preferred_abilities": ["howl", "bite"]},
        "alpha_hunter": {"attack_stat": "agility", "skill_focus": ["survival", "defense"], "allowed_abilities": ["bite", "howl", "pack_attack"], "preferred_abilities": ["howl", "pack_attack", "bite"]},
        "cutpurse": {"attack_stat": "agility", "skill_focus": ["stealth", "swordsmanship"], "allowed_abilities": ["slash"], "preferred_abilities": ["slash"]},
        "skirmisher": {"attack_stat": "agility", "skill_focus": ["stealth", "swordsmanship"], "allowed_abilities": ["slash", "dirty_trick"], "preferred_abilities": ["dirty_trick", "slash"]},
        "raider": {"attack_stat": "agility", "skill_focus": ["stealth", "swordsmanship"], "allowed_abilities": ["jab", "slash"], "preferred_abilities": ["jab", "slash"]},
        "enforcer": {"attack_stat": "strength", "skill_focus": ["swordsmanship", "defense"], "allowed_abilities": ["slash", "dirty_trick", "ambush"], "preferred_abilities": ["slash", "ambush", "dirty_trick"]},
        "pass_raider": {"attack_stat": "strength", "skill_focus": ["swordsmanship", "defense"], "allowed_abilities": ["slash", "dirty_trick"], "preferred_abilities": ["slash", "dirty_trick"]},
        "scavenger": {"attack_stat": "agility", "skill_focus": ["stealth", "swordsmanship"], "allowed_abilities": ["dirty_trick", "slash"], "preferred_abilities": ["dirty_trick", "slash"]},
        "wreck_scavenger": {"attack_stat": "agility", "skill_focus": ["stealth", "swordsmanship"], "allowed_abilities": ["jab", "scatter"], "preferred_abilities": ["scatter", "jab"]},
        "surf_reaver": {"attack_stat": "agility", "skill_focus": ["stealth", "swordsmanship"], "allowed_abilities": ["cheap_shot", "jab", "scatter"], "preferred_abilities": ["scatter", "cheap_shot", "jab"]},
        "ambusher": {"attack_stat": "agility", "skill_focus": ["stealth", "survival"], "allowed_abilities": ["venom_bite", "web_trap", "pounce"], "preferred_abilities": ["web_trap", "venom_bite", "pounce"]},
        "ooze": {"attack_stat": "vitality", "skill_focus": ["defense"], "allowed_abilities": ["corrosive_splash", "divide", "engulf"], "preferred_abilities": ["corrosive_splash", "divide", "engulf"]},
        "hexer": {"attack_stat": "mind", "skill_focus": ["spellcasting", "lore"], "allowed_abilities": ["grave_touch", "ash_bolt"], "preferred_abilities": ["ash_bolt", "grave_touch"]},
        "ash_hexer": {"attack_stat": "mind", "skill_focus": ["spellcasting", "lore"], "allowed_abilities": ["ash_bolt", "warding_hex", "grave_touch"], "preferred_abilities": ["warding_hex", "ash_bolt", "grave_touch"]},
        "ember_spirit": {"attack_stat": "mind", "skill_focus": ["spellcasting", "lore"], "allowed_abilities": ["ash_bolt", "warding_hex"], "preferred_abilities": ["ash_bolt", "warding_hex"]},
        "undead_guard": {"attack_stat": "wisdom", "skill_focus": ["defense", "lore"], "allowed_abilities": ["grave_touch"], "preferred_abilities": ["grave_touch"]},
        "stone_guardian": {"attack_stat": "strength", "skill_focus": ["defense"], "allowed_abilities": ["heavy_strike", "stone_defense", "stomp"], "preferred_abilities": ["stone_defense", "heavy_strike", "stomp"]},
        "grave_sentinel": {"attack_stat": "strength", "skill_focus": ["defense", "lore"], "allowed_abilities": ["heavy_strike", "stone_defense", "stomp"], "preferred_abilities": ["stone_defense", "heavy_strike", "stomp"]},
        "ember_sentinel": {"attack_stat": "strength", "skill_focus": ["defense", "lore"], "allowed_abilities": ["heavy_strike", "stone_defense", "stomp"], "preferred_abilities": ["stone_defense", "heavy_strike", "stomp"]},
        "charger": {"attack_stat": "strength", "skill_focus": ["defense", "survival"], "allowed_abilities": ["maul", "pounce"], "preferred_abilities": ["maul", "pounce"]},
        "cliff_charger": {"attack_stat": "strength", "skill_focus": ["defense", "survival"], "allowed_abilities": ["maul", "thick_hide"], "preferred_abilities": ["thick_hide", "maul"]},
        "brute": {"attack_stat": "strength", "skill_focus": ["defense"], "allowed_abilities": ["maul", "thick_hide", "crushing_blow"], "preferred_abilities": ["thick_hide", "maul", "crushing_blow"]},
    }
    ENEMY_ABILITIES = {
        "bite": {
            "name": "Bite",
            "min_level": 1,
            "cost": 1,
            "kind": "attack",
            "scale_stat": "agility",
            "scale_skill": "survival",
            "damage": 2,
            "accuracy_bonus": 1,
        },
        "howl": {
            "name": "Howl",
            "min_level": 2,
            "cost": 2,
            "kind": "self_buff",
            "buff": {"attack_bonus": 1, "damage_bonus": 1, "crit_bonus": 5},
        },
        "pack_attack": {
            "name": "Pack Attack",
            "min_level": 4,
            "cost": 3,
            "kind": "attack",
            "scale_stat": "agility",
            "scale_skill": "survival",
            "damage": 4,
            "accuracy_bonus": 2,
            "crit_bonus": 5,
        },
        "venom_bite": {
            "name": "Venom Bite",
            "min_level": 1,
            "cost": 1,
            "kind": "attack",
            "scale_stat": "agility",
            "scale_skill": "stealth",
            "damage": 2,
            "accuracy_bonus": 1,
            "target_attack_penalty": 1,
        },
        "web_trap": {
            "name": "Web Trap",
            "min_level": 2,
            "cost": 2,
            "kind": "attack",
            "scale_stat": "agility",
            "scale_skill": "stealth",
            "damage": 1,
            "accuracy_bonus": 2,
            "target_defense_penalty": 1,
            "target_dodge_penalty": 1,
        },
        "slash": {
            "name": "Slash",
            "min_level": 1,
            "cost": 1,
            "kind": "attack",
            "scale_stat": "strength",
            "scale_skill": "swordsmanship",
            "damage": 2,
            "accuracy_bonus": 1,
        },
        "dirty_trick": {
            "name": "Dirty Trick",
            "min_level": 2,
            "cost": 2,
            "kind": "attack",
            "scale_stat": "agility",
            "scale_skill": "stealth",
            "damage": 1,
            "accuracy_bonus": 2,
            "target_attack_penalty": 1,
            "target_defense_penalty": 1,
        },
        "ambush": {
            "name": "Ambush",
            "min_level": 3,
            "cost": 3,
            "kind": "attack",
            "scale_stat": "agility",
            "scale_skill": "stealth",
            "damage": 3,
            "accuracy_bonus": 2,
            "crit_bonus": 10,
        },
        "grave_touch": {
            "name": "Grave Touch",
            "min_level": 1,
            "cost": 1,
            "kind": "attack",
            "scale_stat": "wisdom",
            "scale_skill": "lore",
            "damage": 2,
            "accuracy_bonus": 1,
        },
        "ash_bolt": {
            "name": "Ash Bolt",
            "min_level": 2,
            "cost": 2,
            "kind": "attack",
            "scale_stat": "mind",
            "scale_skill": "spellcasting",
            "damage": 3,
            "accuracy_bonus": 1,
        },
        "warding_hex": {
            "name": "Warding Hex",
            "min_level": 3,
            "cost": 2,
            "kind": "hybrid",
            "scale_stat": "wisdom",
            "scale_skill": "spellcasting",
            "damage": 1,
            "accuracy_bonus": 1,
            "buff": {"defense_bonus": 1},
            "target_attack_penalty": 1,
        },
        "maul": {
            "name": "Maul",
            "min_level": 1,
            "cost": 1,
            "kind": "attack",
            "scale_stat": "strength",
            "scale_skill": "defense",
            "damage": 3,
        },
        "pounce": {
            "name": "Pounce",
            "min_level": 2,
            "cost": 2,
            "kind": "attack",
            "scale_stat": "agility",
            "scale_skill": "survival",
            "damage": 2,
            "accuracy_bonus": 2,
            "crit_bonus": 5,
        },
        "thick_hide": {
            "name": "Thick Hide",
            "min_level": 2,
            "cost": 2,
            "kind": "self_buff",
            "buff": {"defense_bonus": 2},
        },
        "crushing_blow": {
            "name": "Crushing Blow",
            "min_level": 4,
            "cost": 3,
            "kind": "attack",
            "scale_stat": "strength",
            "scale_skill": "defense",
            "damage": 4,
            "accuracy_bonus": 1,
        },
        "heavy_strike": {
            "name": "Heavy Strike",
            "min_level": 1,
            "cost": 2,
            "kind": "attack",
            "scale_stat": "strength",
            "scale_skill": "defense",
            "damage": 3,
            "accuracy_bonus": 1,
        },
        "stone_defense": {
            "name": "Stone Defense",
            "min_level": 2,
            "cost": 2,
            "kind": "self_buff",
            "buff": {"defense_bonus": 2, "damage_bonus": 1},
        },
        "stomp": {
            "name": "Stomp",
            "min_level": 4,
            "cost": 3,
            "kind": "attack",
            "scale_stat": "vitality",
            "scale_skill": "defense",
            "damage": 4,
            "target_defense_penalty": 1,
        },
        "corrosive_splash": {
            "name": "Corrosive Splash",
            "min_level": 1,
            "cost": 1,
            "kind": "attack",
            "scale_stat": "vitality",
            "scale_skill": "defense",
            "damage": 2,
            "target_defense_penalty": 1,
        },
        "corrosive_slam": {
            "name": "Corrosive Slam",
            "min_level": 1,
            "cost": 1,
            "kind": "attack",
            "scale_stat": "vitality",
            "scale_skill": "defense",
            "damage": 2,
            "target_defense_penalty": 1,
        },
        "divide": {
            "name": "Divide",
            "min_level": 2,
            "cost": 2,
            "kind": "self_buff",
            "buff": {"defense_bonus": 1, "damage_bonus": 1},
        },
        "engulf": {
            "name": "Engulf",
            "min_level": 2,
            "cost": 2,
            "kind": "attack",
            "scale_stat": "vitality",
            "scale_skill": "defense",
            "damage": 3,
            "accuracy_bonus": 1,
        },
        "jab": {
            "name": "Jab",
            "min_level": 1,
            "cost": 1,
            "kind": "attack",
            "scale_stat": "agility",
            "scale_skill": "swordsmanship",
            "damage": 1,
            "accuracy_bonus": 1,
        },
        "cheap_shot": {
            "name": "Cheap Shot",
            "min_level": 2,
            "cost": 2,
            "kind": "attack",
            "scale_stat": "agility",
            "scale_skill": "stealth",
            "damage": 2,
            "accuracy_bonus": 2,
            "crit_bonus": 10,
        },
        "scatter": {
            "name": "Scatter",
            "min_level": 2,
            "cost": 2,
            "kind": "self_buff",
            "buff": {"dodge_bonus": 1, "defense_bonus": 1},
        },
    }

    def __init__(self):
        self.dice = DiceEngine()

    @staticmethod
    def _normalize_key(value: str) -> str:
        return str(value).strip().lower().replace("-", "_").replace(" ", "_")

    @staticmethod
    def _stat_modifier(value: int) -> int:
        return (max(1, int(value)) - 10) // 2

    def _normalized_enemy_stats(self, stats: dict | None) -> dict[str, int]:
        normalized = dict(self.DEFAULT_ENEMY_STATS)
        if isinstance(stats, dict):
            for stat_name in normalized:
                try:
                    normalized[stat_name] = max(1, int(stats.get(stat_name, normalized[stat_name])))
                except (TypeError, ValueError):
                    pass
        return normalized

    def _normalized_enemy_skills(self, skills: dict | None) -> dict[str, int]:
        normalized = dict(self.DEFAULT_ENEMY_SKILLS)
        if isinstance(skills, dict):
            for skill_name in normalized:
                try:
                    normalized[skill_name] = max(0, int(skills.get(skill_name, normalized[skill_name])))
                except (TypeError, ValueError):
                    pass
        return normalized

    def _max_enemy_abilities(self, level: int) -> int:
        if level <= 1:
            return 1
        if level <= 3:
            return 2
        return 3

    def _enemy_family(self, family: str) -> str:
        normalized = self._normalize_key(family)
        return self.FAMILY_ALIASES.get(normalized, normalized)

    def _type_definition(self, class_type: str) -> dict:
        return self.TYPE_LIBRARY.get(self._normalize_key(class_type), {})

    def _resolve_enemy_abilities(self, family: str, class_type: str, level: int, requested: list | None) -> list[dict]:
        family_def = self.FAMILY_LIBRARY.get(family, {})
        type_def = self._type_definition(class_type)
        family_allowed = [self._normalize_key(ability_id) for ability_id in family_def.get("allowed_abilities", [])]
        type_allowed = [self._normalize_key(ability_id) for ability_id in type_def.get("allowed_abilities", [])]
        preferred = [self._normalize_key(ability_id) for ability_id in type_def.get("preferred_abilities", [])]
        allowed = [ability_id for ability_id in family_allowed if not type_allowed or ability_id in type_allowed]
        if not allowed:
            allowed = family_allowed or type_allowed
        max_abilities = self._max_enemy_abilities(level)
        resolved_ids = []

        for raw_ability in requested if isinstance(requested, list) else []:
            ability_id = self._normalize_key(raw_ability)
            ability = self.ENEMY_ABILITIES.get(ability_id)
            if not ability or ability_id not in allowed or level < int(ability.get("min_level", 1)):
                continue
            if ability_id not in resolved_ids:
                resolved_ids.append(ability_id)
            if len(resolved_ids) >= max_abilities:
                break

        fallback_order = preferred + [ability_id for ability_id in allowed if ability_id not in preferred]
        if not resolved_ids:
            for ability_id in fallback_order:
                ability = self.ENEMY_ABILITIES.get(ability_id)
                if not ability or level < int(ability.get("min_level", 1)):
                    continue
                resolved_ids.append(ability_id)
                if len(resolved_ids) >= max_abilities:
                    break

        return [{"id": ability_id, **self.ENEMY_ABILITIES[ability_id]} for ability_id in resolved_ids]

    def _enemy_profile(self, enemy_id: str, enemy_data: dict) -> dict:
        family = self._enemy_family(enemy_data.get("family", ""))
        class_type = self._normalize_key(enemy_data.get("class_type", "")) or "foe"
        level = max(1, int(enemy_data.get("level", 1)))
        stats = self._normalized_enemy_stats(enemy_data.get("stats", {}))
        skills = self._normalized_enemy_skills(enemy_data.get("skills", {}))
        abilities = self._resolve_enemy_abilities(family, class_type, level, enemy_data.get("abilities", []))
        focus_max = max(
            0,
            int(enemy_data.get("focus", 2 + level + max(0, self._stat_modifier(stats["mind"])))),
        )
        return {
            "id": enemy_id,
            "name": str(enemy_data.get("name", enemy_id)),
            "family": family,
            "class_type": class_type,
            "level": level,
            "stats": stats,
            "skills": skills,
            "abilities": abilities,
            "focus_max": focus_max,
        }

    def preview_enemy(self, enemy_id: str, enemy_data: dict) -> dict:
        return self._enemy_profile(enemy_id, enemy_data)

    def _enemy_stat_value(self, profile: dict, stat_name: str) -> int:
        return int(profile["stats"].get(stat_name, self.DEFAULT_ENEMY_STATS.get(stat_name, 10)))

    def _enemy_stat_modifier(self, profile: dict, stat_name: str) -> int:
        return self._stat_modifier(self._enemy_stat_value(profile, stat_name))

    def _enemy_skill(self, profile: dict, skill_name: str) -> int:
        return max(0, int(profile["skills"].get(skill_name, 0)))

    def _enemy_attack_stat(self, profile: dict) -> str:
        class_type = profile.get("class_type", "")
        family = profile.get("family", "")
        type_attack_stat = self._normalize_key(self._type_definition(class_type).get("attack_stat", ""))
        if type_attack_stat in self.DEFAULT_ENEMY_STATS:
            return type_attack_stat
        if family in {"shrine_creatures"} and self._enemy_skill(profile, "spellcasting") >= self._enemy_skill(profile, "swordsmanship"):
            return "mind"
        if class_type in {"hexer", "ember_spirit"}:
            return "mind"
        if class_type in {"hunter", "pack_hunter", "alpha_hunter", "ambusher", "skirmisher"}:
            return "agility"
        return "strength"

    def _enemy_basic_skill(self, profile: dict) -> str:
        type_skills = [
            self._normalize_key(skill_name)
            for skill_name in self._type_definition(profile.get("class_type", "")).get("skill_focus", [])
            if self._normalize_key(skill_name) in self.DEFAULT_ENEMY_SKILLS
        ]
        if type_skills:
            return max(type_skills, key=lambda skill_name: (self._enemy_skill(profile, skill_name), -type_skills.index(skill_name)))
        candidates = ("swordsmanship", "archery", "spellcasting", "defense")
        return max(candidates, key=lambda skill_name: (self._enemy_skill(profile, skill_name), -candidates.index(skill_name)))

    def _enemy_dodge_score(self, profile: dict, enemy_state: dict) -> int:
        return (
            max(0, self._enemy_stat_modifier(profile, "agility"))
            + (self._enemy_skill(profile, "stealth") // 2)
            + int(enemy_state.get("dodge_bonus", 0))
        )

    def _enemy_defense_value(self, profile: dict, enemy_defense: int, enemy_state: dict, behavior: str) -> int:
        defense = (
            enemy_defense
            + max(0, self._enemy_stat_modifier(profile, "endurance"))
            + (self._enemy_skill(profile, "defense") // 2)
            + self._enemy_dodge_score(profile, enemy_state)
            + int(enemy_state.get("defense_bonus", 0))
        )
        if behavior == "defensive":
            defense += 1
        return max(5, defense)

    def _enemy_resilience(self, profile: dict, enemy_state: dict) -> int:
        return (
            max(0, self._enemy_stat_modifier(profile, "vitality"))
            + max(0, self._enemy_stat_modifier(profile, "endurance"))
            + (self._enemy_skill(profile, "defense") // 2)
            + (int(enemy_state.get("defense_bonus", 0)) // 2)
        )

    def _enemy_crit_chance(self, profile: dict, stat_name: str, enemy_state: dict) -> int:
        agility_bonus = max(0, self._enemy_stat_modifier(profile, "agility"))
        attack_bonus = max(0, self._enemy_stat_modifier(profile, stat_name))
        luck_bonus = max(0, self._enemy_stat_modifier(profile, "luck"))
        return min(25, 4 + (agility_bonus * 2) + (attack_bonus * 2) + luck_bonus + int(enemy_state.get("crit_bonus", 0)))

    @staticmethod
    def _crit_threshold(chance: int) -> int:
        steps = max(1, int(chance) // 5)
        return max(16, 21 - steps)

    def _enemy_basic_attack_modifier(self, profile: dict, enemy_attack: int, enemy_state: dict, player: Character, behavior: str) -> int:
        attack_stat = self._enemy_attack_stat(profile)
        modifier = (
            enemy_attack
            + max(0, self._enemy_stat_modifier(profile, attack_stat))
            + (self._enemy_skill(profile, self._enemy_basic_skill(profile)) // 2)
            + int(enemy_state.get("attack_bonus", 0))
        )
        if behavior == "aggressive":
            modifier += 1
        elif behavior == "defensive":
            modifier = max(1, modifier - 1)
        elif behavior == "hunter" and player.hp <= max(1, player.max_hp // 2):
            modifier += 1
        modifier -= int(player.combat_boosts.get("enemy_attack_penalty", 0))
        return max(1, modifier)

    def _enemy_basic_damage(self, profile: dict, enemy_attack: int, enemy_state: dict) -> int:
        attack_stat = self._enemy_attack_stat(profile)
        damage = (
            enemy_attack
            + max(0, self._enemy_stat_modifier(profile, attack_stat))
            + int(enemy_state.get("damage_bonus", 0))
        )
        return max(1, damage)

    def _enemy_ability_scale_bonus(self, profile: dict, effect: dict) -> int:
        scale_stat = self._normalize_key(effect.get("scale_stat", ""))
        scale_skill = self._normalize_key(effect.get("scale_skill", ""))
        total = 0
        if scale_stat in self.DEFAULT_ENEMY_STATS:
            total += max(0, self._enemy_stat_modifier(profile, scale_stat))
        if scale_skill in self.DEFAULT_ENEMY_SKILLS:
            total += self._enemy_skill(profile, scale_skill) // 2
        return total

    def _enemy_ability_accuracy(self, profile: dict, effect: dict, enemy_attack: int, enemy_state: dict) -> int:
        scale_stat = self._normalize_key(effect.get("scale_stat", self._enemy_attack_stat(profile)))
        scale_skill = self._normalize_key(effect.get("scale_skill", self._enemy_basic_skill(profile)))
        accuracy = enemy_attack + max(0, self._enemy_stat_modifier(profile, scale_stat)) + int(effect.get("accuracy_bonus", 0))
        if scale_skill in self.DEFAULT_ENEMY_SKILLS:
            accuracy += self._enemy_skill(profile, scale_skill) // 2
        accuracy += int(enemy_state.get("attack_bonus", 0))
        return max(1, accuracy)

    def _apply_enemy_buff(self, enemy_state: dict, buff: dict) -> str:
        if not isinstance(buff, dict):
            return ""
        labels = {
            "attack_bonus": "Accuracy",
            "damage_bonus": "Damage",
            "defense_bonus": "Defense",
            "dodge_bonus": "Dodge",
            "crit_bonus": "Crit",
        }
        parts = []
        for key, amount in buff.items():
            if key not in enemy_state:
                continue
            enemy_state[key] += int(amount)
            sign = "+" if int(amount) >= 0 else ""
            if key == "dodge_bonus":
                parts.append(f"{sign}{int(amount) * 5}% {labels[key]}")
            elif key == "crit_bonus":
                parts.append(f"{sign}{int(amount)}% {labels[key]}")
            else:
                parts.append(f"{sign}{int(amount)} {labels[key]}")
        return ", ".join(parts)

    def _apply_player_penalties(self, player_state: dict, effect: dict) -> str:
        mapping = {
            "target_attack_penalty": ("attack_penalty", "player Accuracy"),
            "target_defense_penalty": ("defense_penalty", "player Defense"),
            "target_dodge_penalty": ("dodge_penalty", "player Dodge"),
        }
        parts = []
        for effect_key, (state_key, label) in mapping.items():
            amount = int(effect.get(effect_key, 0))
            if not amount:
                continue
            player_state[state_key] += amount
            sign = "-" if amount > 0 else "+"
            if state_key == "dodge_penalty":
                parts.append(f"{sign}{abs(amount) * 5}% {label}")
            else:
                parts.append(f"{sign}{abs(amount)} {label}")
        return ", ".join(parts)

    def _available_enemy_abilities(self, profile: dict, enemy_focus: int) -> list[dict]:
        return [ability for ability in profile["abilities"] if int(ability.get("cost", 0)) <= enemy_focus]

    def _select_enemy_ability(
        self,
        profile: dict,
        behavior: str,
        enemy_hp: int,
        enemy_max_hp: int,
        enemy_focus: int,
        enemy_state: dict,
        turn: int,
    ) -> dict | None:
        available = self._available_enemy_abilities(profile, enemy_focus)
        if not available:
            return None

        for ability in available:
            if ability.get("kind") != "self_buff":
                continue
            if ability["id"] in enemy_state["used_buffs"]:
                continue
            if turn == 1 or (enemy_hp * 2 <= enemy_max_hp and behavior == "defensive"):
                return ability

        if turn % 2 == 0:
            for ability in available:
                if ability.get("kind") == "hybrid":
                    return ability

        damaging = [ability for ability in available if int(ability.get("damage", 0)) > 0]
        if damaging:
            damaging = sorted(
                damaging,
                key=lambda ability: (int(ability.get("damage", 0)), int(ability.get("accuracy_bonus", 0)), int(ability.get("cost", 0))),
                reverse=True,
            )
            return damaging[(turn - 1) % len(damaging)]

        return available[0]

    def _basic_enemy_attack(
        self,
        player: Character,
        profile: dict,
        enemy_name: str,
        enemy_attack: int,
        items_data: dict,
        enemy_state: dict,
        player_state: dict,
        behavior: str,
        turn: int,
    ) -> str:
        modifier = self._enemy_basic_attack_modifier(profile, enemy_attack, enemy_state, player, behavior)
        player_defense = max(
            5,
            player.defense_value(items_data) - int(player_state.get("defense_penalty", 0)) - int(player_state.get("dodge_penalty", 0)),
        )
        roll = self.dice.roll_d20(modifier)
        if roll["total"] < player_defense:
            return (
                f"Turn {turn}: {enemy_name} rolls {roll['die']} + {roll['modifier']} = {roll['total']} "
                f"against your DEF {player_defense} and misses."
            )

        damage = max(1, self._enemy_basic_damage(profile, enemy_attack, enemy_state) - player.resilience_value())
        critical = roll["die"] >= self._crit_threshold(self._enemy_crit_chance(profile, self._enemy_attack_stat(profile), enemy_state))
        if critical:
            damage += max(1, damage // 2)
        player.hp = max(0, player.hp - damage)
        crit_text = " Critical hit." if critical else ""
        return (
            f"Turn {turn}: {enemy_name} rolls {roll['die']} + {roll['modifier']} = {roll['total']} "
            f"against your DEF {player_defense} and hits for {damage} damage "
            f"(your HP: {player.hp}/{player.max_hp}).{crit_text}"
        )

    def _enemy_ability_action(
        self,
        player: Character,
        profile: dict,
        enemy_name: str,
        enemy_attack: int,
        items_data: dict,
        enemy_state: dict,
        player_state: dict,
        behavior: str,
        enemy_focus: int,
        turn: int,
    ) -> tuple[str, int]:
        ability = self._select_enemy_ability(profile, behavior, enemy_state["hp"], enemy_state["max_hp"], enemy_focus, enemy_state, turn)
        if not ability:
            return self._basic_enemy_attack(player, profile, enemy_name, enemy_attack, items_data, enemy_state, player_state, behavior, turn), enemy_focus

        enemy_focus -= int(ability.get("cost", 0))
        effect = ability

        if ability.get("kind") == "self_buff":
            buff_summary = self._apply_enemy_buff(enemy_state, effect.get("buff", {}))
            enemy_state["used_buffs"].add(ability["id"])
            if buff_summary:
                return f"Turn {turn}: {enemy_name} uses {ability['name']} and prepares itself ({buff_summary}).", enemy_focus
            return f"Turn {turn}: {enemy_name} uses {ability['name']}.", enemy_focus

        attack_stat = self._normalize_key(effect.get("scale_stat", self._enemy_attack_stat(profile)))
        accuracy = self._enemy_ability_accuracy(profile, effect, enemy_attack, enemy_state) - int(player.combat_boosts.get("enemy_attack_penalty", 0))
        if behavior == "aggressive":
            accuracy += 1
        elif behavior == "defensive":
            accuracy = max(1, accuracy - 1)

        player_defense = max(
            5,
            player.defense_value(items_data) - int(player_state.get("defense_penalty", 0)) - int(player_state.get("dodge_penalty", 0)),
        )
        roll = self.dice.roll_d20(max(1, accuracy))
        if roll["total"] < player_defense:
            return (
                f"Turn {turn}: {enemy_name} uses {ability['name']} but rolls {roll['die']} + {roll['modifier']} = {roll['total']} "
                f"against your DEF {player_defense} and fails to connect."
            ), enemy_focus

        base_damage = max(0, int(effect.get("damage", 0)) + self._enemy_ability_scale_bonus(profile, effect) + int(enemy_state.get("damage_bonus", 0)))
        critical = base_damage > 0 and roll["die"] >= self._crit_threshold(self._enemy_crit_chance(profile, attack_stat, enemy_state) + int(effect.get("crit_bonus", 0)))
        if critical:
            base_damage += max(1, base_damage // 2)
        damage = max(1, base_damage - player.resilience_value()) if base_damage > 0 else 0
        if damage > 0:
            player.hp = max(0, player.hp - damage)

        buff_summary = self._apply_enemy_buff(enemy_state, effect.get("buff", {}))
        penalty_summary = self._apply_player_penalties(player_state, effect)
        details = []
        if damage > 0:
            details.append(f"hits for {damage} damage")
        if buff_summary:
            details.append(buff_summary)
            enemy_state["used_buffs"].add(ability["id"])
        if penalty_summary:
            details.append(penalty_summary)
        detail_text = "; ".join(details) if details else "has an effect"
        crit_text = " Critical hit." if critical else ""
        return (
            f"Turn {turn}: {enemy_name} uses {ability['name']} and rolls {roll['die']} + {roll['modifier']} = {roll['total']} "
            f"against your DEF {player_defense}; {detail_text} (your HP: {player.hp}/{player.max_hp}).{crit_text}"
        ), enemy_focus

    def fight(
        self,
        player: Character,
        enemy_id: str,
        enemies_data: dict,
        items_data: dict,
        starting_enemy_hp: int | None = None,
    ) -> dict:
        enemy_data = enemies_data.get(enemy_id)
        if not enemy_data:
            return {
                "victory": False,
                "enemy_id": enemy_id,
                "enemy_name": enemy_id,
                "log": ["No such enemy."],
                "loot": [],
                "enemy_hp": 0,
            }

        profile = self._enemy_profile(enemy_id, enemy_data)
        enemy_max_hp = max(1, int(enemy_data.get("hp", 1)))
        enemy_hp = enemy_max_hp
        if starting_enemy_hp is not None:
            enemy_hp = max(0, min(enemy_max_hp, int(starting_enemy_hp)))
        enemy_attack = int(enemy_data.get("attack", 1))
        enemy_defense = int(enemy_data.get("defense", self.DEFAULT_ENEMY_DEFENSE))
        enemy_name = str(enemy_data.get("name", enemy_id))
        behavior = str(enemy_data.get("behavior", "aggressive")).strip().lower()
        xp_reward = int(enemy_data.get("xp", max(5, enemy_hp * 5)))

        log = []
        turn = 1
        enemy_fled = False
        enemy_focus = int(profile.get("focus_max", 0))
        enemy_state = {
            "hp": enemy_hp,
            "max_hp": enemy_max_hp,
            "attack_bonus": 0,
            "damage_bonus": 0,
            "defense_bonus": 0,
            "dodge_bonus": 0,
            "crit_bonus": 0,
            "used_buffs": set(),
        }
        player_state = {
            "attack_penalty": 0,
            "defense_penalty": 0,
            "dodge_penalty": 0,
        }

        while player.is_alive() and enemy_hp > 0:
            player_attack = max(1, player.attack_value(items_data))
            player_attack_modifier = max(1, player.attack_roll_modifier(items_data) - int(player_state.get("attack_penalty", 0)))
            player_roll = self.dice.roll_d20(player_attack_modifier)
            effective_enemy_defense = self._enemy_defense_value(profile, enemy_defense, enemy_state, behavior)
            effective_enemy_defense = max(5, effective_enemy_defense - int(player.combat_boosts.get("enemy_defense_penalty", 0)))
            if player_roll["total"] >= effective_enemy_defense:
                player_damage = max(1, player_attack - self._enemy_resilience(profile, enemy_state))
                critical_hit = player_roll["die"] >= player.crit_threshold(items_data)
                if critical_hit:
                    player_damage = player.critical_damage(player_damage)
                enemy_hp = max(0, enemy_hp - player_damage)
                enemy_state["hp"] = enemy_hp
                crit_text = " Critical hit." if critical_hit else ""
                log.append(
                    f"Turn {turn}: You roll {player_roll['die']} + {player_roll['modifier']} = {player_roll['total']} "
                    f"against {enemy_name} DEF {effective_enemy_defense} and hit for {player_damage} damage "
                    f"(enemy HP: {enemy_hp}).{crit_text}"
                )
            else:
                log.append(
                    f"Turn {turn}: You roll {player_roll['die']} + {player_roll['modifier']} = {player_roll['total']} "
                    f"against {enemy_name} DEF {effective_enemy_defense} and miss."
                )

            if enemy_hp <= 0:
                break

            if behavior == "cowardly" and enemy_hp <= max(1, int(enemy_state["max_hp"] * 0.3)):
                enemy_fled = True
                log.append(f"Turn {turn}: {enemy_name} breaks and flees.")
                break

            enemy_line, enemy_focus = self._enemy_ability_action(
                player,
                profile,
                enemy_name,
                enemy_attack,
                items_data,
                enemy_state,
                player_state,
                behavior,
                enemy_focus,
                turn,
            )
            log.append(enemy_line)
            turn += 1

        victory = enemy_hp <= 0 and player.is_alive()
        loot = enemy_data.get("loot", []) if victory else []

        return {
            "victory": victory,
            "enemy_fled": enemy_fled,
            "enemy_id": enemy_id,
            "enemy_name": enemy_name,
            "behavior": behavior,
            "log": log,
            "loot": loot,
            "enemy_hp": max(0, enemy_hp),
            "xp_reward": xp_reward if victory else 0,
            "enemy_abilities": [ability["name"] for ability in profile["abilities"]],
            "enemy_level": profile["level"],
            "enemy_family": profile["family"],
        }
