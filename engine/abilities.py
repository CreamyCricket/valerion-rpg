class AbilityEngine:
    """Provides deterministic ability metadata; the game engine applies the actual effects."""

    QUERY_ALIASES = {
        "second_wind": "guard_stance",
        "spark": "firebolt",
        "mend": "healing_light",
        "cunning_strike": "backstab",
    }

    ABILITIES = {
        "power_strike": {
            "name": "Power Strike",
            "kind": "ability",
            "target": "enemy",
            "cost": 2,
            "effect": {
                "damage": 4,
                "scale_stat": "strength",
                "scale_skill": "athletics",
                "accuracy_bonus": 1,
            },
            "description": "A heavy opening blow that scales with Strength and a trained body.",
        },
        "guard_stance": {
            "name": "Guard Stance",
            "kind": "ability",
            "target": "self",
            "cost": 2,
            "effect": {
                "buff": {
                    "defense_bonus": 2,
                    "dodge_bonus": 1,
                }
            },
            "description": "Prepare for the next fight with a tighter guard and steadier footing.",
        },
        "aimed_shot": {
            "name": "Aimed Shot",
            "kind": "ability",
            "target": "enemy",
            "cost": 2,
            "effect": {
                "damage": 3,
                "scale_stat": "agility",
                "scale_skill": "survival",
                "accuracy_bonus": 2,
                "crit_bonus": 10,
            },
            "description": "Loose a careful opening shot with better accuracy and critical pressure.",
        },
        "track_prey": {
            "name": "Track Prey",
            "kind": "ability",
            "target": "enemy",
            "cost": 2,
            "effect": {
                "buff": {
                    "attack_bonus": 2,
                    "damage_bonus": 1,
                    "crit_bonus": 5,
                    "enemy_defense_penalty": 1,
                },
                "reveal_enemy": True,
            },
            "description": "Read the target's movement and carry that advantage into the fight.",
        },
        "firebolt": {
            "name": "Firebolt",
            "kind": "spell",
            "target": "enemy",
            "cost": 3,
            "effect": {
                "damage": 5,
                "scale_stat": "mind",
                "scale_skill": "arcana",
                "accuracy_bonus": 1,
            },
            "description": "Send a sharp bolt of fire that scales with Mind and arcane training.",
        },
        "frost_shard": {
            "name": "Frost Shard",
            "kind": "spell",
            "target": "enemy",
            "cost": 3,
            "effect": {
                "damage": 3,
                "scale_stat": "mind",
                "scale_skill": "arcana",
                "buff": {
                    "enemy_attack_penalty": 2,
                },
                "accuracy_bonus": 1,
            },
            "description": "Strike with cold magic and blunt the enemy's attack for the coming clash.",
        },
        "healing_light": {
            "name": "Healing Light",
            "kind": "spell",
            "target": "self",
            "cost": 3,
            "effect": {
                "heal": 6,
                "scale_stat": "mind",
                "scale_skill": "lore",
            },
            "description": "Gather light into a steady restoration shaped by Mind and lore.",
        },
        "backstab": {
            "name": "Backstab",
            "kind": "ability",
            "target": "enemy",
            "cost": 2,
            "effect": {
                "damage": 4,
                "scale_stat": "agility",
                "scale_skill": "stealth",
                "accuracy_bonus": 2,
                "crit_bonus": 15,
            },
            "description": "Exploit a brief opening for a fast, high-pressure strike.",
        },
        "smoke_step": {
            "name": "Smoke Step",
            "kind": "ability",
            "target": "self",
            "cost": 2,
            "effect": {
                "buff": {
                    "dodge_bonus": 2,
                    "crit_bonus": 10,
                    "attack_bonus": 1,
                }
            },
            "description": "Break the enemy's read on you and enter the next fight harder to pin down.",
        },
    }

    @classmethod
    def available_to(cls, player) -> list[dict]:
        abilities = []
        for ability_id in getattr(player, "abilities", []):
            normalized_id = str(ability_id).strip().lower()
            ability = cls.ABILITIES.get(normalized_id)
            if not ability:
                continue
            abilities.append({"id": normalized_id, **ability})
        return abilities

    @classmethod
    def normalize_query(cls, query: str) -> str:
        normalized = str(query or "").strip().lower().replace("-", "_").replace(" ", "_")
        return cls.QUERY_ALIASES.get(normalized, normalized)

    @classmethod
    def find_for_player(cls, player, query: str) -> dict | None:
        normalized = cls.normalize_query(query)
        if not normalized:
            return None

        for ability in cls.available_to(player):
            if normalized == ability["id"]:
                return ability
            name_normalized = ability["name"].strip().lower().replace("-", "_").replace(" ", "_")
            if normalized == name_normalized:
                return ability
        return None

    @classmethod
    def parse_player_input(cls, player, raw_text: str) -> tuple[dict | None, str]:
        normalized_text = str(raw_text or "").strip().lower()
        if not normalized_text:
            return None, ""

        for ability in cls.available_to(player):
            prefixes = [
                ability["id"].replace("_", " "),
                ability["name"].strip().lower(),
            ]
            for prefix in prefixes:
                if normalized_text == prefix:
                    return ability, ""
                if normalized_text.startswith(prefix + " "):
                    return ability, normalized_text[len(prefix):].strip()

        alias_match = cls.find_for_player(player, raw_text)
        return alias_match, ""
