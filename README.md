# Valerion Terminal RPG

Valerion is a beginner-friendly, deterministic terminal adventure. The engine enforces rules for combat, quests, and inventory, while the AI narration layer simply describes what is happening without altering state.

## Run the game
1. Ensure your system has Python 3 installed.
2. From the repo root run `python3 main.py`.
3. Choose `new` to start fresh or `load` to continue a saved campaign. `save`/`load` persist the entire deterministic world plus the narrative event log.

## Key commands
- `look` / `search <target>` / `map`: describe locations, visible items/enemies/NPCs, and exits.
- `move <direction>`: travel between connected areas.
- `fight [enemy]`: resolve deterministic combat with the selected foe.
- `take <item>` / `inventory` / `use <item>`: manage items and equipment.
- `quests` / `journal` / `recap` / `story`: monitor quest progress, lore, chapter context, and milestone history.
- `inspect <target>` / `ask <npc> about <topic>` / `do <free text>`: trigger AI narration on objects, NPCs, or safe narrative actions.
- `hint` / `history`: keep guidance and the important-event timeline at hand.
- `save` / `load`: persist or restore the engine state and event memory in `savegame.json`.
- `help` / `quit`: inspect the command list or exit cleanly.

## Project structure
- `main.py`: CLI menu, player prompt, and input dispatch.
- `engine/`: world state, combat math, inventory, quest tracking, history/event logging, and save/load flow. This is the deterministic, rule-driven core.
- `ai/`: narrative helpers that only describe what the engine already knows—locations, NPC dialog, hints, the new `do` command, chapter text, and lore inspection.
- `player/`: character persistence (HP, inventory, the event log that drives history-aware narration).
- `data/`: JSON files for locations, quests, items, and enemies that seed the deterministic world.

## Architecture note
- **Engine mechanics** control movement, combat resolution, inventory changes, quest completion, and event logging. They never rely on randomness.
- **AI narration** reads the engine state and event memory to deliver atmospheric prose, hints, and chapter cues. It never mutates game state.

## Save/load reminder
Saving records the player, current location, quest progress, world state, and the event log that fuels story/history text. Loading restores those assets and also backfills any narration-friendly events that might be missing, so the chapter/story output stays aligned with the cleared content.
