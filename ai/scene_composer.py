from ai.dm_context import SceneContext


class SceneComposer:
    """Creates short scene text from state snapshots without changing mechanics."""

    def compose_look_lines(self, context: SceneContext) -> list[str]:
        lines = [f"Scene: {self._scene_line(context)}"]
        memory_line = self._memory_line(context)
        if memory_line:
            lines.append(f"Memory: {memory_line}")
        focus_line = self._focus_line(context)
        if focus_line:
            lines.append(f"Focus: {focus_line}")
        return lines

    def compose_entry_lines(self, context: SceneContext) -> list[str]:
        return [f"Arrival: {self._arrival_line(context)}"]

    def compose_transition_lines(self, context: SceneContext, event_types: set[str]) -> list[str]:
        lines = [f"Scene shift: {self._transition_line(context, event_types)}"]
        memory_line = self._memory_line(context)
        if memory_line:
            lines.append(f"Memory: {memory_line}")
        focus_line = self._focus_line(context)
        if focus_line:
            lines.append(f"Focus: {focus_line}")
        return lines

    def _scene_line(self, context: SceneContext) -> str:
        if context.visible_enemy_names and context.visible_item_names:
            return "Danger and opportunity are both in plain view."
        if context.visible_enemy_names and context.visible_npc_names:
            return "Visible danger keeps every conversation on edge."
        if context.visible_enemy_names:
            return "Threat is the clearest thing in view."
        if context.visible_item_names and context.visible_npc_names:
            return "The area feels active, with useful supplies close at hand."
        if context.visible_npc_names:
            return "The area feels inhabited and alert."
        if context.visible_item_names:
            return "The area is quiet enough for useful details to stand out."
        if context.exits:
            return "Nothing presses in immediately, but the road still opens onward."
        return "The place holds in a tense, self-contained pause."

    def _arrival_line(self, context: SceneContext) -> str:
        if context.visible_enemy_names:
            return "Trouble shows itself as soon as you arrive."
        if context.visible_item_names:
            return "Something useful stands out right away."
        if context.visible_npc_names:
            return "You step into a place already claimed by other voices."
        if context.recent_event_notes:
            return "The place feels shaped by what happened here recently."
        return "Nothing urgent moves against you yet."

    def _transition_line(self, context: SceneContext, event_types: set[str]) -> str:
        if "miniboss_defeated" in event_types:
            return "A major pressure has lifted from the area."
        if "enemy_fled" in event_types:
            return "The danger breaks formation and falls back."
        if "quest_completed" in event_types:
            return "The moment resolves, and the next step comes into focus."
        if "enemy_defeated" in event_types and not context.visible_enemy_names:
            return "The immediate threat is gone, leaving the area easier to read."
        if "important_item_acquired" in event_types:
            return "What you carry now changes the weight of the scene."
        if context.visible_enemy_names:
            return "The scene changes, but tension still holds."
        return "The area settles around your latest action."

    @staticmethod
    def _memory_line(context: SceneContext) -> str:
        if not context.recent_event_notes:
            return ""
        return context.recent_event_notes[0]

    @staticmethod
    def _focus_line(context: SceneContext) -> str:
        if context.active_quest_title:
            if context.active_quest_note:
                return f"{context.active_quest_title}. {context.active_quest_note}"
            return context.active_quest_title
        return context.chapter_note
