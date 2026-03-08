import json
from pathlib import Path

from ai.dm_context import DMContextBuilder
from ai.intent_parser import IntentParseResult, IntentParser
from ai.narrator import Narrator
from ai.scene_composer import SceneComposer
from engine.action_router import ActionRouter
from engine.abilities import AbilityEngine
from engine.combat import CombatEngine
from engine.dice import DiceEngine
from engine.encounters import EncounterEngine
from engine.factions import FactionEngine
from engine.inventory import InventoryEngine
from engine.quests import QuestEngine
from engine.world import World
from player.character import Character


class Game:
    """Engine-first RPG core: tracks locations, inventory, quests, events, and persistence."""
    SAVE_FILE = "savegame.json"
    SAFE_REST_LOCATIONS = {"village_square", "shop", "inn"}
    IMPORTANT_ITEM_IDS = {"rusty_sword", "wolf_pelt", "guardian_sigil"}
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
        "quests",
        "journal",
        "about",
        "talk",
        "ask",
        "accept",
        "do",
        "buy",
        "save",
        "load",
        "help",
        "quit",
    }
    NLP_COMMAND_TRIGGERS = {"ask", "fight", "inspect", "look", "move", "take", "talk", "use"}
    ACTION_COMMAND_TRIGGERS = {"fight", "move", "take", "use"}

    def __init__(self, data_dir: str = "data", player_name: str = "Hero", character_profile: dict | None = None):
        self.data_dir = data_dir
        self.save_path = Path(self.SAVE_FILE)
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
        self._load_npc_registry()

        self.combat = CombatEngine()
        self.abilities = AbilityEngine()
        self.dice = DiceEngine()
        self.encounters = EncounterEngine()
        self.factions = FactionEngine(self.world.factions)
        self.inventory = InventoryEngine()
        self.quests = QuestEngine(self.world.quests, self.world.items)
        self.intent_parser = IntentParser()
        self.action_router = ActionRouter()
        self.dm_context = DMContextBuilder()
        self.scene_composer = SceneComposer()

        self.running = True
        self._sync_social_state()
        self._record_location_visit(self.current_location)

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
        return [
            Narrator.reputation_change_text(
                change["name"],
                change["change"],
                change["after"],
                change["tier"],
            )
        ]

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
        if item_id not in self.IMPORTANT_ITEM_IDS:
            return
        if self.player.has_event("important_item_acquired", "item_id", item_id):
            return
        self._log_event(
            "important_item_acquired",
            item_id=item_id,
            item_name=self.world.item_name(item_id),
            source=source,
        )

    def _backfill_world_progress_events(self) -> None:
        """Ensure event memory reflects world state (needed for legacy saves without history)."""
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
        if len(npcs_here) == 1:
            return self.quests.quest_offer_lines(
                self.player,
                npcs_here[0],
                world=self.world,
                current_location=self.current_location,
            )
        return [
            quest.get("title", quest_id)
            for quest_id, quest in self.quests.available_quests(
                self.player,
                npcs_here,
                world=self.world,
                current_location=self.current_location,
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
        modifier = self.player.skill_value(skill_name)
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

        level_ups = self.player.gain_xp(amount)
        self._log_event("xp_gained", amount=amount, source=source)
        lines = [
            Narrator.xp_text(
                amount,
                self.player.level,
                self.player.xp,
                self.player.xp_needed_for_next_level(),
            )
        ]

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

        return lines

    def _skill_display_data(self) -> dict[str, dict[str, int | str]]:
        display = {}
        for skill_name in ("athletics", "survival", "lore", "persuasion", "arcana", "stealth"):
            stat_name = self.player.SKILL_STAT_MAP.get(skill_name, "mind")
            display[skill_name] = {
                "proficiency": self.player.skill_proficiency(skill_name),
                "total": self.player.skill_value(skill_name),
                "stat": stat_name,
            }
        return display

    def _ability_name(self, ability_id: str) -> str:
        ability = self.abilities.ABILITIES.get(str(ability_id).strip().lower(), {})
        return str(ability.get("name", str(ability_id).replace("_", " ").title()))

    def _resolve_random_encounter(self, location_id: str) -> list[str]:
        location = self.world.get_location(location_id)
        location_name = location.get("name", location_id)

        if self.world.get_enemies_at(location_id):
            return []

        encounter_entries = self.world.encounter_entries(location_id)
        encounter_entries.extend(self.factions.encounter_modifiers(self.player, location_id))
        encounter = self.encounters.roll_from_table(encounter_entries)
        if not encounter:
            return []

        encounter_type = str(encounter.get("type", "")).strip().lower()
        target = str(encounter.get("target", "")).strip().lower()
        if not target:
            return []

        if encounter_type == "enemy":
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
            if target in self.world.get_npcs_at(location_id):
                return []
            self.world.add_npc(location_id, target)
            encounter_name = "Traveling Merchant" if target == "merchant" else target.replace("_", " ").title()
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
        chance = int(location.get("state_event_chance", 0))
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
        return self._trigger_dynamic_world_state(self.current_location, trigger="action", source=source)

    def _recent_world_events(self) -> list[dict]:
        world_event_types = {"world_state_started", "world_state_cleared", "world_event_resolved"}
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

    def _resolve_random_world_event(self, location_id: str) -> list[str]:
        location = self.world.get_location(location_id)
        location_name = location.get("name", location_id)
        event = self.encounters.roll_world_event(location)
        if not event:
            return []

        event_name = str(event.get("name", event.get("event_id", "World Event")))
        event_type = str(event.get("type", "")).strip().lower()
        skill_name = str(event.get("skill", "survival")).strip().lower()
        dc = int(event.get("dc", 10))
        check = self._skill_check(skill_name, dc)
        roll = check["roll"]
        roll_text = f"{roll['die']} + {roll['modifier']} = {roll['total']} vs DC {dc}"
        social_lines = []

        if event_type == "ambush":
            enemy_id = str(event.get("enemy", "bandit"))
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
        next_objective = self.quests.next_objective(self.player)
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
        chapter_progress = self._chapter_progress()
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
        if command == "quests":
            return self._cmd_quests()
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
        if command == "do":
            return self._cmd_do(arg)
        if command == "buy":
            return self._cmd_buy(arg)
        if command == "save":
            return self._cmd_save()
        if command == "load":
            return self._cmd_load()
        if command == "help":
            return self._cmd_help()
        if command == "quit":
            self.running = False
            return "Goodbye."

        return (
            f"Unknown command: '{command}'. "
            "Type 'help' to see valid commands."
        )

    def _cmd_look(self) -> str:
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

        return Narrator.location_text(
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
        )

    def _cmd_inspect(self, arg: str) -> str:
        if not arg.strip():
            return "Inspect what? Try your location, an item nearby, an item in your backpack, or an NPC here."

        query = self._strip_leading_article(arg.strip())
        query_lower = query.lower()

        if self.world.is_current_location_query(self.current_location, query):
            location = self.world.get_location(self.current_location)
            if self.current_location in {"old_watchtower", "ruined_shrine"}:
                return Narrator.inspect_special_location_text(
                    self.current_location,
                    location,
                    self._history_flags(),
                )
            return Narrator.inspect_location_text(location, self.current_location, self._history_flags())

        lore_object_id = self._find_lore_object_at_location(self.current_location, query)
        if lore_object_id:
            return Narrator.inspect_lore_object_text(
                lore_object_id=lore_object_id,
                location_id=self.current_location,
                history_flags=self._history_flags(),
            )

        inventory_item_id = self.inventory.find_item_in_inventory(self.player, self.world.items, query)
        if inventory_item_id:
            item = self.world.items.get(inventory_item_id, {})
            item_name = self.world.item_name(inventory_item_id)
            item_type = item.get("type", "unknown")
            description = item.get("description", "No details are known about this item yet.")
            return Narrator.inspect_item_text(item_name, item_type, description, "your backpack")

        location_item_id = self.world.find_item_at_location(self.current_location, query)
        if location_item_id:
            item = self.world.items.get(location_item_id, {})
            item_name = self.world.item_name(location_item_id)
            item_type = item.get("type", "unknown")
            description = item.get("description", "No details are known about this item yet.")
            return Narrator.inspect_item_text(item_name, item_type, description, "the ground here")

        npc_id = self._find_visible_npc_at_location(self.current_location, query)
        if npc_id:
            npc_name = self.TALKABLE_NPCS.get(npc_id, npc_id.title())
            location_name = self.world.get_location(self.current_location).get("name", self.current_location)
            return Narrator.inspect_npc_text(npc_name, location_name)

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
        return "\n".join(self.world.map_lines(self.current_location))

    def _cmd_search(self, arg: str) -> str:
        if not arg.strip():
            return "Search what? Try: area, ground, or location."

        target = self.world.normalize_search_target(arg)
        if not target:
            return "You can search only: area, ground, or location."

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
        )

    def _cmd_move(self, arg: str) -> str:
        if not arg:
            exits = self.world.get_location(self.current_location).get("connected_locations", {})
            if not exits:
                return "No exits from here."
            return "Move where? Available exits: " + ", ".join(exits.keys())

        previous_location = self.current_location
        new_location = self.world.find_connected_location(self.current_location, arg)
        if not new_location:
            exits = self.world.get_location(self.current_location).get("connected_locations", {})
            if exits:
                return "You cannot go there from here. Available exits: " + ", ".join(exits.keys())
            return "You cannot go there from here."

        event_count_before = len(self.player.event_log)
        self.world.clear_transient_npcs(previous_location)
        self.current_location = new_location
        self._record_location_visit(self.current_location)
        location = self.world.get_location(self.current_location)
        location_name = location.get("name", self.current_location)
        lines = [Narrator.movement_text(location_name, self.world.get_enemies_at(self.current_location), self.world.get_items_at(self.current_location))]
        lines.extend(self._resolve_random_encounter(self.current_location))
        lines.extend(self._resolve_random_world_event(self.current_location))
        lines.extend(self._trigger_dynamic_world_state(self.current_location, trigger="travel", source="move"))
        lines.extend(self._resolve_location_events(self.current_location))
        if not self.player.is_alive():
            lines.append("Game over.")
            return "\n".join(lines)
        scene_context = self._build_scene_context()
        lines.extend(self.scene_composer.compose_entry_lines(scene_context))
        lines.append(self._cmd_look())
        quest_messages = self.quests.on_location_enter(self.player, self.current_location, self.inventory)
        lines.extend(quest_messages)
        for quest_id in self.quests.recently_completed_quests:
            quest_data = self.quests.quests.get(quest_id, {})
            quest_title = quest_data.get("title", quest_id)
            self._log_event("quest_completed", quest_id=quest_id, quest_title=quest_title)
            lines.extend(self._apply_quest_social_effects(quest_id))
            reward_items = quest_data.get("reward", {}).get("items", [])
            if isinstance(reward_items, list):
                for reward_item_id in reward_items:
                    self._record_important_item_acquired(str(reward_item_id), source="quest_reward")
        transition_text = self._scene_transition_text(self.player.event_log[event_count_before:])
        if transition_text:
            lines.append(transition_text)
        return "\n".join(lines)

    def _cmd_fight(self, arg: str) -> str:
        enemy_id, error = self._find_enemy_here(arg)
        if error:
            return error

        enemy_data = self.world.enemies.get(enemy_id, {})
        enemy_name = self.world.enemy_name(enemy_id)
        player_hp_before = self.player.hp
        enemy_hp_before = int(enemy_data.get("hp", 1))
        event_count_before = len(self.player.event_log)
        result = self.combat.fight(self.player, enemy_id, self.world.enemies, self.world.items)

        lines = [
            Narrator.combat_intro(enemy_name),
            (
                f"Start: Your HP {player_hp_before}/{self.player.max_hp} | "
                f"{enemy_name} HP {enemy_hp_before}"
            ),
        ]
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

        if self.running:
            lines.extend(self._post_action_world_tick("fight"))
        transition_text = self._scene_transition_text(self.player.event_log[event_count_before:])
        if transition_text:
            lines.append(transition_text)
        lines.append(f"End: Your HP {self.player.hp}/{self.player.max_hp} | {enemy_name} HP {result['enemy_hp']}")
        return "\n".join(lines)

    def _cmd_take(self, arg: str) -> str:
        items_here = self.world.get_items_at(self.current_location)
        if not items_here:
            return "There are no items here."

        if arg:
            item_id = self.world.find_item_at_location(self.current_location, arg)
            if not item_id:
                item_names = [self.world.item_name(iid) for iid in items_here]
                return "That item is not here. Items here: " + ", ".join(item_names)
        else:
            item_id = items_here[0]

        event_count_before = len(self.player.event_log)
        self.world.remove_item(self.current_location, item_id)
        self.inventory.add_item(self.player, item_id)
        self._record_important_item_acquired(item_id, source="ground_pickup")

        item_name = self.world.item_name(item_id)
        lines = [Narrator.item_taken(item_name)]
        lines.extend(self.quests.on_item_obtained(self.player, item_id))
        lines.extend(self._post_action_world_tick("take"))
        transition_text = self._scene_transition_text(self.player.event_log[event_count_before:])
        if transition_text:
            lines.append(transition_text)
        return "\n".join(lines)

    def _cmd_inventory(self) -> str:
        lines = [
            "Inventory",
            f"HP: {self.player.hp}/{self.player.max_hp}",
            f"Focus: {self.player.focus}/{self.player.max_focus}",
            f"Defense: {self.player.defense_value(self.world.items)}",
            f"Gold: {self.player.gold}",
        ]
        lines.extend(self.inventory.inventory_lines(self.player, self.world.items))
        return "\n".join(lines)

    def _cmd_stats(self) -> str:
        location_name = self.world.get_location(self.current_location).get("name", self.current_location)
        equipped_weapon = "none"
        if self.player.equipped_weapon:
            equipped_weapon = self.world.item_name(self.player.equipped_weapon)
        equipped_armor = "none"
        if getattr(self.player, "equipped_armor", None):
            equipped_armor = self.world.item_name(self.player.equipped_armor)

        active_quest_summary = "None"
        next_objective = self.quests.next_objective(self.player)
        if next_objective:
            active_quest_summary = (
                f"{next_objective['title']} "
                f"({next_objective['have']}/{next_objective['need']})"
            )

        return (
            "Player Stats\n"
            f"Name: {self.player.name}\n"
            f"Gender: {self.player.gender}\n"
            f"Race: {self.player.race}\n"
            f"Class: {self.player.player_class}\n"
            f"Background: {self.player.background}\n"
            f"Level: {self.player.level}\n"
            f"XP: {self.player.xp}/{self.player.xp_needed_for_next_level()}\n"
            f"HP: {self.player.hp}/{self.player.max_hp}\n"
            f"Focus: {self.player.focus}/{self.player.max_focus}\n"
            f"Attack: {self.player.attack_value(self.world.items)}\n"
            f"Defense: {self.player.defense_value(self.world.items)}\n"
            f"Strength: {self.player.stat_value('strength')}\n"
            f"Agility: {self.player.stat_value('agility')}\n"
            f"Mind: {self.player.stat_value('mind')}\n"
            f"Vitality: {self.player.stat_value('vitality')}\n"
            f"Gold: {self.player.gold}\n"
            f"Location: {location_name}\n"
            f"Equipped weapon: {equipped_weapon}\n"
            f"Equipped armor: {equipped_armor}\n"
            f"Inventory items: {len(self.player.inventory)}\n"
            f"Abilities known: {', '.join(self._ability_name(ability_id) for ability_id in self.player.abilities) or 'none'}\n"
            f"Active quest: {active_quest_summary}"
            + (f"\nBio: {self.player.bio}" if self.player.bio else "")
        )

    def _cmd_skills(self) -> str:
        return Narrator.skills_text(self._skill_display_data())

    def _cmd_abilities(self) -> str:
        return Narrator.abilities_text(
            self.abilities.available_to(self.player),
            self.player.focus,
            self.player.max_focus,
        )

    def _cmd_recap(self) -> str:
        location_name = self.world.get_location(self.current_location).get("name", self.current_location)
        equipped_weapon = "none"
        if self.player.equipped_weapon:
            equipped_weapon = self.world.item_name(self.player.equipped_weapon)

        quest_summary = self.quests.recap_summary(self.player)
        event_counts = self._event_counts()
        chapter_progress = self._chapter_progress()
        return Narrator.recap_text(
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
            chapter_progress=chapter_progress,
            character_context=self._character_lore_context(),
            location_context=self._location_lore_context(),
            history_flags=self._history_flags(),
        )

    def _cmd_story(self) -> str:
        location_name = self.world.get_location(self.current_location).get("name", self.current_location)
        quest_summary = self.quests.story_summary(self.player)
        event_counts = self._event_counts()
        chapter_progress = self._chapter_progress()

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
            chapter_progress=chapter_progress,
            character_context=self._character_lore_context(),
            location_context=self._location_lore_context(),
            history_flags=self._history_flags(),
        )

    def _event_counts(self) -> dict:
        counts = {
            "locations_visited": 0,
            "enemies_defeated": 0,
            "quests_completed": 0,
            "minibosses_defeated": 0,
            "important_items_acquired": 0,
        }

        for event in self.player.event_log:
            event_type = event.get("type")
            if event_type == "location_visited":
                counts["locations_visited"] += 1
            elif event_type == "enemy_defeated":
                counts["enemies_defeated"] += 1
            elif event_type == "quest_completed":
                counts["quests_completed"] += 1
            elif event_type == "miniboss_defeated":
                counts["minibosses_defeated"] += 1
            elif event_type == "important_item_acquired":
                counts["important_items_acquired"] += 1

        return counts

    def _chapter_progress(self) -> dict:
        """Compute lightweight chapter context from major milestones for UI text."""
        history_flags = self._history_flags()

        chapter_title = "Chapter 1: Forest Roads"
        chapter_note = "Push beyond the village and secure the nearby roads."

        if (
            history_flags.get("watchtower_cleared")
            or history_flags.get("watchtower_sweep_completed")
            or history_flags.get("shrine_guardian_defeated")
        ):
            chapter_title = "Chapter 2: Watchtower and Shrine"
            if history_flags.get("shrine_guardian_defeated"):
                chapter_note = "Major milestone: the Shrine Guardian has been defeated."
            elif history_flags.get("watchtower_sweep_completed"):
                chapter_note = "The watchtower threat has been reported and the route is stabilizing."
            else:
                chapter_note = "The watchtower is quieter, and deeper forest mysteries are now in focus."
        elif history_flags.get("forest_path_cleared"):
            chapter_note = "Forest Path danger has been reduced; press deeper toward the watchtower and shrine."

        return {
            "title": chapter_title,
            "note": chapter_note,
        }

    def chapter_context(self) -> dict:
        return self._chapter_progress()

    def history_context(self) -> dict:
        return self._history_flags()

    def current_location_name(self) -> str:
        return self.world.get_location(self.current_location).get("name", self.current_location)

    def _character_lore_context(self) -> dict:
        return {
            "name": self.player.name,
            "race": self.player.race,
            "class": self.player.player_class,
            "background": self.player.background,
            "race_lore": Character.creation_lore("race", self.player.race),
            "class_lore": Character.creation_lore("class", self.player.player_class),
            "background_lore": Character.creation_lore("background", self.player.background),
        }

    def _location_lore_context(self) -> dict:
        location = self.world.get_location(self.current_location)
        states = self.world.get_location_states(self.current_location)
        return {
            "location_name": location.get("name", self.current_location),
            "region": location.get("region", ""),
            "location_lore": location.get("lore", ""),
            "state_names": [state.get("name", state.get("state_id", "State")) for state in states],
            "npcs": self._visible_npc_names_at_location(self.current_location),
        }

    def character_context(self) -> dict:
        summary = self.player.character_summary()
        summary["attack"] = self.player.attack_value(self.world.items)
        summary["inventory"] = [self.world.item_name(item_id) for item_id in self.player.inventory]
        summary["abilities"] = [self._ability_name(ability_id) for ability_id in self.player.abilities]
        summary["race_lore"] = Character.creation_lore("race", self.player.race)
        summary["class_lore"] = Character.creation_lore("class", self.player.player_class)
        summary["background_lore"] = Character.creation_lore("background", self.player.background)
        return summary

    def _find_enemy_here(self, arg: str) -> tuple[str | None, str | None]:
        enemies_here = self.world.get_enemies_at(self.current_location)
        if not enemies_here:
            return None, "There are no enemies here."

        if arg:
            enemy_id = self.world.find_enemy_at_location(self.current_location, arg)
            if not enemy_id:
                enemy_names = [self.world.enemy_name(eid) for eid in enemies_here]
                return None, "That enemy is not here. Enemies here: " + ", ".join(enemy_names)
            return enemy_id, None

        return enemies_here[0], None

    def _resolve_enemy_victory(self, enemy_id: str, enemy_name: str, result: dict, enemy_data: dict) -> list[str]:
        lines = [Narrator.combat_result(True, enemy_name)]
        self.world.remove_enemy(self.current_location, enemy_id)
        self._log_event(
            "enemy_defeated",
            enemy_id=enemy_id,
            enemy_name=enemy_name,
            location_id=self.current_location,
            location_name=self.world.get_location(self.current_location).get("name", self.current_location),
        )
        if enemy_id == "shrine_guardian":
            self._log_event(
                "miniboss_defeated",
                enemy_id=enemy_id,
                enemy_name=enemy_name,
                location_id=self.current_location,
                location_name=self.world.get_location(self.current_location).get("name", self.current_location),
            )

        for item_id in result["loot"]:
            self.inventory.add_item(self.player, item_id)
            self._record_important_item_acquired(item_id, source="combat_loot")
        loot_names = [self.world.item_name(item_id) for item_id in result["loot"]]
        lines.append(Narrator.loot_text(loot_names))

        reward_text = enemy_data.get("reward_text")
        if reward_text:
            lines.append(str(reward_text))

        for item_id in result["loot"]:
            lines.extend(self.quests.on_item_obtained(self.player, item_id))

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
        lines.extend(
            self.quests.on_enemy_defeated(
                self.player,
                enemy_id,
                self.current_location,
                self.inventory,
            )
        )
        return lines

    def _cmd_history(self) -> str:
        return Narrator.history_text(self.player.event_log)

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
        )

        next_objective = self.quests.next_objective(self.player)
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

        was_injured = self.player.hp < self.player.max_hp or self.player.focus < self.player.max_focus
        self.player.hp = self.player.max_hp
        self.player.focus = self.player.max_focus
        lines = [
            Narrator.rest_text(
                location_name,
                self.player.hp,
                self.player.max_hp,
                self.player.focus,
                self.player.max_focus,
                was_injured,
            )
        ]
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
            return "Cast what?\n" + Narrator.abilities_text(available, self.player.focus, self.player.max_focus)

        ability, target_text = self.abilities.parse_player_input(self.player, arg)
        if not ability:
            return "You do not know that ability.\n" + Narrator.abilities_text(available, self.player.focus, self.player.max_focus)

        cost = int(ability.get("cost", 0))
        if self.player.focus < cost:
            return f"Not enough focus for {ability['name']}. Focus: {self.player.focus}/{self.player.max_focus}."

        event_count_before = len(self.player.event_log)
        effect = ability.get("effect", {})
        lines = []

        if ability.get("target") == "self":
            self.player.spend_focus(cost)
            healed = self.player.heal(int(effect.get("heal", 0)))
            if healed > 0:
                lines.append(
                    Narrator.ability_text(
                        ability["name"],
                        f"You recover {healed} HP. HP {self.player.hp}/{self.player.max_hp}. Focus {self.player.focus}/{self.player.max_focus}.",
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
        opening_damage = max(0, int(effect.get("damage", 0)) + max(0, self.player.stat_modifier("mind")))
        enemy_hp_after = max(0, enemy_hp_before - opening_damage)
        self.player.spend_focus(cost)
        lines.append(
            Narrator.ability_text(
                ability["name"],
                f"You hit {enemy_name} for {opening_damage} opening damage. Focus {self.player.focus}/{self.player.max_focus}.",
            )
        )

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
            lines.append(
                f"Start: Your HP {player_hp_before}/{self.player.max_hp} | "
                f"{enemy_name} HP {enemy_hp_after}/{enemy_hp_before}"
            )
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

        if self.running:
            lines.extend(self._post_action_world_tick("cast"))
        transition_text = self._scene_transition_text(self.player.event_log[event_count_before:])
        if transition_text:
            lines.append(transition_text)
        lines.append(f"End: Your HP {self.player.hp}/{self.player.max_hp} | {enemy_name} HP {result['enemy_hp']}")
        return "\n".join(lines)

    def _cmd_quests(self) -> str:
        return "Quest Log\n" + "\n".join(
            self.quests.list_quests(
                self.player,
                self._visible_npcs_at_location(self.current_location),
                world=self.world,
                current_location=self.current_location,
            )
        )

    def _cmd_journal(self) -> str:
        return "\n".join(self.quests.journal_lines(self.player, world=self.world, current_location=self.current_location))

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
        )
        return Narrator.npc_dialogue_text(npc_name, role, dialogue, offers)

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

        return Narrator.ask_text(npc_query, topic, self._history_flags())

    def _cmd_accept(self, arg: str) -> str:
        npcs_here = self._visible_npcs_at_location(self.current_location)
        accepted, lines, quest_id = self.quests.accept_quest(
            self.player,
            arg,
            npcs_here,
            self.inventory,
            world=self.world,
            current_location=self.current_location,
        )
        if accepted and quest_id:
            quest_data = self.quests.quests.get(quest_id, {})
            self._log_event(
                "quest_accepted",
                quest_id=quest_id,
                quest_title=quest_data.get("title", quest_id),
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
            if not isinstance(stock, list) or not stock:
                continue
            shops.append(
                {
                    "npc_id": npc_id,
                    "name": self.world.npc_name(npc_id),
                    "faction": str(npc_data.get("faction", "")).strip().lower(),
                    "stock": [str(item_id).strip().lower() for item_id in stock if str(item_id).strip()],
                }
            )
        return shops

    def _shop_stock_lines(self, shop: dict) -> list[str]:
        lines = []
        for item_id in shop["stock"]:
            item = self.world.items.get(item_id, {})
            base_cost = self.inventory.item_price(item_id, self.world.items)
            price = self.factions.price_for_service(self.player, shop["faction"], shop["npc_id"], base_cost)
            item_name = item.get("name", item_id.replace("_", " ").title())
            item_type = item.get("type", "item")
            lines.append(f"- {item_name} ({item_type}) - {price} gold")
        return lines

    def _cmd_buy(self, arg: str) -> str:
        shops = self._local_shop_npcs()
        if not shops:
            return "You cannot buy here: no vendor is offering goods in this location."

        if not arg:
            lines = []
            for shop in shops:
                allowed, denial = self.factions.service_access(self.player, shop["faction"], shop["npc_id"])
                lines.append(f"{shop['name']} offers:")
                if not allowed:
                    lines.append(f"- {denial}")
                    continue
                lines.extend(self._shop_stock_lines(shop))
            lines.append("Use 'buy <item>' to purchase something from a local vendor.")
            return "\n".join(lines)

        selected_shop = None
        item_id = None
        for shop in shops:
            resolved = self.inventory.resolve_shop_item(self.world.items, arg, stock=shop["stock"])
            if not resolved:
                continue
            selected_shop = shop
            item_id = resolved
            break

        if not selected_shop or not item_id:
            lines = ["Nothing here matches that purchase request. Local stock:"]
            for shop in shops:
                lines.append(f"{shop['name']}:")
                lines.extend(self._shop_stock_lines(shop))
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

    def _save_data(self) -> dict:
        return {
            "player": self.player.to_dict(),
            "current_location": self.current_location,
            "quests": self.quests.to_dict(),
            "world_state": self.world.state_to_dict(),
        }

    def _cmd_save(self) -> str:
        data = self._save_data()
        try:
            self.save_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as exc:
            return f"Could not save game: {exc}"
        return f"Game saved to {self.save_path}."

    def _cmd_load(self) -> str:
        if not self.save_path.exists():
            return f"No save file found at {self.save_path}."

        try:
            raw = self.save_path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except OSError as exc:
            return f"Could not load game: {exc}"
        except json.JSONDecodeError:
            return f"Could not load game: {self.save_path} is not valid JSON."

        if not isinstance(data, dict):
            return "Could not load game: save data format is invalid."

        # Reset world and engines to avoid carrying over runtime changes.
        self.world = World(self.data_dir)
        self._load_npc_registry()
        self.combat = CombatEngine()
        self.abilities = AbilityEngine()
        self.dice = DiceEngine()
        self.encounters = EncounterEngine()
        self.factions = FactionEngine(self.world.factions)
        self.inventory = InventoryEngine()
        self.quests = QuestEngine(self.world.quests, self.world.items)

        self.player = Character.from_dict(data.get("player", {}))
        self._sync_social_state()

        saved_location = str(data.get("current_location", self.world.starting_location))
        if saved_location not in self.world.locations:
            self.current_location = self.world.starting_location
            location_note = " Saved location was invalid, so you were moved to the starting area."
        else:
            self.current_location = saved_location
            location_note = ""

        quests_data = data.get("quests", {})
        if isinstance(quests_data, dict):
            self.quests.load_from_dict(quests_data)

        world_state = data.get("world_state", {})
        if isinstance(world_state, dict):
            self.world.load_state_from_dict(world_state)

        self._backfill_world_progress_events()
        self._record_location_visit(self.current_location)

        location_name = self.world.get_location(self.current_location).get("name", self.current_location)
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
            "inspect <target>   - Focus on an item, NPC, or your surroundings.\n"
            "search <target>    - List visible items, enemies, NPCs, and exits.\n"
            "map                - Outline every location and its exits.\n"
            "move <exit>        - Travel to a connected area (e.g. move forest).\n"
            "fight [enemy]      - Engage a nearby enemy (defaults to the first).\n"
            "take [item]        - Pick up a nearby item.\n"
            "talk <npc>         - Converse with an NPC who is present.\n"
            "ask <npc> about <topic> - Ask a present NPC about a topic.\n"
            "accept <quest>     - Accept a quest offered by an NPC in your current location.\n"
            "do <free text>     - Optional wrapper for safe narrative input like observe, ask, or listen.\n"
            "free text          - You can also type lines like 'look around', 'go to the forest', or 'attack the slime'.\n"
            "buy <item>         - Purchase from a local vendor in your current location.\n"
            "\n"
            "inventory          - See HP, gold, carried items, and weapon.\n"
            "stats              - Snapshot core stats, focus, and next quest target.\n"
            "skills             - Show your skill totals and proficiencies.\n"
            "abilities          - List your class abilities and spells.\n"
            "recap              - Recap your location, resources, and quests.\n"
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
            "cast <ability>     - Use a known spell or class ability.\n"
            "quests             - Show raw quest progress and completion.\n"
            "journal            - Read each quest's story and progress.\n"
            "about              - Explain engine rules vs AI narration.\n"
            "\n"
            "save               - Persist your run to `savegame.json`.\n"
            "load               - Resume from a previous save.\n"
            "help               - Show this command list again.\n"
            "quit               - Exit Valerion."
        )
