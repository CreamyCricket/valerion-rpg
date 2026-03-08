from dataclasses import dataclass


@dataclass(frozen=True)
class SceneContext:
    location_id: str
    location_name: str
    location_description: str
    visible_enemy_names: tuple[str, ...]
    visible_item_names: tuple[str, ...]
    visible_npc_names: tuple[str, ...]
    exits: tuple[tuple[str, str], ...]
    recent_event_notes: tuple[str, ...]
    chapter_title: str
    chapter_note: str
    active_quest_title: str = ""
    active_quest_note: str = ""


class DMContextBuilder:
    """Builds narrative-only context snapshots from deterministic engine state."""

    def build(
        self,
        *,
        location_id: str,
        location_name: str,
        location_description: str,
        visible_enemy_names: list[str],
        visible_item_names: list[str],
        visible_npc_names: list[str],
        exits: dict[str, str],
        recent_events: list[dict],
        chapter_progress: dict,
        active_quest_title: str = "",
        active_quest_note: str = "",
    ) -> SceneContext:
        chapter_title = str(chapter_progress.get("title", "Chapter 1: Forest Roads"))
        chapter_note = str(chapter_progress.get("note", "")).strip()
        event_notes = self._recent_event_notes(recent_events, current_location_id=location_id)
        return SceneContext(
            location_id=location_id,
            location_name=location_name,
            location_description=location_description,
            visible_enemy_names=tuple(visible_enemy_names),
            visible_item_names=tuple(visible_item_names),
            visible_npc_names=tuple(visible_npc_names),
            exits=tuple(exits.items()),
            recent_event_notes=tuple(event_notes),
            chapter_title=chapter_title,
            chapter_note=chapter_note,
            active_quest_title=active_quest_title.strip(),
            active_quest_note=active_quest_note.strip(),
        )

    def _recent_event_notes(self, recent_events: list[dict], current_location_id: str) -> list[str]:
        important_notes = []
        fallback_notes = []

        for event in reversed(recent_events):
            note = self._event_note(event, current_location_id)
            if not note:
                continue

            event_type = str(event.get("type", "")).strip().lower()
            if event_type == "location_visited":
                if note not in fallback_notes:
                    fallback_notes.append(note)
                continue

            if note not in important_notes:
                important_notes.append(note)

            if len(important_notes) >= 2:
                break

        if important_notes:
            return important_notes[:2]
        return fallback_notes[:1]

    @staticmethod
    def _event_note(event: dict, current_location_id: str) -> str:
        event_type = str(event.get("type", "")).strip().lower()
        details = event.get("details", {})
        if not isinstance(details, dict):
            details = {}

        if event_type == "enemy_defeated":
            enemy_name = str(details.get("enemy_name", details.get("enemy_id", "an enemy")))
            location_id = str(details.get("location_id", ""))
            if location_id == current_location_id:
                return f"{enemy_name} already fell here."
            location_name = str(details.get("location_name", location_id or "nearby"))
            return f"You recently defeated {enemy_name} at {location_name}."

        if event_type == "quest_completed":
            quest_title = str(details.get("quest_title", details.get("quest_id", "a quest")))
            return f"{quest_title} is complete."

        if event_type == "miniboss_defeated":
            enemy_name = str(details.get("enemy_name", details.get("enemy_id", "a miniboss")))
            return f"The fall of {enemy_name} still defines this stretch of the journey."

        if event_type == "important_item_acquired":
            item_name = str(details.get("item_name", details.get("item_id", "an item")))
            return f"You secured {item_name}."

        if event_type == "encounter_triggered":
            encounter_name = str(details.get("encounter_name", details.get("encounter_id", "an encounter")))
            return f"{encounter_name} recently entered the area."

        if event_type == "enemy_fled":
            enemy_name = str(details.get("enemy_name", details.get("enemy_id", "an enemy")))
            return f"{enemy_name} escaped."

        if event_type == "level_up":
            level = str(details.get("level", ""))
            if level:
                return f"You reached level {level}."
            return "You grew stronger."

        if event_type == "world_event_resolved":
            event_name = str(details.get("event_name", details.get("event_id", "a world event")))
            return f"{event_name} has already changed this area."

        if event_type == "location_visited":
            location_id = str(details.get("location_id", ""))
            if location_id == current_location_id:
                return ""
            location_name = str(details.get("location_name", details.get("location_id", "this place")))
            return f"You recently passed through {location_name}."

        return ""
