from player.character import Character


class InventoryEngine:
    SHOP_PRICES = {"potion": 5}
    RARITY_COST_STEPS = {"common": 0, "uncommon": 1, "rare": 2, "epic": 3, "relic": 4}
    STACKABLE_TYPES = {"consumable", "loot"}

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

    @classmethod
    def item_type(cls, item_id: str, items_data: dict) -> str:
        return str(items_data.get(item_id, {}).get("type", "item")).strip().lower()

    @classmethod
    def is_stackable(cls, item_id: str, items_data: dict) -> bool:
        return cls.item_type(item_id, items_data) in cls.STACKABLE_TYPES

    def carry_load(self, player: Character, items_data: dict) -> int:
        load = 0
        counted_stacks = set()
        for item_id in player.inventory:
            normalized_item = str(item_id).strip().lower()
            if self.is_stackable(normalized_item, items_data):
                if normalized_item in counted_stacks:
                    continue
                counted_stacks.add(normalized_item)
            load += 1
        return load

    def carry_status_line(self, player: Character, items_data: dict) -> str:
        load = self.carry_load(player, items_data)
        capacity = player.carry_capacity()
        if load <= capacity:
            return ""
        return (
            f"Carry status: overloaded ({load}/{capacity}). "
            "Loot and consumables stack into one slot each, but new item types and gear still take space."
        )

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
    def item_label(cls, item_id: str, items_data: dict, upgrade_level: int = 0) -> str:
        item = items_data.get(item_id, {})
        item_name = item.get("name", cls._fallback_name(item_id))
        rarity = cls.item_rarity(item)
        tier = str(item.get("tier", "")).strip()
        tier_text = f" T{tier}" if tier else ""
        upgrade_text = f" +{int(upgrade_level)}" if int(upgrade_level) > 0 else ""
        return f"{item_name}{upgrade_text} [{rarity}{tier_text}]"

    @classmethod
    def item_shop_line(cls, item_id: str, items_data: dict, price: int) -> str:
        item = items_data.get(item_id, {})
        item_type = item.get("type", "item")
        bonus_parts = cls.item_bonus_parts(item)
        bonus_text = " | " + ", ".join(bonus_parts) if bonus_parts else ""
        return f"- {cls.item_label(item_id, items_data)} ({item_type}){bonus_text} - {price} gold"

    @staticmethod
    def _upgrade_material_count(item: dict) -> int:
        material_id = str(item.get("upgrade_material", "")).strip().lower()
        if not material_id:
            return 0
        return max(1, int(item.get("upgrade_material_count", 1)))

    @classmethod
    def upgrade_cost(cls, player: Character, item_id: str, items_data: dict) -> dict | None:
        item = items_data.get(item_id, {})
        max_level = player.max_item_upgrade_level(item)
        if max_level <= 0:
            return None

        current_level = player.item_upgrade_level(item_id, items_data)
        if current_level >= max_level:
            return None

        next_level = current_level + 1
        rarity_key = str(item.get("rarity", "common")).strip().lower()
        rarity_step = int(cls.RARITY_COST_STEPS.get(rarity_key, 0))
        tier = max(1, int(item.get("tier", 1)))
        gold_cost = max(8, (6 + (tier * 4) + (rarity_step * 6)) * next_level)
        material_id = str(item.get("upgrade_material", "")).strip().lower()
        material_count = cls._upgrade_material_count(item)

        return {
            "current_level": current_level,
            "next_level": next_level,
            "max_level": max_level,
            "gold": gold_cost,
            "material_id": material_id,
            "material_count": material_count,
        }

    @classmethod
    def upgrade_cost_text(cls, player: Character, item_id: str, items_data: dict) -> str:
        cost = cls.upgrade_cost(player, item_id, items_data)
        if not cost:
            item = items_data.get(item_id, {})
            if player.max_item_upgrade_level(item) <= 0:
                return "This item cannot be upgraded."
            return "This item is already at its upgrade cap."

        parts = [f"{cost['gold']} gold"]
        if cost["material_id"] and cost["material_count"] > 0:
            material_name = items_data.get(cost["material_id"], {}).get("name", cls._fallback_name(cost["material_id"]))
            parts.append(f"{cost['material_count']} {material_name}")
        return ", ".join(parts)

    def gear_lines(self, player: Character, items_data: dict) -> list[str]:
        lines = ["Gear"]
        slots = [
            ("Weapon", player.equipped_weapon),
            ("Armor", getattr(player, "equipped_armor", None)),
            ("Accessory", getattr(player, "equipped_accessory", None)),
        ]
        for slot_name, item_id in slots:
            if not item_id:
                lines.append(f"{slot_name}: none")
                continue
            effective_item = player.effective_item_data(item_id, items_data)
            label = self.item_label(item_id, items_data, player.item_upgrade_level(item_id, items_data))
            bonus_parts = self.item_bonus_parts(effective_item)
            bonus_text = " | " + ", ".join(bonus_parts) if bonus_parts else ""
            cost_text = self.upgrade_cost_text(player, item_id, items_data)
            lines.append(f"{slot_name}: {label}{bonus_text}")
            lines.append(f"Upgrade: {cost_text}")
        return lines

    def inspect_item_lines(self, player: Character, item_id: str, items_data: dict, source: str, include_upgrade_state: bool = True) -> list[str]:
        base_item = items_data.get(item_id, {})
        upgrade_level = player.item_upgrade_level(item_id, items_data) if include_upgrade_state else 0
        effective_item = player.effective_item_data(item_id, items_data) if include_upgrade_state and item_id in player.inventory else dict(base_item)
        item_name = self.item_label(item_id, items_data, upgrade_level)
        item_type = effective_item.get("type", base_item.get("type", "unknown"))
        description = effective_item.get("description", base_item.get("description", "No details are known about this item yet."))
        lines = [
            f"You inspect {item_name} ({item_type}).",
            str(description),
            f"Found: {source}.",
        ]
        bonus_parts = self.item_bonus_parts(effective_item)
        if bonus_parts:
            lines.append("Bonuses: " + ", ".join(bonus_parts))
        max_level = player.max_item_upgrade_level(base_item)
        if include_upgrade_state and max_level > 0:
            current_level = upgrade_level
            lines.append(f"Upgrade level: +{current_level}/{max_level}")
            lines.append("Next upgrade: " + self.upgrade_cost_text(player, item_id, items_data))
        elif max_level > 0:
            lines.append(f"Upgrade cap: +{max_level}")
        return lines

    def find_item_in_inventory(self, player: Character, items_data: dict, query: str) -> str | None:
        query = query.strip().lower()
        for item_id in player.inventory:
            item = items_data.get(item_id, {})
            if query == item_id.lower() or query == item.get("name", "").lower():
                return item_id
        return None

    def inventory_lines(self, player: Character, items_data: dict) -> list[str]:
        if not player.inventory:
            return ["Backpack: empty", "Equipped weapon: none", "Equipped armor: none", "Equipped accessory: none"]

        lines = ["Backpack:"]
        display_entries = []
        stack_counts = {}
        for item_id in player.inventory:
            normalized_item = str(item_id).strip().lower()
            if self.is_stackable(normalized_item, items_data):
                stack_counts[normalized_item] = stack_counts.get(normalized_item, 0) + 1
                if normalized_item not in display_entries:
                    display_entries.append(normalized_item)
                continue
            display_entries.append(normalized_item)

        for index, item_id in enumerate(display_entries, start=1):
            item = player.effective_item_data(item_id, items_data)
            item_name = self.item_label(item_id, items_data, player.item_upgrade_level(item_id, items_data))
            item_type = item.get("type", "unknown")
            bonus_parts = self.item_bonus_parts(item)
            equipped_tags = []
            if item_id == player.equipped_weapon:
                equipped_tags.append("weapon")
            if item_id == getattr(player, "equipped_armor", None):
                equipped_tags.append("armor")
            if item_id == getattr(player, "equipped_accessory", None):
                equipped_tags.append("accessory")
            equipped_tag = f" [{' & '.join(equipped_tags)}]" if equipped_tags else ""
            bonus_text = f" | {', '.join(bonus_parts)}" if bonus_parts else ""
            quantity = stack_counts.get(item_id, 1)
            quantity_text = f"{quantity}x " if quantity > 1 else ""
            lines.append(f"{index}. {quantity_text}{item_name} ({item_type}){equipped_tag}{bonus_text}")
        equipped_name = "none"
        if player.equipped_weapon:
            equipped_name = self.item_label(player.equipped_weapon, items_data, player.item_upgrade_level(player.equipped_weapon, items_data))
        equipped_armor_name = "none"
        if getattr(player, "equipped_armor", None):
            equipped_armor_name = self.item_label(player.equipped_armor, items_data, player.item_upgrade_level(player.equipped_armor, items_data))
        equipped_accessory_name = "none"
        if getattr(player, "equipped_accessory", None):
            equipped_accessory_name = self.item_label(player.equipped_accessory, items_data, player.item_upgrade_level(player.equipped_accessory, items_data))
        lines.append(f"Equipped weapon: {equipped_name}")
        lines.append(f"Equipped armor: {equipped_armor_name}")
        lines.append(f"Equipped accessory: {equipped_accessory_name}")
        return lines

    def use_item(self, player: Character, item_id: str, items_data: dict) -> str:
        item = player.effective_item_data(item_id, items_data) if item_id in player.inventory else items_data.get(item_id, {})
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
            return f"You equipped {self.item_label(item_id, items_data, player.item_upgrade_level(item_id, items_data))}. Attack is now {attack_value}.{bonus_text}"

        if item_type == "armor":
            if getattr(player, "equipped_armor", None) == item_id:
                defense_value = player.defense_value(items_data)
                return f"{item_name} is already equipped. Defense is {defense_value}."
            player.equipped_armor = item_id
            defense_value = player.defense_value(items_data)
            bonus_parts = self.item_bonus_parts(item)
            bonus_text = " Bonuses: " + ", ".join(bonus_parts) + "." if bonus_parts else ""
            return f"You equipped {self.item_label(item_id, items_data, player.item_upgrade_level(item_id, items_data))}. Defense is now {defense_value}.{bonus_text}"

        if item_type in {"gear", "accessory"}:
            if getattr(player, "equipped_accessory", None) == item_id:
                return f"{item_name} is already equipped. Its bonuses are already active."
            player.equipped_accessory = item_id
            bonus_parts = self.item_bonus_parts(item)
            bonus_text = " Bonuses: " + ", ".join(bonus_parts) + "." if bonus_parts else ""
            focus_text = f" Focus {player.focus}/{player.max_focus}."
            return f"You equipped {self.item_label(item_id, items_data, player.item_upgrade_level(item_id, items_data))}.{bonus_text}{focus_text}"

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
        load = self.carry_load(player, items_data)
        capacity = player.carry_capacity()
        return True, f"{seller_name}: Sold 1 {item_name} for {cost} gold. Gold left: {player.gold}. Carry {load}/{capacity}."

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
        still_has_copy = item_id in player.inventory
        if player.equipped_weapon == item_id and not still_has_copy:
            player.equipped_weapon = None
        if getattr(player, "equipped_armor", None) == item_id and not still_has_copy:
            player.equipped_armor = None
        if getattr(player, "equipped_accessory", None) == item_id and not still_has_copy:
            player.equipped_accessory = None
        if not still_has_copy:
            player.set_item_upgrade_level(item_id, 0)
        player.gold += value
        load = self.carry_load(player, items_data)
        capacity = player.carry_capacity()
        return True, f"{buyer_name}: Bought 1 {item_name} for {value} gold. Gold now: {player.gold}. Carry {load}/{capacity}."

    def upgrade_item(self, player: Character, item_id: str, items_data: dict) -> tuple[bool, str]:
        if item_id not in player.inventory:
            return False, "You do not have that item."
        if item_id not in items_data:
            return False, "That item does not exist."

        item = items_data.get(item_id, {})
        cost = self.upgrade_cost(player, item_id, items_data)
        if cost is None:
            if player.max_item_upgrade_level(item) <= 0:
                return False, "That item cannot be upgraded."
            return False, "That item is already at its upgrade cap."

        if player.gold < cost["gold"]:
            return False, f"You need {cost['gold']} gold to upgrade {self.item_label(item_id, items_data, player.item_upgrade_level(item_id, items_data))}."

        material_id = cost["material_id"]
        material_count = int(cost["material_count"])
        if material_id and material_count > 0 and player.inventory.count(material_id) < material_count:
            material_name = items_data.get(material_id, {}).get("name", self._fallback_name(material_id))
            return False, f"You need {material_count} {material_name} to upgrade this item."

        player.gold -= cost["gold"]
        for _ in range(material_count):
            if material_id in player.inventory:
                player.inventory.remove(material_id)
        player.set_item_upgrade_level(item_id, cost["next_level"], items_data)
        effective_item = player.effective_item_data(item_id, items_data)
        bonus_parts = self.item_bonus_parts(effective_item)
        bonus_text = " New bonuses: " + ", ".join(bonus_parts) + "." if bonus_parts else ""
        return (
            True,
            f"Upgraded {self.item_label(item_id, items_data, cost['next_level'])} for {cost['gold']} gold."
            f"{bonus_text} Gold left: {player.gold}.",
        )
