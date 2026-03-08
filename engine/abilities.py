class AbilityEngine:
    """Provides deterministic ability metadata; the game engine applies the actual effects."""

    ABILITIES = {
        "second_wind": {
            "name": "Second Wind",
            "kind": "ability",
            "target": "self",
            "cost": 2,
            "effect": {"heal": 6},
            "description": "Recover your footing and restore a small amount of HP.",
        },
        "aimed_shot": {
            "name": "Aimed Shot",
            "kind": "ability",
            "target": "enemy",
            "cost": 2,
            "effect": {"damage": 4},
            "description": "Make a careful opening strike before the fight closes in.",
        },
        "spark": {
            "name": "Spark",
            "kind": "spell",
            "target": "enemy",
            "cost": 3,
            "effect": {"damage": 6},
            "description": "Release a small bolt of focused magic at a visible enemy.",
        },
        "mend": {
            "name": "Mend",
            "kind": "spell",
            "target": "self",
            "cost": 2,
            "effect": {"heal": 5},
            "description": "Draw on focus to restore a small amount of HP.",
        },
        "cunning_strike": {
            "name": "Cunning Strike",
            "kind": "ability",
            "target": "enemy",
            "cost": 2,
            "effect": {"damage": 5},
            "description": "Exploit a brief opening for reliable early damage.",
        },
    }

    @classmethod
    def available_to(cls, player) -> list[dict]:
        abilities = []
        for ability_id in getattr(player, "abilities", []):
            ability = cls.ABILITIES.get(str(ability_id).strip().lower())
            if not ability:
                continue
            abilities.append({"id": str(ability_id).strip().lower(), **ability})
        return abilities

    @classmethod
    def find_for_player(cls, player, query: str) -> dict | None:
        normalized = str(query or "").strip().lower().replace("-", "_").replace(" ", "_")
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
        return cls.find_for_player(player, raw_text), ""
