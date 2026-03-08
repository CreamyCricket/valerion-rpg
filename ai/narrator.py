class Narrator:
    """Provides text only; it never mutates game state and only reflects current mechanics."""
    @staticmethod
    def intro() -> str:
        return "Welcome to Valerion. Type 'help' to see commands."

    @staticmethod
    def new_game_intro(chapter_progress: dict, location_name: str, character_context: dict | None = None) -> str:
        title = chapter_progress.get("title", "Arc 1: Village Roads")
        note = chapter_progress.get("note", "")
        parts = [title]
        if note:
            parts.append(note)
        if character_context:
            race = character_context.get("race", "")
            player_class = character_context.get("class", "")
            background = character_context.get("background", "")
            if race and player_class and background:
                article = "an" if str(race).strip().lower()[:1] in {"a", "e", "i", "o", "u"} else "a"
                parts.append(f"You begin as {article} {race} {player_class} with a {background} past.")
        parts.append(f"Begin at {location_name}.")
        return " ".join(parts)

    @staticmethod
    def character_creation_text(character_context: dict) -> str:
        lines = [
            "Character Created",
            f"Name: {character_context.get('name', 'Hero')}",
            f"Gender: {character_context.get('gender', 'Other')}",
            f"Race: {character_context.get('race', 'Human')}",
            f"Race bonus: {character_context.get('race_summary', 'None')}",
            f"Class: {character_context.get('class', 'Warrior')}",
            f"Class bonus: {character_context.get('class_summary', 'None')}",
            f"Background: {character_context.get('background', 'Village-born')}",
            f"Background bonus: {character_context.get('background_summary', 'None')}",
            f"Starting HP: {character_context.get('max_hp', 20)}",
            f"Starting Focus: {character_context.get('max_focus', 6)}",
            f"Starting Attack: {character_context.get('attack', character_context.get('base_attack', 3))}",
            f"Starting Accuracy: {character_context.get('accuracy', character_context.get('attack', 3))}",
            f"Starting Defense: {character_context.get('defense', 10)}",
            f"Starting Dodge: {character_context.get('dodge_chance', 0)}%",
            f"Starting Crit: {character_context.get('crit_chance', 5)}%",
            f"Starting Gold: {character_context.get('gold', 0)}",
        ]
        if "spell_power" in character_context or "healing_power" in character_context:
            lines.append(
                "Power: "
                f"Mana/Focus {character_context.get('mana', character_context.get('max_focus', 0))} | "
                f"Spell {character_context.get('spell_power', 0)} | "
                f"Healing {character_context.get('healing_power', 0)} | "
                f"Magic Guard {character_context.get('magic_guard', 0)} | "
                f"Carry {len(character_context.get('inventory', []))}/{character_context.get('carry_capacity', len(character_context.get('inventory', [])))}"
            )
        stats = character_context.get("stats", {})
        if isinstance(stats, dict) and stats:
            lines.append(
                "Stats: "
                + ", ".join(f"{stat_name.title()} {int(value)}" for stat_name, value in stats.items())
            )
        skill_values = character_context.get("skills", {})
        skill_proficiencies = character_context.get("skill_proficiencies", {})
        if isinstance(skill_values, dict) and skill_values:
            lines.append(
                "Skills: "
                + ", ".join(
                    f"{skill_name.title()} {int(skill_values.get(skill_name, 0))}"
                    f" (prof {int(skill_proficiencies.get(skill_name, 0))})"
                    for skill_name in (
                        "swordsmanship",
                        "archery",
                        "defense",
                        "spellcasting",
                        "stealth",
                        "survival",
                        "lore",
                        "persuasion",
                    )
                )
            )
        inventory = character_context.get("inventory", [])
        if inventory:
            lines.append("Starting gear: " + ", ".join(inventory))
        else:
            lines.append("Starting gear: none")
        if character_context.get("equipped_weapon"):
            lines.append("Equipped weapon: " + str(character_context.get("equipped_weapon")))
        if character_context.get("equipped_armor"):
            lines.append("Equipped armor: " + str(character_context.get("equipped_armor")))
        abilities = character_context.get("abilities", [])
        if isinstance(abilities, list) and abilities:
            lines.append("Starting abilities: " + ", ".join(str(name) for name in abilities))
        race_lore = str(character_context.get("race_lore", "")).strip()
        class_lore = str(character_context.get("class_lore", "")).strip()
        background_lore = str(character_context.get("background_lore", "")).strip()
        if race_lore:
            lines.append("Race lore: " + race_lore)
        if class_lore:
            lines.append("Class lore: " + class_lore)
        if background_lore:
            lines.append("Background lore: " + background_lore)
        bio = str(character_context.get("bio", "") or "").strip()
        if bio:
            lines.append("Bio: " + bio)
        return "\n".join(lines)

    @staticmethod
    def character_sheet_text(
        character_context: dict,
        skills: dict[str, dict[str, int | str]],
        abilities: list[dict],
        current_hp: int,
        current_focus: int,
        xp: int,
        xp_needed: int,
    ) -> str:
        lines = [
            "Character Sheet",
            (
                f"{character_context.get('name', 'Hero')} | "
                f"{character_context.get('race', 'Unknown')} {character_context.get('class', 'Adventurer')} | "
                f"{character_context.get('background', 'Unknown')}"
            ),
            f"Level {character_context.get('level', 1)} | XP {xp}/{xp_needed}",
            (
                f"Resources: HP {current_hp}/{character_context.get('max_hp', current_hp)} | "
                f"Mana/Focus {current_focus}/{character_context.get('max_focus', current_focus)} | "
                f"Gold {character_context.get('gold', 0)}"
            ),
        ]

        stats = character_context.get("stats", {})
        if isinstance(stats, dict) and stats:
            lines.append(
                "Stats: "
                + ", ".join(
                    f"{stat_name.title()} {int(value)}"
                    for stat_name, value in stats.items()
                )
            )

        lines.append(
            "Derived: "
            f"Attack {character_context.get('attack', 0)} ({character_context.get('attack_stat', 'Unknown')}/{character_context.get('weapon_skill', 'Unknown')}) | "
            f"Accuracy {character_context.get('accuracy', 0)} | "
            f"Defense {character_context.get('defense', 0)} | "
            f"Dodge {character_context.get('dodge_chance', 0)}% | "
            f"Crit {character_context.get('crit_chance', 0)}%"
        )
        lines.append(
            "Power: "
            f"Spell {character_context.get('spell_power', 0)} | "
            f"Healing {character_context.get('healing_power', 0)} | "
            f"Magic Guard {character_context.get('magic_guard', 0)} | "
            f"Resilience {character_context.get('resilience', 0)}"
        )

        skill_bits = []
        for skill_name in ("swordsmanship", "archery", "defense", "spellcasting", "stealth", "survival", "lore", "persuasion"):
            entry = skills.get(skill_name, {}) if isinstance(skills, dict) else {}
            skill_bits.append(f"{skill_name.title()} {int(entry.get('total', 0))}")
        lines.append("Skills: " + ", ".join(skill_bits))

        lines.append(
            f"Gear: Weapon {character_context.get('equipped_weapon', 'none') or 'none'} | "
            f"Armor {character_context.get('equipped_armor', 'none') or 'none'} | "
            f"Accessory {character_context.get('equipped_accessory', 'none') or 'none'}"
        )

        if abilities:
            lines.append("Abilities: " + ", ".join(str(ability.get("name", "Ability")) for ability in abilities))
        else:
            lines.append("Abilities: none")

        bio = str(character_context.get("bio", "") or "").strip()
        if bio:
            lines.append("Bio: " + bio)
        return "\n".join(lines)

    @staticmethod
    def load_reminder_text(location_name: str, chapter_progress: dict, history_flags: dict | None) -> str:
        history_flags = history_flags or {}
        title = chapter_progress.get("title", "Arc 1: Village Roads")
        note = chapter_progress.get("note", "")
        lines = [f"Returning to {location_name}.", title]
        if note:
            lines.append(note)
        if history_flags.get("shrine_guardian_defeated"):
            lines.append("The shrine remains calm since the guardian fell.")
        elif history_flags.get("watchtower_cleared"):
            lines.append("The watchtower road is quieter now.")
        return " ".join(lines)

    @staticmethod
    def location_text(
        location_id: str,
        location: dict,
        enemies: list[str],
        items: list[str],
        exits: dict,
        enemy_names: dict,
        item_names: dict,
        npc_names: list[str] | None = None,
        scene_lines: list[str] | None = None,
        state_lines: list[str] | None = None,
        history_flags: dict | None = None,
        location_context: dict | None = None,
    ) -> str:
        location_context = location_context or {}
        lines = [f"{location.get('name', 'Unknown')}\n{location.get('description', '')}"]
        if scene_lines:
            lines.extend(scene_lines)
        else:
            memory_note = Narrator._location_memory_note(location_id, history_flags or {}, inspect_mode=False)
            if memory_note:
                lines.append(memory_note)

        continuity_lines = Narrator._location_continuity_lines(location_context)
        if continuity_lines:
            lines.extend(continuity_lines)

        if state_lines:
            lines.append("Area state: " + ", ".join(state_lines))

        npc_names = npc_names or []
        if npc_names:
            lines.append("NPCs here: " + ", ".join(npc_names))
        else:
            lines.append("NPCs here: none")

        if enemies:
            names = [enemy_names.get(enemy_id, enemy_id) for enemy_id in enemies]
            lines.append("Enemies here: " + ", ".join(names))
        else:
            lines.append("Enemies here: none")

        if items:
            names = [item_names.get(item_id, item_id) for item_id in items]
            lines.append("Items here: " + ", ".join(names))
        else:
            lines.append("Items here: none")

        if exits:
            exit_text = ", ".join([f"{key} -> {value}" for key, value in exits.items()])
            lines.append("Exits: " + exit_text)
        else:
            lines.append("Exits: none")
        return "\n".join(lines)

    @staticmethod
    def movement_text(location_name: str, enemies: list[str], items: list[str]) -> str:
        return f"You travel to {location_name}."

    @staticmethod
    def encounter_text(location_name: str, enemy_names: list[str]) -> str:
        if not enemy_names:
            return ""
        if len(enemy_names) == 1:
            return f"Encounter: {enemy_names[0]} is waiting in {location_name}."
        return f"Encounter: danger is present in {location_name} ({', '.join(enemy_names)})."

    @staticmethod
    def encounter_npc_text(location_name: str, npc_name: str) -> str:
        return f"Encounter: {npc_name} crosses your path in {location_name}."

    @staticmethod
    def combat_intro(enemy_name: str) -> str:
        return f"You engage {enemy_name} in battle."

    @staticmethod
    def combat_result(victory: bool, enemy_name: str) -> str:
        if victory:
            return f"You defeated {enemy_name}."
        return f"You were defeated by {enemy_name}."

    @staticmethod
    def item_taken(item_name: str) -> str:
        return f"You took {item_name}."

    @staticmethod
    def item_bought(item_name: str, cost: int, gold_left: int) -> str:
        return f"You bought {item_name} for {cost} gold. Gold left: {gold_left}."

    @staticmethod
    def loot_text(loot_names: list[str]) -> str:
        if not loot_names:
            return "Loot gained: none."
        return "Loot gained: " + ", ".join(loot_names) + "."

    @staticmethod
    def world_event_text(event_name: str, location_name: str, effect_summary: str) -> str:
        return f"World event: {event_name} at {location_name}. {effect_summary}"

    @staticmethod
    def enemy_fled_text(enemy_name: str) -> str:
        return f"{enemy_name} flees the fight."

    @staticmethod
    def xp_text(amount: int, level: int, xp: int, xp_needed: int) -> str:
        return f"XP gained: {amount}. Level {level} progress: {xp}/{xp_needed}."

    @staticmethod
    def level_up_text(level: int, max_hp: int, attack: int, max_focus: int | None = None) -> str:
        if max_focus is None:
            return f"Level up: You are now level {level}. Max HP {max_hp}. Base attack {attack}."
        return f"Level up: You are now level {level}. Max HP {max_hp}. Focus {max_focus}. Base attack {attack}."

    @staticmethod
    def skills_text(skills: dict[str, dict[str, int]]) -> str:
        lines = ["Skills"]
        for skill_name in ("swordsmanship", "archery", "defense", "spellcasting", "stealth", "survival", "lore", "persuasion"):
            entry = skills.get(skill_name, {}) if isinstance(skills, dict) else {}
            total = int(entry.get("total", 0))
            proficiency = int(entry.get("proficiency", 0))
            stat_name = str(entry.get("stat", "mind")).title()
            lines.append(f"- {skill_name.title()}: {total} (prof {proficiency}, {stat_name})")
        return "\n".join(lines)

    @staticmethod
    def abilities_text(abilities: list[dict], current_focus: int, max_focus: int) -> str:
        lines = ["Abilities", f"Focus: {current_focus}/{max_focus}"]
        if not abilities:
            lines.append("- none")
            return "\n".join(lines)
        for ability in abilities:
            kind = str(ability.get("kind", "ability")).title()
            lines.append(
                f"- {ability.get('name', ability.get('id', 'Ability'))} "
                f"({kind}, cost {int(ability.get('cost', 0))}): {ability.get('description', '')}"
            )
        return "\n".join(lines)

    @staticmethod
    def ability_text(name: str, detail: str) -> str:
        return f"{name}: {detail}"

    @staticmethod
    def combat_header_text(
        enemy_name: str,
        player_hp: int,
        player_max_hp: int,
        player_focus: int,
        player_max_focus: int,
        enemy_hp: int,
        enemy_max_hp: int,
        enemy_summary: str = "",
        prepared_effect: str = "",
    ) -> str:
        lines = [
            f"Combat: {enemy_name}",
            f"Player: HP {player_hp}/{player_max_hp} | Focus {player_focus}/{player_max_focus}",
            f"Enemy: HP {enemy_hp}/{enemy_max_hp}",
        ]
        if enemy_summary:
            lines.append("Enemy read: " + enemy_summary)
        if prepared_effect:
            lines.append("Prepared effect: " + prepared_effect)
        return "\n".join(lines)

    @staticmethod
    def combat_options_text(option_lines: list[str]) -> str:
        lines = ["Combat options"]
        if option_lines:
            lines.extend(option_lines)
        else:
            lines.append("- Attack with: fight <enemy>")
        return "\n".join(lines)

    @staticmethod
    def combat_footer_text(
        player_hp: int,
        player_max_hp: int,
        player_focus: int,
        player_max_focus: int,
        enemy_name: str,
        enemy_hp: int,
    ) -> str:
        return (
            f"Combat end: Player HP {player_hp}/{player_max_hp} | "
            f"Focus {player_focus}/{player_max_focus} | "
            f"{enemy_name} HP {enemy_hp}"
        )

    @staticmethod
    def npc_dialogue_text(
        npc_name: str,
        role: str,
        dialogue: str,
        offered_quests: list[str],
        service_lines: list[str] | None = None,
        memory_lines: list[str] | None = None,
    ) -> str:
        lines = [f"{npc_name} ({role})", dialogue]
        if memory_lines:
            lines.extend(memory_lines)
        if service_lines:
            lines.extend(service_lines)
        if offered_quests:
            lines.append("Quest offers: " + ", ".join(offered_quests))
            lines.append("Use 'accept <quest>' to take one.")
        return "\n".join(lines)

    @staticmethod
    def reputation_change_text(faction_name: str, amount: int, score: int, tier: str) -> str:
        sign = "+" if amount > 0 else ""
        return f"Reputation: {faction_name} {sign}{amount} -> {score} ({tier})."

    @staticmethod
    def trust_change_text(npc_name: str, amount: int, trust: int, tier: str) -> str:
        sign = "+" if amount > 0 else ""
        return f"Relations: {npc_name} trust {sign}{amount} -> {trust} ({tier})."

    @staticmethod
    def talk_text(npc_id: str, location_name: str, history_flags: dict | None = None) -> str:
        history_flags = history_flags or {}
        if npc_id == "elder":
            if history_flags.get("carrying_guardian_sigil"):
                return (
                    f'The Elder studies the sigil at your side in {location_name}. '
                    '"So the shrine truly yielded. Carry that proof with humility," he says.'
                )
            if history_flags.get("shrine_guardian_defeated"):
                return (
                    f'The Elder exhales more easily in {location_name}. '
                    '"The forest has changed since your victory at the shrine. Even the silence feels lighter," he says.'
                )
            if history_flags.get("watchtower_sweep_completed"):
                return (
                    f'The Elder nods with quiet approval in {location_name}. '
                    '"The watchtower stands empty again. Old roads remember brave work," he says.'
                )
            if history_flags.get("forest_path_cleared"):
                return (
                    f'The Elder watches the road from {location_name} with less strain in his eyes. '
                    '"You have already made the village path safer. Keep that steadiness," he says.'
                )
            return (
                f'The Elder folds his hands and studies the road ahead from {location_name}. '
                '"Keep your steps steady, and return wiser than you left," he says.'
            )
        if npc_id == "merchant":
            if history_flags.get("carrying_guardian_sigil"):
                return (
                    f'The Merchant leans over the counter in {location_name} and lowers her voice. '
                    '"That sigil will turn heads for weeks. I would not trade it away if I were you," she says.'
                )
            if history_flags.get("shrine_guardian_defeated"):
                return (
                    f'The Merchant straightens a bundle of goods in {location_name}. '
                    '"People are already walking with more confidence. Big victories travel fast," she says.'
                )
            if history_flags.get("watchtower_sweep_completed"):
                return (
                    f'The Merchant counts a fresh stack of wrapped supplies in {location_name}. '
                    '"With the watchtower quiet, traders may risk the road again," she says.'
                )
            if history_flags.get("forest_path_cleared"):
                return (
                    f'The Merchant adjusts her stock in {location_name} with a small smile. '
                    '"A safer forest path means fewer lost packs and better business," she says.'
                )
            return (
                f'The Merchant adjusts a stack of goods in {location_name}. '
                '"Supplies are simple today, but simple tools keep heroes alive," she says.'
            )
        if npc_id == "scout":
            if history_flags.get("watchtower_sweep_completed"):
                return (
                    f'The Scout studies the tower stones in {location_name}. '
                    '"Your sweep gave me room to work. I am mapping what moved through here," the Scout says.'
                )
            if history_flags.get("watchtower_cleared"):
                return (
                    f'The Scout keeps a careful watch from {location_name}. '
                    '"The immediate threat is gone, but I am not calling this route clean yet," the Scout says.'
                )
            return (
                f'The Scout scans the road from {location_name}. '
                '"I report what I can, but this post is still unstable," the Scout says.'
            )
        if npc_id == "caretaker":
            if history_flags.get("carrying_guardian_sigil"):
                return (
                    f'The Caretaker bows slightly in {location_name}. '
                    '"You carry the sigil. Good. Let memory be kept with care, not fear," the Caretaker says.'
                )
            if history_flags.get("shrine_guardian_defeated"):
                return (
                    f'The Caretaker traces a cracked rune in {location_name}. '
                    '"With the guardian fallen, this place can be studied instead of feared," the Caretaker says.'
                )
            return (
                f'The Caretaker watches the altar from {location_name}. '
                '"Old vows fade slowly, but they can still be read," the Caretaker says.'
            )
        return f"You exchange a few words with {npc_id.title()}."

    @staticmethod
    def demo_complete_text() -> str:
        return "Demo complete: You have finished the current Valerion adventure. You can keep exploring."

    @staticmethod
    def inspect_location_text(
        location: dict,
        location_id: str | None = None,
        history_flags: dict | None = None,
        location_context: dict | None = None,
    ) -> str:
        location_context = location_context or {}
        name = location.get("name", "Unknown")
        description = location.get("description", "There is nothing notable here.")
        lines = [f"You inspect {name}.", description]
        if location_id:
            memory_note = Narrator._location_memory_note(location_id, history_flags or {}, inspect_mode=True)
            if memory_note:
                lines.append(memory_note)
        continuity_lines = Narrator._location_continuity_lines(location_context, inspect_mode=True)
        if continuity_lines:
            lines.extend(continuity_lines)
        return "\n".join(lines)

    @staticmethod
    def inspect_special_location_text(
        location_id: str,
        location: dict,
        history_flags: dict | None = None,
        location_context: dict | None = None,
    ) -> str:
        name = location.get("name", "Unknown")
        description = location.get("description", "There is nothing notable here.")
        history_flags = history_flags or {}
        location_context = location_context or {}

        if location_id == "old_watchtower":
            if history_flags.get("watchtower_cleared"):
                text = (
                    f"You inspect {name}.\n"
                    f"{description}\n"
                    "The broken stair and wind-cut parapet feel less threatening now that the slime has been cleared away. "
                    "Only old watch-post scars remain: tally marks, rain-dark stone, and the sense that this ruin still wants to keep watch."
                )
                continuity = Narrator._location_continuity_lines(location_context, inspect_mode=True)
                if continuity:
                    text += "\n" + "\n".join(continuity)
                return text
            text = (
                f"You inspect {name}.\n"
                f"{description}\n"
                "Weather-worn arrow slits still face the old road, where watchfires once warned the village of raiders and winter beasts. "
                "Along the inner stair, faded tally marks and a half-buried captain's sigil hint that the final garrison held this post longer than anyone remembers."
            )
            continuity = Narrator._location_continuity_lines(location_context, inspect_mode=True)
            if continuity:
                text += "\n" + "\n".join(continuity)
            return text

        if location_id == "ruined_shrine":
            if history_flags.get("sigil_quest_completed"):
                text = (
                    f"You inspect {name}.\n"
                    f"{description}\n"
                    "The shrine now feels settled rather than haunted. With the sigil delivered and its story preserved, "
                    "the ruined stones read like memory instead of warning."
                )
                continuity = Narrator._location_continuity_lines(location_context, inspect_mode=True)
                if continuity:
                    text += "\n" + "\n".join(continuity)
                return text
            if history_flags.get("shrine_guardian_defeated"):
                text = (
                    f"You inspect {name}.\n"
                    f"{description}\n"
                    "The shrine's cold tension has broken into a solemn quiet, as if the stones themselves have finally exhaled. "
                    "Where a guardian once waited in judgment, only drifting ash, cracked runes, and the memory of an old vow remain."
                )
                continuity = Narrator._location_continuity_lines(location_context, inspect_mode=True)
                if continuity:
                    text += "\n" + "\n".join(continuity)
                return text
            text = (
                f"You inspect {name}.\n"
                f"{description}\n"
                "Moss-choked altar stones circle a blackened basin where offerings once burned through the night, and the air carries a cold, metallic stillness. "
                "Across the fallen lintel, fragments of prayer-runes repeat one surviving promise: a guardian would wake if the sacred boundary was broken."
            )
            continuity = Narrator._location_continuity_lines(location_context, inspect_mode=True)
            if continuity:
                text += "\n" + "\n".join(continuity)
            return text

        return Narrator.inspect_location_text(location, location_id, history_flags, location_context=location_context)

    @staticmethod
    def inspect_item_text(item_name: str, item_type: str, description: str, source: str) -> str:
        return (
            f"You inspect {item_name} ({item_type}).\n"
            f"{description}\n"
            f"Found: {source}."
        )

    @staticmethod
    def inspect_lore_object_text(lore_object_id: str, location_id: str, history_flags: dict | None = None) -> str:
        history_flags = history_flags or {}

        if lore_object_id == "shrine_altar":
            if history_flags.get("shrine_guardian_defeated"):
                return (
                    "You inspect the shrine altar.\n"
                    "Ash lines and faint offerings remain, but the old threat is gone. The altar now feels like a record, not a warning."
                )
            return (
                "You inspect the shrine altar.\n"
                "Cold stone surrounds a blackened basin where night offerings once burned, and the runes still carry a guarded silence."
            )

        if lore_object_id == "cracked_sigil_stone":
            if history_flags.get("shrine_guardian_defeated"):
                return (
                    "You inspect the cracked sigil stone.\n"
                    "The fracture now reads like an ending mark, as if the vow bound here has finally been fulfilled."
                )
            return (
                "You inspect the cracked sigil stone.\n"
                "The carved mark is split down the center, but one phrase is still readable: 'wake and ward.'"
            )

        if lore_object_id == "watchtower_journal":
            if history_flags.get("watchtower_cleared"):
                return (
                    "You inspect the watchtower journal.\n"
                    "Most pages are weather-warped, but the final entries describe long quiet watches after one last slime purge."
                )
            return (
                "You inspect the watchtower journal.\n"
                "A damp ledger of patrol notes, supply counts, and repeated warnings that the lower stair was never fully secure."
            )

        if lore_object_id == "memorial_plaque":
            return (
                "You inspect the memorial plaque.\n"
                "The names are worn nearly smooth, but a closing line remains: 'They held the road when no one else could.'"
            )

        return (
            f"You inspect {lore_object_id.replace('_', ' ')}.\n"
            f"There is old history here in {location_id.replace('_', ' ')}."
        )

    @staticmethod
    def inspect_npc_text(npc_name: str, location_name: str) -> str:
        if npc_name.lower() == "elder":
            return (
                f"You inspect Elder in {location_name}.\n"
                "The village elder watches quietly, measuring every decision."
            )
        if npc_name.lower() == "merchant":
            return (
                f"You inspect Merchant in {location_name}.\n"
                "The merchant keeps careful notes and checks each item before a sale."
            )
        if npc_name.lower() == "scout":
            return (
                f"You inspect Scout in {location_name}.\n"
                "The scout keeps practical field notes and rarely looks away from likely approaches."
            )
        if npc_name.lower() == "caretaker":
            return (
                f"You inspect Caretaker in {location_name}.\n"
                "The caretaker records damaged runes and treats every shrine stone like a fragile archive."
            )
        return f"You inspect {npc_name} in {location_name}."

    @staticmethod
    def ask_text(npc_id: str, topic: str, history_flags: dict | None = None, npc_memory: dict | None = None) -> str:
        topic_normalized = " ".join(topic.strip().lower().split())
        history_flags = history_flags or {}
        npc_memory = npc_memory or {}
        reply_prefix = Narrator._npc_memory_reply_prefix(npc_id, npc_memory)

        if npc_id == "elder":
            if any(word in topic_normalized for word in ["forest", "woods", "trees"]):
                if history_flags.get("shrine_guardian_defeated"):
                    return reply_prefix + (
                        'The Elder looks toward the deeper woods. "You felt it too. The forest still keeps its secrets, '
                        'but the old pressure around the shrine has lifted."'
                    )
                if history_flags.get("forest_path_cleared"):
                    return reply_prefix + (
                        'The Elder nods once. "The forest path is steadier now because you acted. '
                        'Safety begins with one cleared road."'
                    )
                return reply_prefix + (
                    'The Elder nods slowly. "The forest rewards patience. '
                    'Watch your path, and you will return."'
                )
            if any(word in topic_normalized for word in ["danger", "risk", "monster"]):
                if history_flags.get("shrine_guardian_defeated"):
                    return reply_prefix + (
                        'The Elder lowers his voice. "You have already faced what waited deeper than most dare go. '
                        'Do not let one great victory teach you carelessness."'
                    )
                return reply_prefix + (
                    'The Elder lowers his voice. "Danger grows when pride grows. '
                    'Prepare, then act."'
                )
            if any(word in topic_normalized for word in ["watchtower", "tower", "road"]):
                if history_flags.get("watchtower_sweep_completed"):
                    return reply_prefix + (
                        'The Elder allows himself a rare smile. "The watchtower is quiet again. '
                        'That old road may serve the village a while longer."'
                    )
                if history_flags.get("forest_path_cleared"):
                    return reply_prefix + (
                        'The Elder glances toward the road. "The path is better than it was, but the watchtower still deserves caution."'
                    )
            return reply_prefix + (
                f'The Elder considers your question about "{topic.strip()}". '
                '"Steady choices carry you farther than hurried ones."'
            )

        if npc_id == "merchant":
            if any(word in topic_normalized for word in ["supply", "supplies", "stock", "goods"]):
                if history_flags.get("watchtower_sweep_completed"):
                    return reply_prefix + (
                        'The Merchant taps a fresh bundle. "If the watchtower road stays quiet, stock should move more reliably. '
                        'That means fewer shortages for everyone."'
                    )
                return reply_prefix + (
                    'The Merchant taps a crate. "Supplies are simple today: '
                    'Potion, 5 gold. Reliable and affordable."'
                )
            if any(word in topic_normalized for word in ["price", "cost", "gold"]):
                if int(npc_memory.get("trust", 0)) >= 10:
                    return reply_prefix + (
                        'The Merchant smiles more easily than before. "I keep fair prices, and I do a little better for people who have earned trust. '
                        'Reliable trade should reward reliable company."'
                    )
                if int(npc_memory.get("trust", 0)) <= -10 or int(npc_memory.get("harmed", 0)) > int(npc_memory.get("helped", 0)):
                    return reply_prefix + (
                        'The Merchant keeps her tone measured. "Prices stay clear when trust does not. '
                        'Coin first, confidence later."'
                    )
                if history_flags.get("forest_path_cleared"):
                    return reply_prefix + (
                        'The Merchant smiles. "Safer roads help prices stay fair. '
                        'A Potion is still 5 gold, and I would like to keep it that way."'
                    )
                return reply_prefix + (
                    'The Merchant smiles. "I keep fair prices. A Potion is 5 gold, '
                    'and every coin should matter."'
                )
            if any(word in topic_normalized for word in ["sigil", "shrine", "guardian"]):
                if history_flags.get("carrying_guardian_sigil"):
                    return reply_prefix + (
                        'The Merchant keeps her voice low. "That sigil is worth more as a story than as coin. '
                        'People will remember who brought it out of the shrine."'
                    )
                if history_flags.get("shrine_guardian_defeated"):
                    return reply_prefix + (
                        'The Merchant raises her brows. "Word of the shrine is already spreading. '
                        'Proof or not, people can tell something changed in the woods."'
                    )
            return reply_prefix + (
                f'The Merchant considers your question about "{topic.strip()}". '
                '"Good planning is better than expensive mistakes."'
            )

        if npc_id == "scout":
            if any(word in topic_normalized for word in ["watchtower", "tower", "road", "tracks"]):
                if history_flags.get("watchtower_cleared"):
                    return reply_prefix + (
                        'The Scout points to chipped stone. "After the clearing, movement dropped, but not to zero. '
                        'I need a clean sample to confirm what passed through here."'
                    )
                return reply_prefix + (
                    'The Scout keeps his voice low. "The tower sees too much road, and right now none of it feels safe."'
                )
            if any(word in topic_normalized for word in ["slime", "gel", "sample"]):
                return reply_prefix + (
                    'The Scout nods. "Slime gel tells us what kind of nest we are dealing with. '
                    'Bring a sample and we can close this report properly."'
                )
            return reply_prefix + (
                f'The Scout considers your question about "{topic.strip()}". '
                '"Good reports come from clear details and patient observation."'
            )

        if npc_id == "caretaker":
            if any(word in topic_normalized for word in ["shrine", "runes", "altar"]):
                if history_flags.get("shrine_guardian_defeated"):
                    return reply_prefix + (
                        'The Caretaker rests a hand on the stone. "Now that the guardian is gone, we can finally read this place openly."'
                    )
                return reply_prefix + (
                    'The Caretaker whispers, "The shrine speaks in fragments. Read too quickly, and you miss the warning in the gaps."'
                )
            if any(word in topic_normalized for word in ["sigil", "guardian"]):
                if history_flags.get("carrying_guardian_sigil"):
                    return reply_prefix + (
                        'The Caretaker nods toward your pack. "That sigil is not merely loot. '
                        'Delivered properly, it becomes a record instead of a trophy."'
                    )
                return reply_prefix + (
                    'The Caretaker says, "The sigil matters because it proves what happened here, not because it shines."'
                )
            return reply_prefix + (
                f'The Caretaker considers your question about "{topic.strip()}". '
                '"History survives when someone chooses to preserve it."'
            )

        return reply_prefix + f"{npc_id.title()} has nothing to say about that right now."

    @staticmethod
    def _npc_memory_reply_prefix(npc_id: str, npc_memory: dict) -> str:
        if not isinstance(npc_memory, dict):
            return ""

        npc_name = str(npc_memory.get("npc_name", npc_id.replace("_", " ").title())).strip() or npc_id.replace("_", " ").title()
        trust = int(npc_memory.get("trust", 0))
        helped = int(npc_memory.get("helped", 0))
        harmed = int(npc_memory.get("harmed", 0))
        quests_completed = int(npc_memory.get("quests_completed", 0))
        faction_name = str(npc_memory.get("faction_name", "")).strip()

        if trust <= -20 or harmed > helped:
            return f"{npc_name} answers with visible reserve. "
        if trust >= 20 or quests_completed > 0 or helped > harmed:
            if faction_name and faction_name != "Unaffiliated":
                return f"{npc_name} answers more openly, clearly remembering your standing with {faction_name}. "
            return f"{npc_name} answers more openly, clearly remembering how you have dealt with them before. "
        return ""

    @staticmethod
    def recap_text(
        player_name: str,
        location_name: str,
        hp: int,
        max_hp: int,
        gold: int,
        equipped_weapon: str,
        active_quests: list[str],
        completed_quests: list[str],
        demo_complete: bool,
        event_counts: dict,
        recent_events: list[dict],
        event_memory: dict | None,
        chapter_progress: dict,
        character_context: dict | None = None,
        location_context: dict | None = None,
        history_flags: dict | None = None,
    ) -> str:
        character_context = character_context or {}
        location_context = location_context or {}
        history_flags = history_flags or {}
        event_memory = event_memory or {}
        lines = [
            "Adventure Recap",
            f"Hero: {player_name}",
            f"Location: {location_name}",
            f"HP: {hp}/{max_hp}",
            f"Gold: {gold}",
            f"Equipped weapon: {equipped_weapon}",
        ]

        character_hook = Narrator._character_hook(character_context)
        if character_hook:
            lines.append(character_hook)

        region = str(location_context.get("region", "")).strip()
        if region:
            lines.append(f"Current region: {region}")
        region_lore = str(location_context.get("location_lore", "")).strip()
        if region_lore:
            lines.append("Region note: " + region_lore)
        state_names = location_context.get("state_names", [])
        if isinstance(state_names, list) and state_names:
            lines.append("Area pressure: " + ", ".join(str(name) for name in state_names))
        elif region:
            lines.append("Area pressure: calm")

        if active_quests:
            lines.append("Active quests:")
            lines.extend(f"- {line}" for line in active_quests)
        else:
            lines.append("Active quests: none")

        if completed_quests:
            lines.append("Completed quests:")
            lines.extend(f"- {title}" for title in completed_quests)
        else:
            lines.append("Completed quests: none")

        lines.append(f"Current arc: {chapter_progress.get('title', 'Arc 1: Village Roads')}")
        chapter_note = chapter_progress.get("note")
        if chapter_note:
            lines.append(f"Arc focus: {chapter_note}")

        turn_line = Narrator._campaign_turn_line(history_flags)
        if turn_line:
            lines.append(turn_line)

        lines.append(
            "Adventure memory: "
            f"{event_counts.get('locations_visited', 0)} locations, "
            f"{event_counts.get('enemies_defeated', 0)} enemies, "
            f"{event_counts.get('quests_completed', 0)} quests, "
            f"{event_counts.get('minibosses_defeated', 0)} minibosses, "
            f"{event_counts.get('important_items_acquired', 0)} important items."
        )
        memory_lines = Narrator._event_memory_lines(event_memory)
        if memory_lines:
            lines.append("Longer memory:")
            lines.extend(f"- {line}" for line in memory_lines)
        if recent_events:
            lines.append("Recent moments:")
            for event in recent_events:
                lines.append(f"- {Narrator._event_line(event)}")

        lines.append("Demo complete: yes" if demo_complete else "Demo complete: no")
        return "\n".join(lines)

    @staticmethod
    def story_text(
        player_name: str,
        location_name: str,
        completed_quests: list[str],
        active_quests: list[str],
        important_progress: list[str],
        shrine_guardian_status: str | None,
        event_counts: dict,
        recent_events: list[dict],
        event_memory: dict | None,
        chapter_progress: dict,
        character_context: dict | None = None,
        location_context: dict | None = None,
        history_flags: dict | None = None,
    ) -> str:
        character_context = character_context or {}
        location_context = location_context or {}
        history_flags = history_flags or {}
        event_memory = event_memory or {}
        lines = [
            "Story So Far",
            f"{player_name} is currently in {location_name}. The campaign is unfolding one clear step at a time.",
            f"Current arc: {chapter_progress.get('title', 'Arc 1: Village Roads')}",
        ]
        character_hook = Narrator._character_hook(character_context)
        if character_hook:
            lines.append(character_hook)
        chapter_note = chapter_progress.get("note")
        if chapter_note:
            lines.append(f"Arc focus: {chapter_note}")

        region = str(location_context.get("region", "")).strip()
        if region:
            lines.append(f"Region in play: {region}")
        region_lore = str(location_context.get("location_lore", "")).strip()
        if region_lore:
            lines.append("Campaign frame: " + region_lore)

        turn_line = Narrator._campaign_turn_line(history_flags)
        if turn_line:
            lines.append(turn_line)

        if completed_quests:
            lines.append("Completed quests:")
            lines.extend(f"- {title}" for title in completed_quests)
        else:
            lines.append("Completed quests: none yet")

        if active_quests:
            lines.append("Active quests:")
            lines.extend(f"- {summary}" for summary in active_quests)
        else:
            lines.append("Active quests: none")

        if important_progress:
            lines.append("Important progress:")
            lines.extend(f"- {note}" for note in important_progress)

        if shrine_guardian_status == "defeated":
            lines.append("Shrine Guardian: defeated")
        elif shrine_guardian_status == "undefeated":
            lines.append("Shrine Guardian: not yet defeated")
        else:
            lines.append("Shrine Guardian: unknown")

        lines.append(
            "Recorded milestones: "
            f"{event_counts.get('locations_visited', 0)} places charted, "
            f"{event_counts.get('enemies_defeated', 0)} enemies defeated, "
            f"{event_counts.get('quests_completed', 0)} quests completed, "
            f"{event_counts.get('world_states_started', 0)} world shifts begun, "
            f"{event_counts.get('world_states_cleared', 0)} settled."
        )
        memory_lines = Narrator._event_memory_lines(event_memory)
        if memory_lines:
            lines.append("Campaign memory:")
            lines.extend(f"- {line}" for line in memory_lines)
        if recent_events:
            lines.append("Recent timeline:")
            for event in recent_events:
                lines.append(f"- {Narrator._event_line(event)}")

        return "\n".join(lines)

    @staticmethod
    def _character_hook(character_context: dict) -> str:
        race = str(character_context.get("race", "")).strip()
        player_class = str(character_context.get("class", "")).strip()
        background = str(character_context.get("background", "")).strip()
        if not (race and player_class and background):
            return ""

        hook = f"Role: {race} {player_class} | {background}"
        background_lore = str(character_context.get("background_lore", "")).strip()
        class_lore = str(character_context.get("class_lore", "")).strip()
        race_lore = str(character_context.get("race_lore", "")).strip()
        lore_line = background_lore or class_lore or race_lore
        if lore_line:
            return hook + "\nStory hook: " + lore_line
        return hook

    @staticmethod
    def _campaign_turn_line(history_flags: dict) -> str:
        if history_flags.get("carrying_guardian_sigil"):
            return "Campaign turn: the Guardian Sigil is in your keeping, and its meaning now matters as much as its weight."
        if history_flags.get("shrine_guardian_defeated"):
            return "Campaign turn: the shrine has already answered with force, and the world is reacting to what you survived there."
        if history_flags.get("watchtower_sweep_completed"):
            return "Campaign turn: the watchtower road is stabilizing, but deeper forest mysteries are now impossible to ignore."
        if history_flags.get("forest_path_cleared"):
            return "Campaign turn: the village roads are safer than before, which means harder decisions now lie beyond them."
        return "Campaign turn: the opening roads are still testing what kind of adventurer you intend to become."

    @staticmethod
    def _event_memory_lines(event_memory: dict) -> list[str]:
        if not isinstance(event_memory, dict):
            return []

        lines = []
        visited = [entry.get("name", "") for entry in event_memory.get("visited_locations", [])[:3] if isinstance(entry, dict)]
        if visited:
            lines.append("Road walked: " + ", ".join(visited) + ".")

        victories = [entry.get("name", "") for entry in event_memory.get("defeated_enemies", [])[:3] if isinstance(entry, dict)]
        if victories:
            lines.append("Known victories: " + ", ".join(victories) + ".")

        quests = [entry.get("name", "") for entry in event_memory.get("completed_quests", [])[:3] if isinstance(entry, dict)]
        if quests:
            lines.append("Finished work: " + ", ".join(quests) + ".")

        items = [entry.get("name", "") for entry in event_memory.get("important_items_acquired", [])[:2] if isinstance(entry, dict)]
        if items:
            lines.append("Important finds: " + ", ".join(items) + ".")

        started = [entry.get("name", "") for entry in event_memory.get("world_states_started", [])[:2] if isinstance(entry, dict)]
        cleared = [entry.get("name", "") for entry in event_memory.get("world_states_cleared", [])[:2] if isinstance(entry, dict)]
        if started or cleared:
            parts = []
            if started:
                parts.append("troubled by " + ", ".join(started))
            if cleared:
                parts.append("settled after " + ", ".join(cleared))
            lines.append("World memory: " + "; ".join(parts) + ".")

        return lines

    @staticmethod
    def _location_continuity_lines(location_context: dict, inspect_mode: bool = False) -> list[str]:
        if not isinstance(location_context, dict):
            return []

        lines = []
        visit_count = int(location_context.get("visit_count", 0) or 0)
        if visit_count > 1:
            if inspect_mode:
                lines.append(f"You recognize this place from {visit_count} visits already recorded in your journey.")
            else:
                lines.append(f"Memory: you have passed through here {visit_count} times.")

        defeated_here = [str(name) for name in location_context.get("defeated_enemies_here", []) if str(name).strip()]
        if defeated_here:
            lines.append("Local memory: you have already beaten " + ", ".join(defeated_here[:2]) + " here.")

        minibosses_here = [str(name) for name in location_context.get("minibosses_here", []) if str(name).strip()]
        if minibosses_here:
            lines.append("Major memory: " + ", ".join(minibosses_here[:1]) + " fell here.")

        cleared_here = [str(name) for name in location_context.get("world_states_cleared_here", []) if str(name).strip()]
        if cleared_here:
            lines.append("The area still carries the aftermath of " + ", ".join(cleared_here[:2]) + ".")

        return lines

    @staticmethod
    def history_text(events: list[dict], event_memory: dict | None = None) -> str:
        if not events:
            return "History\nNo important events recorded yet."

        event_memory = event_memory or {}
        lines = ["History"]
        memory_lines = Narrator._event_memory_lines(event_memory)
        if memory_lines:
            lines.append("Remembered milestones:")
            lines.extend(f"- {line}" for line in memory_lines)
        lines.append("Timeline of important events:")
        for event in events:
            index = event.get("index", "?")
            lines.append(f"{index}. {Narrator._event_line(event)}")
        return "\n".join(lines)

    @staticmethod
    def world_text(lines: list[str]) -> str:
        return "\n".join(lines)

    @staticmethod
    def events_text(active_events: list[dict], recent_events: list[dict], current_location: str) -> str:
        lines = ["World Events", "Active:"]
        if active_events:
            for event in active_events:
                marker = " [YOU]" if event.get("location_id") == current_location else ""
                location_name = event.get("location_name", event.get("location_id", "Unknown"))
                lines.append(f"- {location_name}{marker}: {event.get('name', event.get('state_id', 'Event'))}")
        else:
            lines.append("- none")

        lines.append("Recent:")
        if recent_events:
            for event in recent_events:
                lines.append(f"- {Narrator._event_line(event)}")
        else:
            lines.append("- none")
        return "\n".join(lines)

    @staticmethod
    def relations_text(lines: list[str]) -> str:
        return "\n".join(lines)

    @staticmethod
    def event_line(event: dict) -> str:
        return Narrator._event_line(event)

    @staticmethod
    def _event_line(event: dict) -> str:
        event_type = str(event.get("type", "")).strip().lower()
        details = event.get("details", {})
        if not isinstance(details, dict):
            details = {}

        if event_type == "location_visited":
            location = details.get("location_name", details.get("location_id", "Unknown"))
            return f"Visited {location}."

        if event_type == "enemy_defeated":
            enemy = details.get("enemy_name", details.get("enemy_id", "Unknown enemy"))
            location = details.get("location_name", details.get("location_id", "unknown location"))
            return f"Defeated {enemy} at {location}."

        if event_type == "quest_completed":
            quest = details.get("quest_title", details.get("quest_id", "Unknown quest"))
            location = details.get("location_name", details.get("location_id", ""))
            if location:
                return f"Completed quest: {quest} at {location}."
            return f"Completed quest: {quest}."

        if event_type == "quest_accepted":
            quest = details.get("quest_title", details.get("quest_id", "Unknown quest"))
            location = details.get("location_name", details.get("location_id", ""))
            if location:
                return f"Accepted quest: {quest} at {location}."
            return f"Accepted quest: {quest}."

        if event_type == "miniboss_defeated":
            enemy = details.get("enemy_name", details.get("enemy_id", "Unknown miniboss"))
            return f"Defeated miniboss: {enemy}."

        if event_type == "important_item_acquired":
            item = details.get("item_name", details.get("item_id", "Unknown item"))
            source = details.get("source")
            location = details.get("location_name", details.get("location_id", ""))
            if source:
                if location:
                    return f"Acquired important item: {item} at {location} ({source})."
                return f"Acquired important item: {item} ({source})."
            return f"Acquired important item: {item}."

        if event_type == "encounter_triggered":
            name = details.get("encounter_name", details.get("encounter_id", "Encounter"))
            location = details.get("location_name", details.get("location_id", "unknown location"))
            return f"Encountered {name} at {location}."

        if event_type == "enemy_fled":
            enemy = details.get("enemy_name", details.get("enemy_id", "Unknown enemy"))
            return f"{enemy} fled from combat."

        if event_type == "xp_gained":
            amount = details.get("amount", 0)
            return f"Gained {amount} XP."

        if event_type == "level_up":
            level = details.get("level", "?")
            return f"Reached level {level}."

        if event_type == "world_event_resolved":
            event_name = details.get("event_name", details.get("event_id", "World event"))
            location = details.get("location_name", details.get("location_id", "unknown location"))
            outcome = details.get("outcome")
            if outcome:
                return f"{event_name} resolved at {location}: {outcome}."
            return f"{event_name} resolved at {location}."

        if event_type == "world_state_started":
            event_name = details.get("event_name", details.get("state_id", "World event"))
            location = details.get("location_name", details.get("location_id", "unknown location"))
            return f"{event_name} began at {location}."

        if event_type == "world_state_cleared":
            event_name = details.get("event_name", details.get("state_id", "World event"))
            location = details.get("location_name", details.get("location_id", "unknown location"))
            outcome = details.get("outcome")
            if outcome:
                return f"{event_name} ended at {location}: {outcome}."
            return f"{event_name} ended at {location}."

        if event_type == "reputation_changed":
            faction = details.get("faction_name", details.get("faction_id", "Faction"))
            amount = details.get("amount", 0)
            score = details.get("score")
            if score is not None:
                return f"Reputation shifted with {faction}: {amount:+} (now {score})."
            return f"Reputation shifted with {faction}: {amount:+}."

        if event_type == "npc_trust_changed":
            npc_name = details.get("npc_name", details.get("npc_id", "NPC"))
            amount = details.get("amount", 0)
            trust = details.get("trust")
            if trust is not None:
                return f"{npc_name}'s trust changed by {amount:+} (now {trust})."
            return f"{npc_name}'s trust changed by {amount:+}."

        return f"{event_type or 'event'}: {details}"

    @staticmethod
    def hint_text(message: str) -> str:
        return f"Hint: {message}"

    @staticmethod
    def search_text(
        location_name: str,
        target: str,
        item_names: list[str],
        enemy_names: list[str],
        npc_names: list[str],
        exits: dict,
    ) -> str:
        lines = [f"You search the {target} in {location_name}."]

        if item_names:
            lines.append("Visible items: " + ", ".join(item_names))
        else:
            lines.append("Visible items: none")

        if enemy_names:
            lines.append("Visible enemies: " + ", ".join(enemy_names))
        else:
            lines.append("Visible enemies: none")

        if npc_names:
            lines.append("Visible NPCs: " + ", ".join(npc_names))
        else:
            lines.append("Visible NPCs: none")

        if exits:
            exit_text = ", ".join(f"{direction} -> {name}" for direction, name in exits.items())
            lines.append("Visible exits: " + exit_text)
        else:
            lines.append("Visible exits: none")

        return "\n".join(lines)

    @staticmethod
    def rest_text(location_name: str, hp: int, max_hp: int, focus: int, max_focus: int, healed: bool) -> str:
        if healed:
            return (
                f"You rest at {location_name}. Your strength and focus return "
                f"(HP: {hp}/{max_hp}, Focus: {focus}/{max_focus})."
            )
        return (
            f"You rest at {location_name}, but you already feel fully recovered "
            f"(HP: {hp}/{max_hp}, Focus: {focus}/{max_focus})."
        )

    @staticmethod
    def rest_not_safe_text(location_name: str) -> str:
        return f"You cannot rest safely in {location_name}. Try resting in Village Square, Shop, or Inn."

    @staticmethod
    def about_text() -> str:
        return (
            "Valerion keeps rules and state in an engine-first rules layer while "
            "the AI narrates only the results the engine has already resolved. The engine owns combat rolls, HP, "
            "inventory, encounters, quest progress, faction reputation, NPC memory, location state changes, and world events. A small parser also accepts safe read-only "
            "free text such as looking, inspecting, asking, greeting, listening, and studying, plus a few validated "
            "actions like moving, fighting, taking, and using items."
        )

    @staticmethod
    def do_greet_text(npc_name: str) -> str:
        if not npc_name.strip():
            return "You offer a respectful greeting. The moment feels grounded and calm."
        return f'You offer a respectful greeting to {npc_name}. The moment feels grounded and calm.'

    @staticmethod
    def do_listen_text(
        location_name: str,
        enemies_here: bool,
        npcs_here: bool,
        history_flags: dict | None = None,
        focus: str = "",
    ) -> str:
        history_flags = history_flags or {}
        focus = " ".join(focus.strip().split())
        if focus and focus != "area":
            intro = f"You listen for {focus} in {location_name}."
        else:
            intro = f"You listen in {location_name}."

        if location_name == "Ruined Shrine" and history_flags.get("shrine_guardian_defeated"):
            return (
                f"{intro} The shrine no longer hums with threat; only wind moves through the cracked stone, "
                "and the silence feels earned."
            )
        if enemies_here:
            return f"{intro} Beneath the stillness, you catch the subtle scrape of danger nearby."
        if npcs_here:
            return f"{intro} Soft voices, shifting goods, and ordinary village sounds make the place feel lived in."
        return f"{intro} The place answers with a quiet, steady hush."

    @staticmethod
    def do_observe_text(location_name: str, has_enemies: bool, has_items: bool) -> str:
        if has_enemies and has_items:
            note = "You notice both danger and opportunity nearby."
        elif has_enemies:
            note = "You notice signs of danger nearby."
        elif has_items:
            note = "You notice useful things within reach."
        else:
            note = "You notice a quiet pause in the journey."
        return f"You observe {location_name}. {note}"

    @staticmethod
    def do_free_text(text: str) -> str:
        return (
            f'You try to "{text}", and the world answers with a quiet beat. '
            "Free-text input works best for observation and a few validated actions like go to, attack, pick up, or drink."
        )

    @staticmethod
    def do_guardrail_text(text: str) -> str:
        return (
            f'You consider "{text}", but the moment stays unresolved. '
            "If the natural-language mapping is unclear, use a direct engine command for movement, combat, inventory, or quests."
        )

    @staticmethod
    def action_router_fallback_text(text: str, detail: str) -> str:
        return f'You try to "{text}", but {detail} Nothing changes yet.'

    @staticmethod
    def _location_memory_note(location_id: str, history_flags: dict, inspect_mode: bool) -> str:
        if location_id == "ruined_shrine" and history_flags.get("shrine_guardian_defeated"):
            if history_flags.get("sigil_quest_completed"):
                if inspect_mode:
                    return "With the sigil's return complete, the shrine feels restored to remembrance rather than fear."
                return "The shrine rests in a final calm now that the sigil thread is resolved and its history has been properly kept."
            if inspect_mode:
                return "Without its guardian, the shrine feels solemn instead of hostile, as if an old burden has finally been lifted."
            return "The ruin feels changed now: the oppressive tension is gone, leaving a grave and watchful calm."

        if location_id == "old_watchtower" and history_flags.get("watchtower_cleared"):
            if inspect_mode:
                return "Whatever lurked here has been driven out, and the tower's loneliness feels older than its danger."
            return "The tower stands empty of immediate danger, its broken crown watching the road in hard silence."

        if location_id == "village_square":
            if history_flags.get("shrine_guardian_defeated"):
                return (
                    "The village mood has shifted; people speak more boldly, and more than one glance lingers on the deeper woods."
                )
            if history_flags.get("watchtower_sweep_completed"):
                return "The square feels more settled now that word of the cleared watchtower has spread."
            if history_flags.get("forest_path_quest_completed"):
                return "The villagers carry themselves with a little less tension now that the forest road is safer."

        if location_id == "shop" and history_flags.get("carrying_guardian_sigil"):
            return "Even here among plain goods, the sigil you carry makes the room feel briefly touched by deeper history."

        return ""
