from engine.dice import DiceEngine
from player.character import Character


class ContractEngine:
    """Tracks repeatable Stonewatch contracts without reshaping story quests."""

    DEFAULT_UNLOCKED_RANKS = {"E", "D"}
    RANK_ORDER = {"E": 0, "D": 1, "C": 2, "B": 3, "A": 4}

    def __init__(self, contracts_data: dict, items_data: dict):
        self.contracts = contracts_data if isinstance(contracts_data, dict) else {}
        self.items = items_data
        self.dice = DiceEngine()
        self.progress = {contract_id: {"stage": 0, "count": 0} for contract_id in self.contracts}
        self.accepted = set()
        self.claimable = set()
        self.completed_counts = {contract_id: 0 for contract_id in self.contracts}
        self.cooldowns = {}
        self.unlocked_ranks = set(self.DEFAULT_UNLOCKED_RANKS)
        self.recently_completed_contracts = []

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(str(text).strip().lower().split())

    @classmethod
    def _normalize_query(cls, text: str) -> str:
        normalized = cls._normalize(text)
        for prefix in ("the ", "a ", "an "):
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
        for suffix in (" contract", " job", " task", " posting"):
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)].strip()
        return normalized

    @staticmethod
    def _fallback_name(entity_id: str) -> str:
        return str(entity_id).replace("_", " ").title()

    def _item_name(self, item_id: str) -> str:
        return self.items.get(item_id, {}).get("name", self._fallback_name(item_id))

    def _progress_entry(self, contract_id: str) -> dict:
        entry = self.progress.get(contract_id, {"stage": 0, "count": 0})
        if not isinstance(entry, dict):
            return {"stage": 0, "count": 0}
        stage = max(0, int(entry.get("stage", 0) or 0))
        count = max(0, int(entry.get("count", 0) or 0))
        return {"stage": stage, "count": count}

    def _set_progress(self, contract_id: str, stage: int, count: int) -> None:
        self.progress[contract_id] = {"stage": max(0, int(stage)), "count": max(0, int(count))}

    def _steps_for(self, contract: dict) -> list[dict]:
        steps = contract.get("steps", [])
        if isinstance(steps, list) and steps:
            return [step for step in steps if isinstance(step, dict)]
        objective = contract.get("objective", {})
        if not isinstance(objective, dict) or not objective:
            return []
        return [{"objective": objective}]

    def _current_stage(self, contract_id: str, contract: dict) -> dict | None:
        steps = self._steps_for(contract)
        if not steps:
            return None
        entry = self._progress_entry(contract_id)
        stage_index = entry["stage"]
        if stage_index >= len(steps):
            return None
        step = steps[stage_index]
        objective = step.get("objective", {}) if isinstance(step, dict) else {}
        if not isinstance(objective, dict):
            objective = {}
        need = max(1, int(objective.get("count", 1)))
        return {
            "index": stage_index,
            "total": len(steps),
            "step": step,
            "objective": objective,
            "need": need,
            "have": entry["count"],
        }

    @staticmethod
    def _allowed_locations(objective: dict) -> list[str]:
        raw_locations = objective.get("locations")
        if isinstance(raw_locations, list) and raw_locations:
            return [str(location_id).strip().lower() for location_id in raw_locations if str(location_id).strip()]
        location_id = str(objective.get("location", "")).strip().lower()
        return [location_id] if location_id else []

    @staticmethod
    def _reward_text(reward: dict, items_data: dict, contract: dict | None = None) -> str:
        parts = []
        gold = int(reward.get("gold", 0))
        if gold:
            parts.append(f"{gold} gold")

        item_rewards = reward.get("items", [])
        if isinstance(item_rewards, list) and item_rewards:
            names = [items_data.get(item_id, {}).get("name", item_id.replace("_", " ").title()) for item_id in item_rewards]
            parts.append(", ".join(names))

        bonus_items = reward.get("bonus_items", [])
        if isinstance(bonus_items, list) and bonus_items:
            bonus_names = []
            for entry in bonus_items:
                if not isinstance(entry, dict):
                    continue
                item_id = str(entry.get("item", "")).strip().lower()
                if not item_id:
                    continue
                bonus_names.append(items_data.get(item_id, {}).get("name", item_id.replace("_", " ").title()))
            if bonus_names:
                parts.append("bonus chance: " + ", ".join(bonus_names))

        contract = contract or {}
        faction_rewards = contract.get("faction_rewards", {})
        if isinstance(faction_rewards, dict):
            for faction_id, amount in faction_rewards.items():
                value = int(amount)
                sign = "+" if value > 0 else ""
                parts.append(f"{sign}{value} {str(faction_id).replace('_', ' ').title()} rep")

        trust_rewards = contract.get("trust_rewards", {})
        if isinstance(trust_rewards, dict):
            for npc_id, amount in trust_rewards.items():
                value = int(amount)
                sign = "+" if value > 0 else ""
                parts.append(f"{sign}{value} {str(npc_id).replace('_', ' ').title()} trust")
        return ", ".join(parts) if parts else "none"

    def _rank_visible(self, contract: dict) -> bool:
        rank = str(contract.get("rank", "")).strip().upper()
        if rank in self.unlocked_ranks:
            return True
        unlock_rank = str(contract.get("unlocks_rank", "")).strip().upper()
        if unlock_rank and unlock_rank == rank:
            return True
        return False

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
    def _trust_requirement_met(player: Character, requirement: dict) -> bool:
        if not isinstance(requirement, dict):
            return True
        npc_id = str(requirement.get("npc", "")).strip().lower()
        if not npc_id:
            return True
        minimum = int(requirement.get("min", 0))
        return player.npc_trust(npc_id) >= minimum

    def _completed_requirement_met(self, requirement) -> bool:
        if isinstance(requirement, str):
            contract_id = str(requirement).strip().lower()
            return self.completed_counts.get(contract_id, 0) > 0
        if not isinstance(requirement, dict):
            return True
        contract_id = str(requirement.get("contract_id", "")).strip().lower()
        minimum = max(1, int(requirement.get("count", 1)))
        if not contract_id:
            return True
        return int(self.completed_counts.get(contract_id, 0)) >= minimum

    def _requirements_met(self, player: Character, contract: dict) -> bool:
        if not self._rank_visible(contract):
            return False

        reputation_requirements = contract.get("requires_reputation", [])
        if isinstance(reputation_requirements, list) and reputation_requirements:
            if not all(self._reputation_requirement_met(player, requirement) for requirement in reputation_requirements):
                return False

        trust_requirements = contract.get("requires_npc_trust", [])
        if isinstance(trust_requirements, list) and trust_requirements:
            if not all(self._trust_requirement_met(player, requirement) for requirement in trust_requirements):
                return False

        contract_requirements = contract.get("requires_contracts_completed", [])
        if isinstance(contract_requirements, list) and contract_requirements:
            if not all(self._completed_requirement_met(requirement) for requirement in contract_requirements):
                return False

        return True

    def _objective_summary(self, objective: dict, have: int, need: int) -> str:
        summary = str(objective.get("summary", "")).strip()
        if summary:
            return f"{summary} ({have}/{need})"

        objective_type = str(objective.get("type", "")).strip().lower()
        if objective_type == "bring_item":
            item_name = self._item_name(str(objective.get("item", "")))
            return f"Recover {item_name} ({have}/{need})"
        return f"Progress {have}/{need}"

    def _offer_line(self, contract_id: str, contract: dict) -> str:
        stage = self._current_stage(contract_id, contract)
        rank = str(contract.get("rank", "")).strip().upper()
        title = str(contract.get("title", contract_id)).strip()
        poster = str(contract.get("posted_by", "Stonewatch Board")).strip()
        display_location = str(contract.get("display_location", "")).strip()
        location_hint = str(contract.get("location_hint", "")).strip()
        location = display_location or location_hint
        if display_location and location_hint and location_hint != display_location:
            location = f"{display_location} ({location_hint})"
        reward_text = self._reward_text(contract.get("reward", {}), self.items, contract)
        if not stage:
            return f"[{rank}-Rank] {title} | {poster} | {location} | Reward: {reward_text}"
        objective_text = self._objective_summary(stage["objective"], stage["have"], stage["need"])
        return (
            f"[{rank}-Rank] {title} | {poster} | {location} | {objective_text} | Reward: {reward_text}"
        )

    def available_contracts(self, player: Character, board_location: str) -> list[tuple[str, dict]]:
        normalized_board = str(board_location).strip().lower()
        available = []
        for contract_id, contract in self.contracts.items():
            if str(contract.get("board_location", "")).strip().lower() != normalized_board:
                continue
            if not bool(contract.get("repeatable", True)) and int(self.completed_counts.get(contract_id, 0)) > 0:
                continue
            if contract_id in self.accepted or contract_id in self.claimable:
                continue
            if int(self.cooldowns.get(contract_id, 0)) > 0:
                continue
            if not self._requirements_met(player, contract):
                continue
            available.append((contract_id, contract))
        available.sort(
            key=lambda entry: (
                self.RANK_ORDER.get(str(entry[1].get("rank", "")).strip().upper(), 99),
                str(entry[1].get("title", entry[0])),
            )
        )
        return available

    def active_contract_lines(self) -> list[str]:
        lines = ["Active contracts:"]
        active_lines = []
        for contract_id in sorted(self.accepted):
            contract = self.contracts.get(contract_id, {})
            stage = self._current_stage(contract_id, contract)
            if not stage:
                continue
            title = str(contract.get("title", contract_id)).strip()
            location_hint = str(contract.get("location_hint", contract.get("display_location", ""))).strip()
            objective_text = self._objective_summary(stage["objective"], stage["have"], stage["need"])
            active_lines.append(f"- [{contract.get('rank', '?')}-Rank] {title} | {location_hint} | {objective_text}")
        if active_lines:
            lines.extend(active_lines)
        else:
            lines.append("- none")

        lines.append("Ready to claim:")
        claim_lines = []
        for contract_id in sorted(self.claimable):
            contract = self.contracts.get(contract_id, {})
            title = str(contract.get("title", contract_id)).strip()
            claim_lines.append(f"- [{contract.get('rank', '?')}-Rank] {title}")
        if claim_lines:
            lines.extend(claim_lines)
        else:
            lines.append("- none")
        return lines

    def board_lines(self, player: Character, board_location: str) -> list[str]:
        available = self.available_contracts(player, board_location)
        lines = ["Stonewatch Contract Board", "Available jobs:"]
        if available:
            lines.extend(f"- {self._offer_line(contract_id, contract)}" for contract_id, contract in available)
        else:
            lines.append("- none")
        lines.append("Accepted jobs:")
        active_any = False
        for contract_id in sorted(self.accepted):
            contract = self.contracts.get(contract_id, {})
            if str(contract.get("board_location", "")).strip().lower() != str(board_location).strip().lower():
                continue
            active_any = True
            lines.append(f"- {self._offer_line(contract_id, contract)}")
        if not active_any:
            lines.append("- none")
        lines.append("Ready to claim:")
        claim_any = False
        for contract_id in sorted(self.claimable):
            contract = self.contracts.get(contract_id, {})
            if str(contract.get("board_location", "")).strip().lower() != str(board_location).strip().lower():
                continue
            claim_any = True
            rank = str(contract.get("rank", "")).strip().upper()
            title = str(contract.get("title", contract_id)).strip()
            lines.append(f"- [{rank}-Rank] {title}")
        if not claim_any:
            lines.append("- none")
        has_visible_c = any(str(contract.get("rank", "")).strip().upper() == "C" for _, contract in available)
        if not has_visible_c:
            for contract_id in self.accepted.union(self.claimable):
                contract = self.contracts.get(contract_id, {})
                if str(contract.get("board_location", "")).strip().lower() != str(board_location).strip().lower():
                    continue
                if str(contract.get("rank", "")).strip().upper() == "C":
                    has_visible_c = True
                    break
        if "C" not in self.unlocked_ranks and not has_visible_c:
            lines.append("C-rank postings remain locked. Complete the urgent Hunters Guild trial when it appears.")
        return lines

    def _match_contract(self, query: str, candidates: list[tuple[str, dict]]) -> tuple[str, dict] | None:
        if not candidates:
            return None
        normalized = self._normalize_query(query)
        if not normalized:
            return candidates[0] if len(candidates) == 1 else None
        exact = None
        partial = []
        for contract_id, contract in candidates:
            title = self._normalize(str(contract.get("title", contract_id)))
            if normalized == contract_id or normalized == title:
                exact = (contract_id, contract)
                break
            if normalized and (normalized in title or title in normalized):
                partial.append((contract_id, contract))
        if exact is not None:
            return exact
        if len(partial) == 1:
            return partial[0]
        return None

    def _apply_stage_world_spawns(self, player: Character, contract_id: str, world) -> None:
        contract = self.contracts.get(contract_id, {})
        stage = self._current_stage(contract_id, contract)
        if not stage:
            return
        objective = stage["objective"]
        spawn_enemies = objective.get("spawn_enemies", [])
        if isinstance(spawn_enemies, list):
            for entry in spawn_enemies:
                if not isinstance(entry, dict):
                    continue
                enemy_id = str(entry.get("enemy", "")).strip().lower()
                location_id = str(entry.get("location", "")).strip().lower()
                if enemy_id and location_id:
                    world.add_enemy(location_id, enemy_id)

        spawn_items = objective.get("spawn_items", [])
        if isinstance(spawn_items, list):
            for entry in spawn_items:
                if not isinstance(entry, dict):
                    continue
                item_id = str(entry.get("item", "")).strip().lower()
                location_id = str(entry.get("location", "")).strip().lower()
                if not item_id or not location_id:
                    continue
                if player.inventory.count(item_id) >= max(1, int(objective.get("count", 1))):
                    continue
                world.add_item(location_id, item_id)

    def accept_contract(self, player: Character, query: str, board_location: str, world) -> tuple[bool, list[str], str | None]:
        available = self.available_contracts(player, board_location)
        if not available:
            return False, ["No contracts are posted here right now."], None

        if not query.strip():
            if len(available) != 1:
                titles = [contract.get("title", contract_id) for contract_id, contract in available]
                return False, ["Accept which contract? Available: " + ", ".join(titles)], None
            selected = available[0]
        else:
            selected = self._match_contract(query, available)
            if selected is None:
                titles = [contract.get("title", contract_id) for contract_id, contract in available]
                return False, ["That contract is not posted here. Available: " + ", ".join(titles)], None

        contract_id, contract = selected
        self.accepted.add(contract_id)
        self.claimable.discard(contract_id)
        self._set_progress(contract_id, 0, 0)
        self._apply_stage_world_spawns(player, contract_id, world)
        self.refresh_passive_progress(player, world)
        stage = self._current_stage(contract_id, contract)
        lines = [f"Contract accepted: {contract.get('title', contract_id)}."]
        if stage:
            lines.append(f"Objective: {self._objective_summary(stage['objective'], stage['have'], stage['need'])}.")
            location_hint = str(contract.get("location_hint", contract.get("display_location", ""))).strip()
            if location_hint:
                lines.append(f"Route: {location_hint}.")
        return True, lines, contract_id

    def _stage_complete(self, player: Character, contract_id: str, world) -> list[str]:
        contract = self.contracts.get(contract_id, {})
        steps = self._steps_for(contract)
        entry = self._progress_entry(contract_id)
        stage_index = entry["stage"]
        if stage_index >= len(steps):
            return []

        current_step = steps[stage_index]
        current_objective = current_step.get("objective", {}) if isinstance(current_step, dict) else {}
        if isinstance(current_objective, dict) and str(current_objective.get("type", "")).strip().lower() == "bring_item":
            item_id = str(current_objective.get("item", "")).strip().lower()
            for _ in range(max(1, int(current_objective.get("count", 1)))):
                if item_id in player.inventory:
                    player.inventory.remove(item_id)

        if stage_index < len(steps) - 1:
            self._set_progress(contract_id, stage_index + 1, 0)
            self._apply_stage_world_spawns(player, contract_id, world)
            next_stage = self._current_stage(contract_id, contract)
            if next_stage:
                return [
                    f"Contract updated: {contract.get('title', contract_id)}.",
                    f"Next: {self._objective_summary(next_stage['objective'], next_stage['have'], next_stage['need'])}.",
                ]
            return [f"Contract updated: {contract.get('title', contract_id)}."]

        self.claimable.add(contract_id)
        self.accepted.discard(contract_id)
        self.recently_completed_contracts.append(contract_id)
        return [
            f"Contract complete: {contract.get('title', contract_id)}.",
            "Return to the Stonewatch board and use 'claim <contract>' for payment.",
        ]

    def _matches_enemy_objective(self, objective: dict, enemy_id: str, location_id: str) -> bool:
        objective_type = str(objective.get("type", "")).strip().lower()
        if objective_type not in {"defeat_enemy", "defeat_targets"}:
            return False
        allowed_locations = self._allowed_locations(objective)
        if allowed_locations and str(location_id).strip().lower() not in allowed_locations:
            return False
        exact_enemy = str(objective.get("enemy", "")).strip().lower()
        if exact_enemy:
            return exact_enemy == str(enemy_id).strip().lower()
        enemy_ids = {
            str(value).strip().lower()
            for value in objective.get("enemy_ids", [])
            if str(value).strip()
        }
        return str(enemy_id).strip().lower() in enemy_ids

    def on_enemy_defeated(self, player: Character, enemy_id: str, location_id: str, world) -> list[str]:
        messages = []
        for contract_id in sorted(self.accepted):
            contract = self.contracts.get(contract_id, {})
            stage = self._current_stage(contract_id, contract)
            if not stage:
                continue
            objective = stage["objective"]
            if not self._matches_enemy_objective(objective, enemy_id, location_id):
                continue
            need = stage["need"]
            have = min(need, stage["have"] + 1)
            self._set_progress(contract_id, stage["index"], have)
            messages.append(f"Contract progress: {contract.get('title', contract_id)} ({have}/{need})")
            if have >= need:
                messages.extend(self._stage_complete(player, contract_id, world))
        return messages

    def refresh_passive_progress(self, player: Character, world) -> list[str]:
        messages = []
        for contract_id in sorted(self.accepted):
            contract = self.contracts.get(contract_id, {})
            stage = self._current_stage(contract_id, contract)
            if not stage:
                continue
            objective = stage["objective"]
            objective_type = str(objective.get("type", "")).strip().lower()
            if objective_type != "bring_item":
                continue
            item_id = str(objective.get("item", "")).strip().lower()
            need = stage["need"]
            have = min(need, player.inventory.count(item_id))
            if have == stage["have"]:
                self._apply_stage_world_spawns(player, contract_id, world)
                continue
            self._set_progress(contract_id, stage["index"], have)
            messages.append(f"Contract progress: {contract.get('title', contract_id)} ({have}/{need})")
            if have >= need:
                messages.extend(self._stage_complete(player, contract_id, world))
            else:
                self._apply_stage_world_spawns(player, contract_id, world)
        return messages

    def next_objective(self) -> dict | None:
        for contract_id in sorted(self.accepted):
            contract = self.contracts.get(contract_id, {})
            stage = self._current_stage(contract_id, contract)
            if not stage:
                continue
            return {
                "contract_id": contract_id,
                "title": str(contract.get("title", contract_id)).strip(),
                "objective_text": self._objective_summary(stage["objective"], stage["have"], stage["need"]),
                "location_hint": str(contract.get("location_hint", contract.get("display_location", ""))).strip(),
                "board_location": str(contract.get("board_location", "")).strip().lower(),
                "claimable": False,
            }
        for contract_id in sorted(self.claimable):
            contract = self.contracts.get(contract_id, {})
            return {
                "contract_id": contract_id,
                "title": str(contract.get("title", contract_id)).strip(),
                "objective_text": "Ready to claim",
                "location_hint": "Market Square",
                "board_location": str(contract.get("board_location", "")).strip().lower(),
                "claimable": True,
            }
        return None

    def claim_contract(self, player: Character, query: str, inventory_engine) -> tuple[bool, list[str], str | None, list[str]]:
        claimable_contracts = [(contract_id, self.contracts.get(contract_id, {})) for contract_id in sorted(self.claimable)]
        if not claimable_contracts:
            return False, ["No completed contracts are waiting for payment."], None, []

        if not query.strip():
            if len(claimable_contracts) != 1:
                titles = [contract.get("title", contract_id) for contract_id, contract in claimable_contracts]
                return False, ["Claim which contract? Ready: " + ", ".join(titles)], None, []
            selected = claimable_contracts[0]
        else:
            selected = self._match_contract(query, claimable_contracts)
            if selected is None:
                titles = [contract.get("title", contract_id) for contract_id, contract in claimable_contracts]
                return False, ["That contract is not ready to claim. Ready: " + ", ".join(titles)], None, []

        contract_id, contract = selected
        reward = contract.get("reward", {})
        reward_items_awarded = []
        gold = int(reward.get("gold", 0))
        if gold:
            player.gold += gold

        for item_id in reward.get("items", []):
            inventory_engine.add_item(player, item_id)
            reward_items_awarded.append(str(item_id))

        for entry in reward.get("bonus_items", []):
            if not isinstance(entry, dict):
                continue
            chance = max(0, min(100, int(entry.get("chance", 0))))
            item_id = str(entry.get("item", "")).strip().lower()
            if not item_id:
                continue
            if self.dice.roll_percent() <= chance:
                inventory_engine.add_item(player, item_id)
                reward_items_awarded.append(item_id)

        self.claimable.discard(contract_id)
        self.completed_counts[contract_id] = int(self.completed_counts.get(contract_id, 0)) + 1
        unlock_rank = str(contract.get("unlocks_rank", "")).strip().upper()
        if unlock_rank:
            self.unlocked_ranks.add(unlock_rank)
        if bool(contract.get("repeatable", True)):
            self.cooldowns[contract_id] = max(0, int(contract.get("cooldown", 1)))
        self._set_progress(contract_id, 0, 0)

        reward_text = self._reward_text(reward, self.items, contract)
        lines = [f"Contract claimed: {contract.get('title', contract_id)}.", f"Reward received: {reward_text}."]
        if reward_items_awarded:
            names = [self._item_name(item_id) for item_id in reward_items_awarded]
            lines.append("Bonus items: " + ", ".join(names) + ".")
        if unlock_rank:
            lines.append(f"{unlock_rank}-rank board access unlocked.")
        return True, lines, contract_id, reward_items_awarded

    def advance_board_refresh(self) -> None:
        updated = {}
        for contract_id, value in self.cooldowns.items():
            cooldown = max(0, int(value) - 1)
            if cooldown > 0:
                updated[contract_id] = cooldown
        self.cooldowns = updated

    def sync_active_targets(self, player: Character, world) -> None:
        for contract_id in sorted(self.accepted):
            self._apply_stage_world_spawns(player, contract_id, world)
        self.refresh_passive_progress(player, world)

    def to_dict(self) -> dict:
        return {
            "progress": {contract_id: self._progress_entry(contract_id) for contract_id in self.contracts},
            "accepted": sorted(self.accepted),
            "claimable": sorted(self.claimable),
            "completed_counts": {contract_id: int(self.completed_counts.get(contract_id, 0)) for contract_id in self.contracts},
            "cooldowns": {contract_id: int(value) for contract_id, value in self.cooldowns.items() if contract_id in self.contracts},
            "unlocked_ranks": sorted(rank for rank in self.unlocked_ranks if rank),
        }

    def load_from_dict(self, data: dict) -> None:
        if not isinstance(data, dict):
            return

        progress_data = data.get("progress", {})
        if isinstance(progress_data, dict):
            for contract_id in self.contracts:
                value = progress_data.get(contract_id, {"stage": 0, "count": 0})
                if not isinstance(value, dict):
                    continue
                self.progress[contract_id] = {
                    "stage": max(0, int(value.get("stage", 0) or 0)),
                    "count": max(0, int(value.get("count", 0) or 0)),
                }

        accepted_data = data.get("accepted", [])
        if isinstance(accepted_data, list):
            self.accepted = {str(contract_id).strip().lower() for contract_id in accepted_data if str(contract_id).strip().lower() in self.contracts}

        claimable_data = data.get("claimable", [])
        if isinstance(claimable_data, list):
            self.claimable = {str(contract_id).strip().lower() for contract_id in claimable_data if str(contract_id).strip().lower() in self.contracts}

        completed_counts = data.get("completed_counts", {})
        if isinstance(completed_counts, dict):
            for contract_id in self.contracts:
                self.completed_counts[contract_id] = max(0, int(completed_counts.get(contract_id, 0) or 0))

        cooldowns = data.get("cooldowns", {})
        if isinstance(cooldowns, dict):
            self.cooldowns = {
                str(contract_id).strip().lower(): max(0, int(value))
                for contract_id, value in cooldowns.items()
                if str(contract_id).strip().lower() in self.contracts and int(value) > 0
            }

        unlocked_ranks = data.get("unlocked_ranks", [])
        self.unlocked_ranks = set(self.DEFAULT_UNLOCKED_RANKS)
        if isinstance(unlocked_ranks, list):
            for rank in unlocked_ranks:
                normalized = str(rank).strip().upper()
                if normalized:
                    self.unlocked_ranks.add(normalized)
