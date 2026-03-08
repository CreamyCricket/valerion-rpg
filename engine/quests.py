from player.character import Character
from ai.narrator import Narrator


class QuestEngine:
    """Tracks quest offers, acceptance, progress, completion, and rewards."""

    def __init__(self, quests_data: dict, items_data: dict):
        self.quests = quests_data
        self.items = items_data
        self.progress = {quest_id: {"stage": 0, "count": 0} for quest_id in quests_data}
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

    @staticmethod
    def _normalize_query(text: str) -> str:
        normalized = " ".join(str(text).strip().lower().split())
        for prefix in ("the ", "a ", "an "):
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
        for suffix in (" quest", " job", " task", " contract"):
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)].strip()
        return normalized

    def _item_name(self, item_id: str) -> str:
        return self.items.get(item_id, {}).get("name", self._fallback_name(item_id))

    def _turn_in_name(self, objective: dict) -> str:
        turn_in = str(objective.get("turn_in", "village_square"))
        return self._fallback_name(turn_in)

    def _progress_entry(self, quest_id: str) -> dict:
        entry = self.progress.get(quest_id, {"stage": 0, "count": 0})
        if isinstance(entry, dict):
            stage = int(entry.get("stage", 0) or 0)
            count = int(entry.get("count", 0) or 0)
        else:
            stage = 0
            try:
                count = int(entry)
            except (TypeError, ValueError):
                count = 0
        return {"stage": max(0, stage), "count": max(0, count)}

    def _set_progress(self, quest_id: str, stage: int, count: int) -> None:
        self.progress[quest_id] = {"stage": max(0, int(stage)), "count": max(0, int(count))}

    def _steps_for(self, quest: dict) -> list[dict]:
        steps = quest.get("steps", [])
        if isinstance(steps, list) and steps:
            return [step for step in steps if isinstance(step, dict)]

        objective = quest.get("objective", {})
        if not isinstance(objective, dict) or not objective:
            return []
        return [
            {
                "title": str(quest.get("title", "")).strip(),
                "description": str(quest.get("description", "")).strip(),
                "objective": objective,
            }
        ]

    def _turn_in_location(self, step: dict, objective: dict) -> str:
        if isinstance(step, dict):
            step_turn_in = str(step.get("turn_in", "")).strip().lower()
            if step_turn_in:
                return step_turn_in
        return str(objective.get("turn_in", "")).strip().lower()

    def _turn_in_npc(self, step: dict) -> str:
        return str(step.get("turn_in_npc", "")).strip().lower()

    def _current_stage(self, quest_id: str, quest: dict) -> dict | None:
        steps = self._steps_for(quest)
        if not steps:
            return None
        entry = self._progress_entry(quest_id)
        stage_index = entry["stage"]
        if stage_index >= len(steps):
            return None
        step = steps[stage_index]
        objective = step.get("objective", {}) if isinstance(step, dict) else {}
        if not isinstance(objective, dict):
            objective = {}
        need = int(objective.get("count", 1))
        return {
            "index": stage_index,
            "total": len(steps),
            "step": step,
            "objective": objective,
            "need": max(1, need),
            "have": entry["count"],
        }

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

    def _skill_requirement_met(self, player: Character, requirement: dict) -> bool:
        if not isinstance(requirement, dict):
            return True

        skill_name = str(requirement.get("skill", "")).strip().lower()
        if not skill_name:
            return True
        minimum = int(requirement.get("min", requirement.get("value", 0)))
        return player.skill_value(skill_name, self.items) >= minimum

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

    def _quest_requirement_met(self, requirement) -> bool:
        if isinstance(requirement, str):
            quest_id = requirement.strip().lower()
            return bool(quest_id) and quest_id in self.completed
        if not isinstance(requirement, dict):
            return True

        quest_id = str(requirement.get("quest_id", "")).strip().lower()
        if not quest_id:
            return True

        require_completed = requirement.get("completed", True)
        min_stage = requirement.get("min_stage")
        if require_completed and quest_id not in self.completed:
            return False
        if min_stage is not None:
            entry = self._progress_entry(quest_id)
            if quest_id not in self.completed and entry["stage"] < int(min_stage):
                return False
        return True

    def _requirements_met(
        self,
        player: Character,
        data: dict,
        world=None,
        current_location: str | None = None,
        campaign_context: dict | None = None,
    ) -> bool:
        if not self._campaign_requirement_met(data, campaign_context):
            return False

        quest_requirements = data.get("requires_quests", [])
        if isinstance(quest_requirements, list) and quest_requirements:
            if not all(self._quest_requirement_met(requirement) for requirement in quest_requirements):
                return False

        requirements = data.get("requires_events", [])
        if isinstance(requirements, list) and requirements:
            if not all(self._event_requirement_met(player, requirement) for requirement in requirements):
                return False

        state_requirements = data.get("requires_world_states", [])
        if isinstance(state_requirements, list) and state_requirements:
            if not all(self._world_state_requirement_met(world, current_location, requirement) for requirement in state_requirements):
                return False

        blocked_states = data.get("blocks_world_states", [])
        if isinstance(blocked_states, list) and blocked_states:
            if any(self._world_state_blocked(world, current_location, requirement) for requirement in blocked_states):
                return False

        reputation_requirements = data.get("requires_reputation", [])
        if isinstance(reputation_requirements, list) and reputation_requirements:
            if not all(self._reputation_requirement_met(player, requirement) for requirement in reputation_requirements):
                return False

        trust_requirements = data.get("requires_npc_trust", [])
        if isinstance(trust_requirements, list) and trust_requirements:
            if not all(self._npc_trust_requirement_met(player, requirement) for requirement in trust_requirements):
                return False

        skill_requirements = data.get("requires_skills", [])
        if isinstance(skill_requirements, list) and skill_requirements:
            if not all(self._skill_requirement_met(player, requirement) for requirement in skill_requirements):
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
        if not self._requirements_met(
            player,
            quest,
            world=world,
            current_location=current_location,
            campaign_context=campaign_context,
        ):
            return False

        steps = self._steps_for(quest)
        if steps and not self._stage_requirements_met(
            player,
            steps[0],
            world=world,
            current_location=current_location,
            campaign_context=campaign_context,
        ):
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

    def _stage_requirements_met(
        self,
        player: Character,
        step: dict,
        world=None,
        current_location: str | None = None,
        campaign_context: dict | None = None,
    ) -> bool:
        if not isinstance(step, dict):
            return True
        return self._requirements_met(
            player,
            step,
            world=world,
            current_location=current_location,
            campaign_context=campaign_context,
        )

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
        return [self._offer_line(quest_id, quest) for quest_id, quest in offered]

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
            normalized = self._normalize_query(quest_query)
            match = None
            candidates = []
            for quest_id, quest in offered:
                title = self._normalize(quest.get("title", quest_id))
                if normalized == quest_id.lower() or normalized == title:
                    match = (quest_id, quest)
                    break
                if normalized and (normalized in title or title in normalized):
                    candidates.append((quest_id, quest))
            if match is None:
                if len(candidates) == 1:
                    match = candidates[0]
                elif len(candidates) > 1:
                    titles = [quest.get("title", quest_id) for quest_id, quest in candidates]
                    return False, ["Accept which quest? Matches: " + ", ".join(titles)], None
            if match is None:
                titles = [quest.get("title", quest_id) for quest_id, quest in offered]
                return False, ["That quest is not being offered here. Available: " + ", ".join(titles)], None
            quest_id, quest = match

        self.accepted.add(quest_id)
        lines = [f"Quest accepted: {quest.get('title', quest_id)}."]
        for item_id in quest.get("starting_items", []):
            inventory_engine.add_item(player, item_id)
            lines.append(f"Received quest item: {self._item_name(item_id)}.")
        stage = self._current_stage(quest_id, quest)
        if stage:
            summary = self._objective_summary(stage["objective"], stage["have"], stage["need"])
            lines.append(f"Next: {summary}.")
        return True, lines, quest_id

    def _turn_in_label(self, step: dict, objective: dict) -> str:
        location_id = self._turn_in_location(step, objective)
        npc_id = self._turn_in_npc(step)
        if not location_id and not npc_id:
            return ""
        if location_id and npc_id:
            return f"{self._fallback_name(location_id)} ({self._fallback_name(npc_id)})"
        if location_id:
            return self._fallback_name(location_id)
        return self._fallback_name(npc_id)

    def _offer_line(self, quest_id: str, quest: dict) -> str:
        title = quest.get("title", quest_id)
        stage = self._current_stage(quest_id, quest)
        if not stage:
            return str(title)
        summary = self._objective_summary(stage["objective"], stage["have"], stage["need"])
        return f"{title} — {summary}"

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
            stage = self._current_stage(quest_id, quest)
            title = quest.get("title", quest_id)
            if not stage:
                active.append(f"{title} | In progress | 0/1")
                continue
            step = stage["step"]
            objective = stage["objective"]
            done = stage["have"]
            count = stage["need"]
            step_title = str(step.get("title", "")).strip()
            step_label = f"Step {stage['index'] + 1}/{stage['total']}"
            if step_title:
                step_label = f"{step_label}: {step_title}"
            status = "Ready to turn in" if done >= count else "In progress"
            if not self._stage_requirements_met(
                player,
                step,
                world=world,
                current_location=current_location,
                campaign_context=campaign_context,
            ):
                status = "Awaiting requirements"
            summary = self._objective_summary(objective, done, count)
            turn_in_label = self._turn_in_label(step, objective)
            if done >= count and turn_in_label:
                summary = f"{summary} -> {turn_in_label}"
            active.append(f"{title} | {step_label} | {status} | {summary}")

        lines = ["Offered quests:"]
        if offered:
            lines.extend(f"- {self._offer_line(quest_id, quest)}" for quest_id, quest in offered)
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

            stage = self._current_stage(quest_id, quest)
            title = quest.get("title", quest_id)
            if not stage:
                active.append(f"{title} (0/1) - In progress")
                continue
            need = stage["need"]
            have = stage["have"]
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
            stage = self._current_stage(quest_id, quest)
            if not stage:
                summary = "progress 0/1"
                need = 1
                have = 0
            else:
                objective = stage["objective"]
                need = stage["need"]
                have = stage["have"]
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

        if objective_type == "talk_to_npc":
            npc_name = self._fallback_name(str(objective.get("npc", "npc")))
            location_name = self._fallback_name(str(objective.get("location", "unknown location")))
            suffix = ", ready to turn in" if have >= need else ""
            return f"talk to {npc_name} at {location_name} ({have}/{need}{suffix})"

        if objective_type == "inspect":
            target_name = self._fallback_name(str(objective.get("target", "target")))
            location_name = self._fallback_name(str(objective.get("location", "unknown location")))
            suffix = ", ready to turn in" if have >= need else ""
            return f"inspect {target_name} at {location_name} ({have}/{need}{suffix})"

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

            stage = self._current_stage(quest_id, quest)
            if not stage:
                continue
            objective = stage["objective"]
            need = stage["need"]
            have = stage["have"]
            turn_in = self._turn_in_location(stage["step"], objective) or "village_square"
            return {
                "quest_id": quest_id,
                "title": quest.get("title", quest_id),
                "objective": objective,
                "have": have,
                "need": need,
                "ready_to_turn_in": have >= need,
                "turn_in": turn_in,
                "stage_index": stage["index"],
                "stage_total": stage["total"],
                "stage_title": str(stage["step"].get("title", "")).strip(),
            }
        return None

    def _complete_stage(
        self,
        player: Character,
        quest_id: str,
        quest: dict,
        step: dict,
        objective: dict,
        inventory_engine,
    ) -> list[str]:
        messages = []
        steps = self._steps_for(quest)
        entry = self._progress_entry(quest_id)
        stage_index = entry["stage"]
        if stage_index >= len(steps):
            return messages

        objective_type = objective.get("type")
        need = int(objective.get("count", 1))
        if objective_type == "bring_item":
            item_id = objective.get("item", "")
            for _ in range(need):
                if item_id in player.inventory:
                    player.inventory.remove(item_id)

        if stage_index < len(steps) - 1:
            self._set_progress(quest_id, stage_index + 1, 0)
            next_step = steps[stage_index + 1]
            next_title = str(next_step.get("title", "")).strip()
            if next_title:
                messages.append(f"Quest updated: {quest.get('title', quest_id)} - {next_title}.")
            else:
                messages.append(f"Quest updated: {quest.get('title', quest_id)}.")
            return messages

        self.completed.add(quest_id)
        self.recently_completed_quests.append(quest_id)
        reward = quest.get("reward", {})
        gold = int(reward.get("gold", 0))
        player.gold += gold
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
        return messages

    def on_item_obtained(
        self,
        player: Character,
        item_id: str,
        world=None,
        current_location: str | None = None,
        campaign_context: dict | None = None,
    ) -> list[str]:
        messages = []

        for quest_id, quest in self.quests.items():
            if not self._is_active(player, quest_id, quest, world=world, current_location=current_location, campaign_context=campaign_context):
                continue
            stage = self._current_stage(quest_id, quest)
            if not stage:
                continue
            step = stage["step"]
            if not self._stage_requirements_met(player, step, world=world, current_location=current_location, campaign_context=campaign_context):
                continue
            objective = stage["objective"]
            if objective.get("type") != "bring_item":
                continue
            if objective.get("item") != item_id:
                continue

            need = stage["need"]
            previous = stage["have"]
            have_item = player.inventory.count(item_id)
            self._set_progress(quest_id, stage["index"], min(need, have_item))
            current = min(need, have_item)

            if current > previous:
                messages.append(f"Quest progress: {quest.get('title', quest_id)} ({current}/{need})")
                if current >= need:
                    turn_in = self._turn_in_label(step, objective)
                    if turn_in:
                        messages.append(
                            f"Objective complete: {quest.get('title', quest_id)}. "
                            f"Return to {turn_in} to finish the step."
                        )

        return messages

    def on_enemy_defeated(
        self,
        player: Character,
        enemy_id: str,
        location_id: str,
        inventory_engine,
        world=None,
        campaign_context: dict | None = None,
    ) -> list[str]:
        messages = []

        for quest_id, quest in self.quests.items():
            if not self._is_active(player, quest_id, quest, world=world, current_location=location_id, campaign_context=campaign_context):
                continue
            stage = self._current_stage(quest_id, quest)
            if not stage:
                continue
            step = stage["step"]
            if not self._stage_requirements_met(player, step, world=world, current_location=location_id, campaign_context=campaign_context):
                continue
            objective = stage["objective"]
            if objective.get("type") != "defeat_enemy":
                continue
            if objective.get("enemy") != enemy_id or objective.get("location") != location_id:
                continue

            need = stage["need"]
            self._set_progress(quest_id, stage["index"], min(need, stage["have"] + 1))
            have = min(need, stage["have"] + 1)
            messages.append(f"Quest progress: {quest.get('title', quest_id)} ({have}/{need})")
            if have >= need:
                turn_in = self._turn_in_label(step, objective)
                if turn_in:
                    messages.append(
                        f"Objective complete: {quest.get('title', quest_id)}. "
                        f"Return to {turn_in} to finish the step."
                    )
                turn_in_location = self._turn_in_location(step, objective)
                if turn_in_location == location_id and not self._turn_in_npc(step):
                    messages.extend(self._complete_stage(player, quest_id, quest, step, objective, inventory_engine))

        return messages

    def on_location_enter(
        self,
        player: Character,
        location_id: str,
        inventory_engine,
        world=None,
        campaign_context: dict | None = None,
    ) -> list[str]:
        messages = []
        self.recently_completed_quests = []

        for quest_id, quest in self.quests.items():
            if not self._is_active(player, quest_id, quest, world=world, current_location=location_id, campaign_context=campaign_context):
                continue
            stage = self._current_stage(quest_id, quest)
            if not stage:
                continue
            step = stage["step"]
            if not self._stage_requirements_met(player, step, world=world, current_location=location_id, campaign_context=campaign_context):
                continue
            objective = stage["objective"]
            objective_type = objective.get("type")
            need = stage["need"]

            if objective_type == "bring_item":
                item_id = objective.get("item", "")
                if item_id:
                    have_item = min(need, player.inventory.count(item_id))
                    self._set_progress(quest_id, stage["index"], have_item)

            if objective_type == "visit_location" and location_id == objective.get("location"):
                previous = stage["have"]
                self._set_progress(quest_id, stage["index"], need)
                if previous < need:
                    messages.append(f"Quest progress: {quest.get('title', quest_id)} ({need}/{need})")
                    turn_in = self._turn_in_label(step, objective)
                    if turn_in:
                        messages.append(
                            f"Objective complete: {quest.get('title', quest_id)}. "
                            f"Return to {turn_in} to finish the step."
                        )

            have = self._progress_entry(quest_id)["count"]
            if have < need:
                continue

            turn_in_location = self._turn_in_location(step, objective)
            if turn_in_location and location_id != turn_in_location:
                continue
            if self._turn_in_npc(step):
                continue

            messages.extend(self._complete_stage(player, quest_id, quest, step, objective, inventory_engine))

        if self.quests and len(self.completed) == len(self.quests) and not self.demo_complete_shown:
            messages.append(Narrator.demo_complete_text())
            self.demo_complete_shown = True

        return messages

    def on_npc_talk(
        self,
        player: Character,
        npc_id: str,
        location_id: str,
        inventory_engine,
        world=None,
        campaign_context: dict | None = None,
    ) -> list[str]:
        messages = []
        self.recently_completed_quests = []
        npc_id = str(npc_id).strip().lower()

        for quest_id, quest in self.quests.items():
            if not self._is_active(player, quest_id, quest, world=world, current_location=location_id, campaign_context=campaign_context):
                continue
            stage = self._current_stage(quest_id, quest)
            if not stage:
                continue
            step = stage["step"]
            if not self._stage_requirements_met(player, step, world=world, current_location=location_id, campaign_context=campaign_context):
                continue
            objective = stage["objective"]
            objective_type = objective.get("type")
            need = stage["need"]
            turn_in_location = self._turn_in_location(step, objective)
            turn_in_npc = self._turn_in_npc(step)
            stage_completed = False

            if objective_type == "talk_to_npc":
                objective_npc = str(objective.get("npc", "")).strip().lower()
                objective_location = str(objective.get("location", "")).strip().lower()
                if npc_id == objective_npc and (not objective_location or objective_location == location_id):
                    self._set_progress(quest_id, stage["index"], need)
                    messages.append(f"Quest progress: {quest.get('title', quest_id)} ({need}/{need})")
                    if not turn_in_npc or turn_in_npc == npc_id:
                        if not turn_in_location or turn_in_location == location_id:
                            messages.extend(self._complete_stage(player, quest_id, quest, step, objective, inventory_engine))
                            stage_completed = True

            if stage_completed:
                continue

            if turn_in_npc and npc_id == turn_in_npc:
                if turn_in_location and turn_in_location != location_id:
                    continue
                if stage["have"] >= need:
                    messages.extend(self._complete_stage(player, quest_id, quest, step, objective, inventory_engine))

        return messages

    def on_inspect(
        self,
        player: Character,
        target_id: str,
        target_type: str,
        location_id: str,
        inventory_engine,
        world=None,
        campaign_context: dict | None = None,
    ) -> list[str]:
        messages = []
        self.recently_completed_quests = []
        target_id = str(target_id).strip().lower()
        target_type = str(target_type).strip().lower()

        for quest_id, quest in self.quests.items():
            if not self._is_active(player, quest_id, quest, world=world, current_location=location_id, campaign_context=campaign_context):
                continue
            stage = self._current_stage(quest_id, quest)
            if not stage:
                continue
            step = stage["step"]
            if not self._stage_requirements_met(player, step, world=world, current_location=location_id, campaign_context=campaign_context):
                continue
            objective = stage["objective"]
            if objective.get("type") != "inspect":
                continue
            objective_target = str(objective.get("target", "")).strip().lower()
            objective_type = str(objective.get("target_type", "")).strip().lower()
            objective_location = str(objective.get("location", "")).strip().lower()
            if objective_target and objective_target != target_id:
                continue
            if objective_type and objective_type != target_type:
                continue
            if objective_location and objective_location != location_id:
                continue

            need = stage["need"]
            self._set_progress(quest_id, stage["index"], need)
            messages.append(f"Quest progress: {quest.get('title', quest_id)} ({need}/{need})")
            turn_in = self._turn_in_label(step, objective)
            if turn_in:
                messages.append(
                    f"Objective complete: {quest.get('title', quest_id)}. "
                    f"Return to {turn_in} to finish the step."
                )
            turn_in_location = self._turn_in_location(step, objective)
            if (not turn_in_location or turn_in_location == location_id) and not self._turn_in_npc(step):
                messages.extend(self._complete_stage(player, quest_id, quest, step, objective, inventory_engine))

        return messages

    def to_dict(self) -> dict:
        progress_out = {}
        for quest_id in self.quests:
            progress_out[quest_id] = self._progress_entry(quest_id)
        return {
            "progress": progress_out,
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
            value = progress_data.get(quest_id, {"stage": 0, "count": 0})
            if isinstance(value, dict):
                stage = value.get("stage", 0)
                count = value.get("count", 0)
            else:
                stage = 0
                count = value
            try:
                stage = max(0, int(stage))
            except (TypeError, ValueError):
                stage = 0
            try:
                count = max(0, int(count))
            except (TypeError, ValueError):
                count = 0
            loaded_progress[quest_id] = {"stage": stage, "count": count}
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
            entry = self._progress_entry(quest_id)
            steps = self._steps_for(self.quests.get(quest_id, {}))
            if steps and entry["stage"] >= len(steps):
                self.completed.add(quest_id)
                continue
            if (entry["count"] > 0 or entry["stage"] > 0) and quest_id not in self.completed:
                self.accepted.add(quest_id)

        self.demo_complete_shown = bool(data.get("demo_complete_shown", False))
        self.recently_completed_quests = []
