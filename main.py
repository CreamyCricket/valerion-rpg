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


def prompt_character_creation() -> dict:
    while True:
        profile = {
            "name": prompt_player_name(),
            "gender": prompt_choice("gender", Character.gender_options()),
            "race": prompt_choice("race", Character.creation_options("race")),
            "player_class": prompt_choice("class", Character.creation_options("class")),
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
        if not character_profile:
            print("Character creation cancelled.")
            return

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
