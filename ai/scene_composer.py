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
        base_line = ""
        if context.visible_enemy_names and context.visible_item_names:
            base_line = "Danger and opportunity are both in plain view."
        elif context.visible_enemy_names and context.visible_npc_names:
            base_line = "Visible danger keeps every conversation on edge."
        elif context.visible_enemy_names:
            base_line = "Threat is the clearest thing in view."
        elif context.visible_item_names and context.visible_npc_names:
            base_line = "The area feels active, with useful supplies close at hand."
        elif context.visible_npc_names:
            base_line = "The area feels inhabited and alert."
        elif context.visible_item_names:
            base_line = "The area is quiet enough for useful details to stand out."
        elif context.exits:
            base_line = "Nothing presses in immediately, but the road still opens onward."
        else:
            base_line = "The place holds in a tense, self-contained pause."
        tone = self._tone_line(context)
        if tone:
            return f"{tone} {base_line}"
        return base_line

    def _arrival_line(self, context: SceneContext) -> str:
        base_line = ""
        if context.visible_enemy_names:
            base_line = "Trouble shows itself as soon as you arrive."
        elif context.visible_item_names:
            base_line = "Something useful stands out right away."
        elif context.visible_npc_names:
            base_line = "You step into a place already claimed by other voices."
        elif context.recent_event_notes:
            base_line = "The place feels shaped by what happened here recently."
        else:
            base_line = "Nothing urgent moves against you yet."
        tone = self._tone_line(context)
        if tone:
            return f"{tone} {base_line}"
        return base_line

    def _transition_line(self, context: SceneContext, event_types: set[str]) -> str:
        base_line = ""
        if "miniboss_defeated" in event_types:
            base_line = "A major pressure has lifted from the area."
        elif "enemy_fled" in event_types:
            base_line = "The danger breaks formation and falls back."
        elif "quest_completed" in event_types:
            base_line = "The moment resolves, and the next step comes into focus."
        elif "enemy_defeated" in event_types and not context.visible_enemy_names:
            base_line = "The immediate threat is gone, leaving the area easier to read."
        elif "important_item_acquired" in event_types:
            base_line = "What you carry now changes the weight of the scene."
        elif context.visible_enemy_names:
            base_line = "The scene changes, but tension still holds."
        else:
            base_line = "The area settles around your latest action."
        tone = self._tone_line(context)
        if tone:
            return f"{tone} {base_line}"
        return base_line

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

    @staticmethod
    def _tone_line(context: SceneContext) -> str:
        tone = str(getattr(context, "chapter_tone", "")).strip().lower()
        if tone == "grounded":
            return "The stakes still feel close to home."
        if tone == "uneasy":
            return "Old unease hangs over the place."
        if tone == "strained":
            return "Wider pressures are crowding in."
        if tone == "ominous":
            return "A larger darkness presses at the edges."
        return ""
