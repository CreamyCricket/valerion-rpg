"""Bootstrap for Valerion CLI: prompts, intro, and main loop."""

from ai.narrator import Narrator
from engine.game import Game
from player.character import Character


def prompt_text(message: str, default: str = "", max_length: int = 180) -> str:
    print(message)
    try:
        raw_value = input("> ")
    except (EOFError, KeyboardInterrupt):
        return default

    value = " ".join(raw_value.strip().split())
    if not value:
        return default
    return value[:max_length]


def prompt_player_name() -> str:
    return prompt_text("Enter your hero name (press Enter for Hero):", default="Hero", max_length=40)


def _normalize_choice_token(text: str) -> str:
    return " ".join(str(text).strip().lower().replace("-", " ").replace("_", " ").split())


def prompt_choice(label: str, options: list[dict], locked_options: list[dict] | None = None) -> str:
    print(f"Choose your {label} (press Enter for 1):")
    for index, option in enumerate(options, start=1):
        lore = option.get("lore", "")
        summary = option.get("summary", "")
        line = f"{index}. {option['name']}"
        if summary:
            line += f" | {summary}"
        print(line)
        if lore:
            print(f"   {lore}")
    locked_options = locked_options or []
    if locked_options:
        print("Locked preview:")
        for option in locked_options:
            name = option.get("name", option.get("id", "Unknown"))
            lore_hook = str(option.get("lore_hook", "")).strip()
            unlock_hint = str(option.get("unlock_hint", "")).strip()
            line = f"- {name} (locked)"
            if lore_hook:
                line += f" | {lore_hook}"
            if unlock_hint:
                line += f" | Hint: {unlock_hint}"
            print(line)

    while True:
        try:
            raw_choice = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            return options[0]["id"]

        if not raw_choice:
            return options[0]["id"]
        if raw_choice.isdigit():
            choice_index = int(raw_choice) - 1
            if 0 <= choice_index < len(options):
                return options[choice_index]["id"]

        normalized = _normalize_choice_token(raw_choice)
        for option in options:
            option_id = _normalize_choice_token(option.get("id", ""))
            option_name = _normalize_choice_token(option.get("name", ""))
            aliases = {_normalize_choice_token(alias) for alias in option.get("aliases", []) if str(alias).strip()}
            if normalized in {option_id, option_name} or normalized in aliases:
                return option["id"]
        print(f"Invalid option. Choose a number from 1 to {len(options)} or type a listed name/alias.")


def prompt_optional_bio() -> str:
    return prompt_text("Optional short bio (press Enter to skip, max 180 characters):", default="", max_length=180)


def print_creation_preview(profile: dict) -> None:
    preview_game = Game(
        data_dir="data",
        player_name=str(profile.get("name", "Hero")),
        character_profile=profile,
    )
    preview = preview_game.character_context()
    print("\nCurrent build:")
    print(Narrator.character_creation_text(preview))


def prompt_creation_review() -> str:
    print("\nConfirm this character? confirm | restart | cancel")
    while True:
        try:
            choice = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "cancel"

        if choice in {"", "confirm"}:
            return "confirm"
        if choice in {"restart", "cancel"}:
            return choice
        print("Invalid option. Choose: confirm, restart, or cancel.")


def prompt_character_creation(menu_game: Game) -> dict:
    while True:
        race_options = menu_game.available_creation_options("race")
        class_options = menu_game.available_creation_options("class")
        locked_races = menu_game.locked_creation_preview_options("race")
        locked_classes = menu_game.locked_creation_preview_options("class")

        profile = {
            "name": prompt_player_name(),
            "gender": prompt_choice("gender", Character.gender_options()),
            "race": prompt_choice("race", race_options, locked_options=locked_races),
            "player_class": prompt_choice("class", class_options, locked_options=locked_classes),
            "background": prompt_choice("background", Character.creation_options("background")),
            "bio": prompt_optional_bio(),
        }

        print_creation_preview(profile)
        review_choice = prompt_creation_review()
        if review_choice == "confirm":
            return profile
        if review_choice == "cancel":
            return {}


def start_menu() -> str:
    print("Valerion")
    print("A Terminal RPG")
    print("Start Menu: new | load | slots | delete | quit")

    while True:
        try:
            choice = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "quit"

        if choice in {"new", "load", "slots", "delete", "quit"}:
            return choice
        print("Invalid option. Choose: new, load, slots, delete, or quit.")


def prompt_slot(game: Game, action: str, default_slot: str) -> str:
    summaries = game.slot_summaries()
    if not summaries:
        prompt = f"Choose a slot to {action} (press Enter for {default_slot}):"
        return prompt_text(prompt, default=default_slot, max_length=20)

    print(f"Choose a slot to {action} (press Enter for {default_slot}):")
    for index, summary in enumerate(summaries, start=1):
        slot_id = str(summary.get("slot_id", index))
        character_name = str(summary.get("character_name", "Unknown")).strip() or "Unknown"
        race = str(summary.get("race", "Unknown")).strip() or "Unknown"
        player_class = str(summary.get("player_class", "Unknown")).strip() or "Unknown"
        level = int(summary.get("level", 1) or 1)
        location = str(summary.get("current_location_name", "Unknown")).strip() or "Unknown"
        print(f"{index}. Slot {slot_id}: {character_name} ({race} {player_class}, Lv {level}) @ {location}")

    while True:
        try:
            raw_choice = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            return default_slot

        if not raw_choice:
            return default_slot
        if raw_choice.isdigit():
            choice_index = int(raw_choice) - 1
            if 0 <= choice_index < len(summaries):
                return str(summaries[choice_index].get("slot_id", default_slot))

        normalized = _normalize_choice_token(raw_choice)
        for summary in summaries:
            slot_id = _normalize_choice_token(summary.get("slot_id", ""))
            character_name = _normalize_choice_token(summary.get("character_name", ""))
            if normalized in {slot_id, character_name, f"slot {slot_id}".strip()}:
                return str(summary.get("slot_id", default_slot))
        print(f"Invalid slot selection. Choose 1-{len(summaries)} or type a slot id/name.")


def main() -> None:
    while True:
        choice = start_menu()
        if choice == "quit":
            print("Goodbye.")
            return
        if choice == "slots":
            menu_game = Game(data_dir="data")
            print(menu_game.process_command("slots"))
            continue
        if choice == "delete":
            menu_game = Game(data_dir="data")
            slot_id = prompt_slot(menu_game, "delete", default_slot="1")
            print(menu_game.process_command(f"delete {slot_id}"))
            continue
        break

    character_profile = None
    menu_game = Game(data_dir="data")
    if choice == "new":
        character_profile = prompt_character_creation(menu_game)
        if not character_profile:
            print("Character creation cancelled.")
            return

    default_slot = menu_game.default_slot_choice() if choice == "new" else "1"
    if choice == "load":
        summaries = menu_game.slot_summaries()
        if summaries:
            default_slot = summaries[0]["slot_id"]
    slot_id = prompt_slot(menu_game, "use", default_slot=default_slot)

    game = Game(
        data_dir="data",
        player_name=(character_profile or {}).get("name", "Hero"),
        character_profile=character_profile,
    )
    print(Narrator.intro())
    if choice == "new":
        print(game.process_command(f"save {slot_id}"))
        print(Narrator.character_creation_text(game.character_context()))
        print(Narrator.new_game_intro(game.chapter_context(), game.current_location_name(), game.character_context()))
    if choice == "load":
        load_output = game.process_command(f"load {slot_id}")
        print(load_output)
        if not load_output.startswith("Game loaded"):
            return
    print(game.process_command("look"))

    while game.running:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue

        output = game.process_command(user_input)
        if output:
            print(output)


if __name__ == "__main__":
    main()
