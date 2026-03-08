"""Bootstrap for Valerion CLI: prompts, intro, and main loop."""

from ai.narrator import Narrator
from engine.game import Game
from player.character import Character


def prompt_player_name() -> str:
    print("Enter your hero name (press Enter for Hero):")
    try:
        raw_name = input("> ")
    except (EOFError, KeyboardInterrupt):
        return "Hero"

    name = raw_name.strip()
    return name if name else "Hero"


def prompt_choice(label: str, options: list[dict]) -> str:
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

        normalized = raw_choice.lower().replace("-", "_").replace(" ", "_")
        for option in options:
            if normalized == option["id"]:
                return option["id"]
        print(f"Invalid option. Choose a number from 1 to {len(options)}.")


def prompt_optional_bio() -> str:
    print("Optional short bio (press Enter to skip, max 180 characters):")
    try:
        raw_bio = input("> ")
    except (EOFError, KeyboardInterrupt):
        return ""
    return raw_bio.strip()[:180]


def prompt_character_creation() -> dict:
    name = prompt_player_name()
    gender = prompt_choice("gender", Character.gender_options())
    race = prompt_choice("race", Character.creation_options("race"))
    player_class = prompt_choice("class", Character.creation_options("class"))
    background = prompt_choice("background", Character.creation_options("background"))
    bio = prompt_optional_bio()
    return {
        "name": name,
        "gender": gender,
        "race": race,
        "player_class": player_class,
        "background": background,
        "bio": bio,
    }


def start_menu() -> str:
    print("Valerion")
    print("A Terminal RPG")
    print("Start Menu: new | load | quit")

    while True:
        try:
            choice = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "quit"

        if choice in {"new", "load", "quit"}:
            return choice
        print("Invalid option. Choose: new, load, or quit.")


def main() -> None:
    choice = start_menu()
    if choice == "quit":
        print("Goodbye.")
        return

    character_profile = None
    if choice == "new":
        character_profile = prompt_character_creation()

    game = Game(data_dir="data", player_name=(character_profile or {}).get("name", "Hero"), character_profile=character_profile)
    print(Narrator.intro())
    if choice == "new":
        print(Narrator.character_creation_text(game.character_context()))
        print(Narrator.new_game_intro(game.chapter_context(), game.current_location_name(), game.character_context()))
    if choice == "load":
        print(game.process_command("load"))
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
