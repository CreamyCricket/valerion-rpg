from player.character import Character
from ai.narrator import Narrator


class QuestEngine:
    """Tracks quest offers, acceptance, progress, completion, and rewards."""

    def __init__(self, quests_data: dict, items_data: dict):
        self.quests = quests_data
        self.items = items_data
        self.progress = {quest_id: 0 for quest_id in quests_data}
        self.accepted = set()
        self.completed = set()
        self.demo_complete_shown = False
        self.recently_completed_quests = []

    @staticmethod
    def _fallback_name(entity_id: str) -> str:
        return entity_id.replace("_", " ").title()

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(str(text).strip().lower().split())

    def _item_name(self, item_id: str) -> str:
        return self.items.get(item_id, {}).get("name", self._fallback_name(item_id))

    def _turn_in_name(self, objective: dict) -> str:
        turn_in = str(objective.get("turn_in", "village_square"))
        return self._fallback_name(turn_in)

    @staticmethod
    def _event_requirement_met(player: Character, requirement: dict) -> bool:
        if not isinstance(requirement, dict):
            return True

        event_type = str(requirement.get("type", "")).strip().lower()
        details = requirement.get("details", {})
        if not event_type:
            return True
        if not isinstance(details, dict):
            details = {}
        if not details:
            return player.has_event(event_type)

        for key, value in details.items():
            if not player.has_event(event_type, str(key), value):
                return False
        return True

    @staticmethod
    def _world_state_requirement_met(world, current_location: str | None, requirement: dict) -> bool:
        if world is None or not isinstance(requirement, dict):
            return True

        state_id = str(requirement.get("state", "")).strip().lower()
        if not state_id:
            return True

        location_id = str(requirement.get("location", current_location or "")).strip().lower()
        if not location_id:
            return True

        return world.has_location_state(location_id, state_id)

    @classmethod
    def _world_state_blocked(cls, world, current_location: str | None, requirement: dict) -> bool:
        return cls._world_state_requirement_met(world, current_location, requirement)

    @staticmethod
    def _reputation_requirement_met(player: Character, requirement: dict) -> bool:
        if not isinstance(requirement, dict):
            return True

        faction_id = str(requirement.get("faction", "")).strip().lower()
        if not faction_id:
            return True
        minimum = int(requirement.get("min", 0))
        return player.reputation_value(faction_id) >= minimum

    @staticmethod
    def _npc_trust_requirement_met(player: Character, requirement: dict) -> bool:
        if not isinstance(requirement, dict):
            return True

        npc_id = str(requirement.get("npc", "")).strip().lower()
        if not npc_id:
            return True
        minimum = int(requirement.get("min", 0))
        return player.npc_trust(npc_id) >= minimum

    @staticmethod
    def _campaign_requirement_met(quest: dict, campaign_context: dict | None) -> bool:
        if not isinstance(quest, dict):
            return True

        minimum_arc = int(quest.get("min_arc", 0) or 0)
        maximum_arc = int(quest.get("max_arc", 0) or 0)
        if minimum_arc <= 0 and maximum_arc <= 0:
            return True

        campaign_context = campaign_context or {}
        current_arc_index = int(campaign_context.get("index", 1) or 1)
        if minimum_arc > 0 and current_arc_index < minimum_arc:
            return False
        if maximum_arc > 0 and current_arc_index > maximum_arc:
            return False
        return True

    def _is_available(
        self,
        player: Character,
        quest: dict,
        world=None,
        current_location: str | None = None,
        campaign_context: dict | None = None,
    ) -> bool:
        if not self._campaign_requirement_met(quest, campaign_context):
            return False

        requirements = quest.get("requires_events", [])
        if isinstance(requirements, list) and requirements:
            if not all(self._event_requirement_met(player, requirement) for requirement in requirements):
                return False

        state_requirements = quest.get("requires_world_states", [])
        if isinstance(state_requirements, list) and state_requirements:
            if not all(self._world_state_requirement_met(world, current_location, requirement) for requirement in state_requirements):
                return False

        blocked_states = quest.get("blocks_world_states", [])
        if isinstance(blocked_states, list) and blocked_states:
            if any(self._world_state_blocked(world, current_location, requirement) for requirement in blocked_states):
                return False

        reputation_requirements = quest.get("requires_reputation", [])
        if isinstance(reputation_requirements, list) and reputation_requirements:
            if not all(self._reputation_requirement_met(player, requirement) for requirement in reputation_requirements):
                return False

        trust_requirements = quest.get("requires_npc_trust", [])
        if isinstance(trust_requirements, list) and trust_requirements:
            if not all(self._npc_trust_requirement_met(player, requirement) for requirement in trust_requirements):
                return False

        return True

    @staticmethod
    def _requires_acceptance(quest: dict) -> bool:
        return bool(quest.get("requires_acceptance", False))

    def _is_active(
        self,
        player: Character,
        quest_id: str,
        quest: dict,
        world=None,
        current_location: str | None = None,
        campaign_context: dict | None = None,
    ) -> bool:
        if quest_id in self.completed:
            return False
        if self._requires_acceptance(quest) and quest_id in self.accepted:
            return True
        if not self._is_available(
            player,
            quest,
            world=world,
            current_location=current_location,
            campaign_context=campaign_context,
        ):
            return False
        return not self._requires_acceptance(quest)

    def available_quests(
        self,
        player: Character,
        npc_ids: list[str] | None = None,
        world=None,
        current_location: str | None = None,
        campaign_context: dict | None = None,
    ) -> list[tuple[str, dict]]:
        if npc_ids is None:
            npc_filter = None
        else:
            npc_filter = {str(npc_id).strip().lower() for npc_id in npc_ids}
            if not npc_filter:
                return []
        offered = []
        for quest_id, quest in self.quests.items():
            if quest_id in self.completed or quest_id in self.accepted:
                continue
            if not self._requires_acceptance(quest):
                continue
            if not self._is_available(
                player,
                quest,
                world=world,
                current_location=current_location,
                campaign_context=campaign_context,
            ):
                continue
            giver = str(quest.get("giver", "")).strip().lower()
            if npc_filter is not None and giver not in npc_filter:
                continue
            offered.append((quest_id, quest))
        return offered

    def quest_offer_lines(
        self,
        player: Character,
        npc_id: str,
        world=None,
        current_location: str | None = None,
        campaign_context: dict | None = None,
    ) -> list[str]:
        offered = self.available_quests(
            player,
            [npc_id],
            world=world,
            current_location=current_location,
            campaign_context=campaign_context,
        )
        return [quest.get("title", quest_id) for quest_id, quest in offered]

    def accept_quest(
        self,
        player: Character,
        quest_query: str,
        npc_ids: list[str],
        inventory_engine,
        world=None,
        current_location: str | None = None,
        campaign_context: dict | None = None,
    ) -> tuple[bool, list[str], str | None]:
        offered = self.available_quests(
            player,
            npc_ids,
            world=world,
            current_location=current_location,
            campaign_context=campaign_context,
        )
        if not offered:
            return False, ["No quests are being offered here right now."], None

        if not quest_query.strip():
            if len(offered) == 1:
                quest_id, quest = offered[0]
            else:
                titles = [quest.get("title", quest_id) for quest_id, quest in offered]
                return False, ["Accept which quest? Available: " + ", ".join(titles)], None
        else:
            normalized = self._normalize(quest_query)
            match = None
            for quest_id, quest in offered:
                title = self._normalize(quest.get("title", quest_id))
                if normalized == quest_id.lower() or normalized == title:
                    match = (quest_id, quest)
                    break
            if match is None:
                titles = [quest.get("title", quest_id) for quest_id, quest in offered]
                return False, ["That quest is not being offered here. Available: " + ", ".join(titles)], None
            quest_id, quest = match

        self.accepted.add(quest_id)
        lines = [f"Quest accepted: {quest.get('title', quest_id)}."]
        for item_id in quest.get("starting_items", []):
            inventory_engine.add_item(player, item_id)
            lines.append(f"Received quest item: {self._item_name(item_id)}.")
        return True, lines, quest_id

    def list_quests(
        self,
        player: Character,
        npc_ids: list[str] | None = None,
        world=None,
        current_location: str | None = None,
        campaign_context: dict | None = None,
    ) -> list[str]:
        offered = self.available_quests(
            player,
            npc_ids,
            world=world,
            current_location=current_location,
            campaign_context=campaign_context,
        )
        active = []
        completed = []

        for quest_id, quest in self.quests.items():
            if quest_id in self.completed:
                completed.append(quest.get("title", quest_id))
                continue
            if not self._is_active(
                player,
                quest_id,
                quest,
                world=world,
                current_location=current_location,
                campaign_context=campaign_context,
            ):
                continue
            title = quest.get("title", quest_id)
            objective = quest.get("objective", {})
            count = int(objective.get("count", 1))
            done = self.progress.get(quest_id, 0)
            status = "Ready to turn in" if done >= count else "In progress"
            active.append(f"{title} | {status} | {done}/{count}")

        lines = ["Offered quests:"]
        if offered:
            lines.extend(f"- {quest.get('title', quest_id)}" for quest_id, quest in offered)
        else:
            lines.append("- none")

        lines.append("Active quests:")
        if active:
            lines.extend(f"- {line}" for line in active)
        else:
            lines.append("- none")

        lines.append("Completed quests:")
        if completed:
            lines.extend(f"- {title}" for title in completed)
        else:
            lines.append("- none")

        return lines

    def journal_lines(
        self,
        player: Character,
        npc_ids: list[str] | None = None,
        world=None,
        current_location: str | None = None,
        campaign_context: dict | None = None,
    ) -> list[str]:
        completed_lines = []

        for quest_id, quest in self.quests.items():
            if quest_id in self.completed:
                completed_lines.append(f"- {quest.get('title', quest_id)}")

        if not completed_lines:
            return ["Journal", "No completed quests recorded yet."]

        return ["Journal", *completed_lines]

    def recap_summary(self, player: Character, campaign_context: dict | None = None) -> dict:
        active = []
        completed = []

        for quest_id, quest in self.quests.items():
            if quest_id in self.completed:
                completed.append(quest.get("title", quest_id))
                continue
            if not self._is_active(player, quest_id, quest, campaign_context=campaign_context):
                continue

            title = quest.get("title", quest_id)
            objective = quest.get("objective", {})
            need = int(objective.get("count", 1))
            have = self.progress.get(quest_id, 0)
            status = "Ready to turn in" if have >= need else "In progress"
            active.append(f"{title} ({have}/{need}) - {status}")

        return {
            "active": active,
            "completed": completed,
            "demo_complete": self.demo_complete_shown,
        }

    def story_summary(self, player: Character, campaign_context: dict | None = None) -> dict:
        active = []
        completed = []
        important_progress = []

        for quest_id, quest in self.quests.items():
            if quest_id in self.completed:
                completed.append(quest.get("title", quest_id))
                continue
            if not self._is_active(player, quest_id, quest, campaign_context=campaign_context):
                continue

            title = quest.get("title", quest_id)
            objective = quest.get("objective", {})
            need = int(objective.get("count", 1))
            have = self.progress.get(quest_id, 0)
            summary = self._objective_summary(objective, have, need)
            active.append(f"{title}: {summary}")

            if have >= need:
                important_progress.append(f"{title} is ready to turn in.")
            elif have > 0:
                important_progress.append(f"{title} has advanced to {have}/{need}.")

        return {
            "active": active,
            "completed": completed,
            "important_progress": important_progress,
        }

    def _objective_summary(self, objective: dict, have: int, need: int) -> str:
        objective_type = objective.get("type")

        if objective_type == "defeat_enemy":
            enemy_name = self._fallback_name(str(objective.get("enemy", "enemy")))
            location_name = self._fallback_name(str(objective.get("location", "unknown location")))
            suffix = ", ready to turn in" if have >= need else ""
            return f"defeat {enemy_name} at {location_name} ({have}/{need}{suffix})"

        if objective_type == "bring_item":
            item_name = self._item_name(str(objective.get("item", "item")))
            turn_in_name = self._turn_in_name(objective)
            suffix = ", ready to turn in" if have >= need else ""
            return f"bring {item_name} to {turn_in_name} ({have}/{need}{suffix})"

        if objective_type == "visit_location":
            location_name = self._fallback_name(str(objective.get("location", "unknown location")))
            suffix = ", ready to turn in" if have >= need else ""
            return f"reach {location_name} ({have}/{need}{suffix})"

        return f"progress {have}/{need}"

    def next_objective(self, player: Character, campaign_context: dict | None = None) -> dict | None:
        for quest_id, quest in self.quests.items():
            if not self._is_active(player, quest_id, quest, campaign_context=campaign_context):
                continue

            objective = quest.get("objective", {})
            need = int(objective.get("count", 1))
            have = self.progress.get(quest_id, 0)
            turn_in = objective.get("turn_in", "village_square")
            return {
                "quest_id": quest_id,
                "title": quest.get("title", quest_id),
                "objective": objective,
                "have": have,
                "need": need,
                "ready_to_turn_in": have >= need,
                "turn_in": turn_in,
            }
        return None

    def on_item_obtained(self, player: Character, item_id: str) -> list[str]:
        messages = []

        for quest_id, quest in self.quests.items():
            if not self._is_active(player, quest_id, quest):
                continue

            objective = quest.get("objective", {})
            if objective.get("type") != "bring_item":
                continue
            if objective.get("item") != item_id:
                continue

            need = int(objective.get("count", 1))
            previous = self.progress.get(quest_id, 0)
            have_item = player.inventory.count(item_id)
            self.progress[quest_id] = min(need, have_item)

            if self.progress[quest_id] > previous:
                messages.append(f"Quest progress: {quest.get('title', quest_id)} ({self.progress[quest_id]}/{need})")
                if self.progress[quest_id] >= need:
                    messages.append(
                        f"Objective complete: {quest.get('title', quest_id)}. "
                        f"Return to {self._turn_in_name(objective)} to finish the quest."
                    )

        return messages

    def on_enemy_defeated(self, player: Character, enemy_id: str, location_id: str, inventory_engine) -> list[str]:
        messages = []

        for quest_id, quest in self.quests.items():
            if not self._is_active(player, quest_id, quest):
                continue

            objective = quest.get("objective", {})
            if objective.get("type") != "defeat_enemy":
                continue
            if objective.get("enemy") != enemy_id or objective.get("location") != location_id:
                continue

            need = int(objective.get("count", 1))
            self.progress[quest_id] = min(need, self.progress.get(quest_id, 0) + 1)
            have = self.progress[quest_id]
            messages.append(f"Quest progress: {quest.get('title', quest_id)} ({have}/{need})")
            if have >= need:
                messages.append(
                    f"Objective complete: {quest.get('title', quest_id)}. "
                    f"Return to {self._turn_in_name(objective)} to finish the quest."
                )

        return messages

    def on_location_enter(self, player: Character, location_id: str, inventory_engine) -> list[str]:
        messages = []
        self.recently_completed_quests = []

        for quest_id, quest in self.quests.items():
            if not self._is_active(player, quest_id, quest):
                continue

            objective = quest.get("objective", {})
            objective_type = objective.get("type")
            need = int(objective.get("count", 1))

            if objective_type == "bring_item":
                item_id = objective.get("item", "")
                if item_id:
                    self.progress[quest_id] = min(need, player.inventory.count(item_id))

            if objective_type == "visit_location" and location_id == objective.get("location"):
                previous = self.progress.get(quest_id, 0)
                self.progress[quest_id] = need
                if previous < need:
                    messages.append(f"Quest progress: {quest.get('title', quest_id)} ({need}/{need})")
                    if location_id != objective.get("turn_in"):
                        messages.append(
                            f"Objective complete: {quest.get('title', quest_id)}. "
                            f"Return to {self._turn_in_name(objective)} to finish the quest."
                        )

            have = self.progress.get(quest_id, 0)
            if have < need:
                continue

            turn_in_location = objective.get("turn_in", "village_square")
            if location_id != turn_in_location:
                continue

            self.completed.add(quest_id)
            self.recently_completed_quests.append(quest_id)
            reward = quest.get("reward", {})
            gold = int(reward.get("gold", 0))
            player.gold += gold
            if objective_type == "bring_item":
                item_id = objective.get("item", "")
                for _ in range(need):
                    if item_id in player.inventory:
                        player.inventory.remove(item_id)
            for item_id in reward.get("items", []):
                inventory_engine.add_item(player, item_id)

            reward_parts = []
            if gold:
                reward_parts.append(f"{gold} gold")
            if reward.get("items"):
                reward_items = [self._item_name(item_id) for item_id in reward.get("items", [])]
                reward_parts.append("items: " + ", ".join(reward_items))
            reward_text = "; ".join(reward_parts) if reward_parts else "no reward"
            messages.append(f"Quest completed: {quest.get('title', quest_id)}.")
            messages.append(f"Reward received: {reward_text}.")

        if self.quests and len(self.completed) == len(self.quests) and not self.demo_complete_shown:
            messages.append(Narrator.demo_complete_text())
            self.demo_complete_shown = True

        return messages

    def to_dict(self) -> dict:
        return {
            "progress": dict(self.progress),
            "accepted": sorted(self.accepted),
            "completed": sorted(self.completed),
            "demo_complete_shown": self.demo_complete_shown,
        }

    def load_from_dict(self, data: dict) -> None:
        progress_data = data.get("progress", {})
        if not isinstance(progress_data, dict):
            progress_data = {}

        loaded_progress = {}
        for quest_id in self.quests:
            value = progress_data.get(quest_id, 0)
            try:
                loaded_progress[quest_id] = max(0, int(value))
            except (TypeError, ValueError):
                loaded_progress[quest_id] = 0
        self.progress = loaded_progress

        accepted_data = data.get("accepted", [])
        if not isinstance(accepted_data, list):
            accepted_data = []
        self.accepted = {quest_id for quest_id in accepted_data if quest_id in self.quests}

        completed_data = data.get("completed", [])
        if not isinstance(completed_data, list):
            completed_data = []
        self.completed = {quest_id for quest_id in completed_data if quest_id in self.quests}

        for quest_id, value in self.progress.items():
            if value > 0 and quest_id not in self.completed:
                self.accepted.add(quest_id)

        self.demo_complete_shown = bool(data.get("demo_complete_shown", False))
        self.recently_completed_quests = []
