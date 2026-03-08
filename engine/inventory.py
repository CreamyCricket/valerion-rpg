from player.character import Character


class InventoryEngine:
    SHOP_PRICES = {"potion": 5}

    """Manages deterministic add/use behavior without hidden randomness."""

    @staticmethod
    def _fallback_name(item_id: str) -> str:
        return item_id.replace("_", " ").title()

    @staticmethod
    def _item_effect_bonus(item: dict, prefix: str) -> int:
        effect = str(item.get("effect", ""))
        if effect.startswith(prefix):
            try:
                return int(effect.split("_")[-1])
            except ValueError:
                return 0
        return 0

    def add_item(self, player: Character, item_id: str) -> None:
        player.inventory.append(item_id)

    @staticmethod
    def item_rarity(item: dict) -> str:
        return str(item.get("rarity", "common")).strip().title() or "Common"

    @classmethod
    def item_bonus_parts(cls, item: dict) -> list[str]:
        parts = []
        attack_bonus = int(item.get("attack_bonus", cls._item_effect_bonus(item, "attack_plus_")))
        defense_bonus = int(item.get("defense_bonus", cls._item_effect_bonus(item, "defense_plus_")))
        if attack_bonus:
            parts.append(f"ATK +{attack_bonus}")
        if defense_bonus:
            parts.append(f"DEF +{defense_bonus}")
        stat_bonuses = item.get("stat_bonuses", {})
        if isinstance(stat_bonuses, dict):
            for stat_name, amount in stat_bonuses.items():
                if int(amount):
                    parts.append(f"{str(stat_name).title()} +{int(amount)}")
        skill_bonuses = item.get("skill_bonuses", {})
        if isinstance(skill_bonuses, dict):
            for skill_name, amount in skill_bonuses.items():
                if int(amount):
                    parts.append(f"{str(skill_name).replace('_', ' ').title()} +{int(amount)}")
        for field, label in (
            ("crit_bonus", "Crit"),
            ("dodge_bonus", "Dodge"),
            ("spell_power_bonus", "Spell"),
            ("magic_guard_bonus", "Guard"),
        ):
            amount = int(item.get(field, 0))
            if amount:
                suffix = "%" if field in {"crit_bonus"} else ""
                parts.append(f"{label} +{amount}{suffix}")
        return parts

    @classmethod
    def item_label(cls, item_id: str, items_data: dict) -> str:
        item = items_data.get(item_id, {})
        item_name = item.get("name", cls._fallback_name(item_id))
        rarity = cls.item_rarity(item)
        tier = str(item.get("tier", "")).strip()
        tier_text = f" T{tier}" if tier else ""
        return f"{item_name} [{rarity}{tier_text}]"

    @classmethod
    def item_shop_line(cls, item_id: str, items_data: dict, price: int) -> str:
        item = items_data.get(item_id, {})
        item_type = item.get("type", "item")
        bonus_parts = cls.item_bonus_parts(item)
        bonus_text = " | " + ", ".join(bonus_parts) if bonus_parts else ""
        return f"- {cls.item_label(item_id, items_data)} ({item_type}){bonus_text} - {price} gold"

    def find_item_in_inventory(self, player: Character, items_data: dict, query: str) -> str | None:
        query = query.strip().lower()
        for item_id in player.inventory:
            item = items_data.get(item_id, {})
            if query == item_id.lower() or query == item.get("name", "").lower():
                return item_id
        return None

    def inventory_lines(self, player: Character, items_data: dict) -> list[str]:
        if not player.inventory:
            return ["Backpack: empty", "Equipped weapon: none", "Equipped armor: none"]

        lines = ["Backpack:"]
        for index, item_id in enumerate(player.inventory, start=1):
            item = items_data.get(item_id, {})
            item_name = self.item_label(item_id, items_data)
            item_type = item.get("type", "unknown")
            bonus_parts = self.item_bonus_parts(item)
            equipped_tags = []
            if item_id == player.equipped_weapon:
                equipped_tags.append("weapon")
            if item_id == getattr(player, "equipped_armor", None):
                equipped_tags.append("armor")
            equipped_tag = f" [{' & '.join(equipped_tags)}]" if equipped_tags else ""
            bonus_text = f" | {', '.join(bonus_parts)}" if bonus_parts else ""
            lines.append(f"{index}. {item_name} ({item_type}){equipped_tag}{bonus_text}")
        equipped_name = "none"
        if player.equipped_weapon:
            equipped_name = self.item_label(player.equipped_weapon, items_data)
        equipped_armor_name = "none"
        if getattr(player, "equipped_armor", None):
            equipped_armor_name = self.item_label(player.equipped_armor, items_data)
        lines.append(f"Equipped weapon: {equipped_name}")
        lines.append(f"Equipped armor: {equipped_armor_name}")
        return lines

    def use_item(self, player: Character, item_id: str, items_data: dict) -> str:
        item = items_data.get(item_id, {})
        item_name = item.get("name", self._fallback_name(item_id))
        item_type = item.get("type", "")
        effect = item.get("effect", "")

        if item_type == "consumable":
            if effect.startswith("heal_"):
                try:
                    amount = int(effect.split("_")[-1])
                except ValueError:
                    return f"{item_name} cannot be used because its heal value is invalid."
                healed = player.heal(amount)
                player.inventory.remove(item_id)
                if healed == 0:
                    return (
                        f"You used {item_name}, but your HP was already full "
                        f"(HP: {player.hp}/{player.max_hp})."
                    )
                return f"You used {item_name}. Healed {healed} HP. HP is now {player.hp}/{player.max_hp}."
            if effect.startswith("focus_"):
                try:
                    amount = int(effect.split("_")[-1])
                except ValueError:
                    return f"{item_name} cannot be used because its focus value is invalid."
                restored = player.restore_focus(amount)
                player.inventory.remove(item_id)
                if restored == 0:
                    return (
                        f"You used {item_name}, but your focus was already full "
                        f"(Focus: {player.focus}/{player.max_focus})."
                    )
                return (
                    f"You used {item_name}. Restored {restored} focus. "
                    f"Focus is now {player.focus}/{player.max_focus}."
                )
            return f"{item_name} cannot be used right now."

        if item_type == "weapon":
            if player.equipped_weapon == item_id:
                attack_value = player.attack_value(items_data)
                return f"{item_name} is already equipped. Attack is {attack_value}."
            player.equipped_weapon = item_id
            attack_value = player.attack_value(items_data)
            bonus_parts = self.item_bonus_parts(item)
            bonus_text = " Bonuses: " + ", ".join(bonus_parts) + "." if bonus_parts else ""
            return f"You equipped {self.item_label(item_id, items_data)}. Attack is now {attack_value}.{bonus_text}"

        if item_type == "armor":
            if getattr(player, "equipped_armor", None) == item_id:
                defense_value = player.defense_value(items_data)
                return f"{item_name} is already equipped. Defense is {defense_value}."
            player.equipped_armor = item_id
            defense_value = player.defense_value(items_data)
            bonus_parts = self.item_bonus_parts(item)
            bonus_text = " Bonuses: " + ", ".join(bonus_parts) + "." if bonus_parts else ""
            return f"You equipped {self.item_label(item_id, items_data)}. Defense is now {defense_value}.{bonus_text}"

        return f"{item_name} is not a usable item."

    def resolve_shop_item(self, items_data: dict, query: str, stock: list[str] | None = None) -> str | None:
        normalized = query.strip().lower()
        item_ids = stock if isinstance(stock, list) else list(self.SHOP_PRICES.keys())
        for item_id in item_ids:
            item_name = items_data.get(item_id, {}).get("name", "").lower()
            if normalized == item_id.lower() or normalized == item_name:
                return item_id
        return None

    def item_price(self, item_id: str, items_data: dict) -> int:
        if item_id in self.SHOP_PRICES:
            return int(self.SHOP_PRICES[item_id])
        item = items_data.get(item_id, {})
        return max(1, int(item.get("price", 1)))

    def sell_price(self, item_id: str, items_data: dict) -> int:
        return max(1, self.item_price(item_id, items_data) // 2)

    def buy_item(
        self,
        player: Character,
        item_id: str,
        items_data: dict,
        cost_override: int | None = None,
        seller_name: str = "Merchant",
        stock: list[str] | None = None,
    ) -> tuple[bool, str]:
        if isinstance(stock, list) and item_id not in stock:
            return False, f"{seller_name}: That item is not sold here."
        if item_id not in items_data:
            return False, f"{seller_name}: That item does not exist."

        cost = int(cost_override) if cost_override is not None else self.item_price(item_id, items_data)
        item_name = items_data.get(item_id, {}).get("name", self._fallback_name(item_id))

        if player.gold < cost:
            return (
                False,
                f"{seller_name}: You need {cost} gold for {item_name}, but you only have {player.gold} gold.",
            )

        player.gold -= cost
        player.inventory.append(item_id)
        return True, f"{seller_name}: Sold 1 {item_name} for {cost} gold. Gold left: {player.gold}."

    def sell_item(
        self,
        player: Character,
        item_id: str,
        items_data: dict,
        value_override: int | None = None,
        buyer_name: str = "Merchant",
    ) -> tuple[bool, str]:
        if item_id not in player.inventory:
            return False, f"{buyer_name}: You do not have that item."
        if item_id not in items_data:
            return False, f"{buyer_name}: That item does not exist."

        value = int(value_override) if value_override is not None else self.sell_price(item_id, items_data)
        item_name = items_data.get(item_id, {}).get("name", self._fallback_name(item_id))

        player.inventory.remove(item_id)
        if player.equipped_weapon == item_id:
            player.equipped_weapon = None
        if getattr(player, "equipped_armor", None) == item_id:
            player.equipped_armor = None
        player.gold += value
        return True, f"{buyer_name}: Bought 1 {item_name} for {value} gold. Gold now: {player.gold}."
