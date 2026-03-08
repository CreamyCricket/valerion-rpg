from engine.dice import DiceEngine


class EncounterEngine:
    """Rolls weighted encounters and world events from location tables."""

    def __init__(self):
        self.dice = DiceEngine()

    def roll_from_table(self, entries: list[dict]) -> dict | None:
        valid_entries = [entry for entry in entries if isinstance(entry, dict) and int(entry.get("weight", 0)) > 0]
        if not valid_entries:
            return None

        total_weight = sum(int(entry.get("weight", 0)) for entry in valid_entries)
        if total_weight <= 0:
            return None

        roll = self.dice.roll_percent()
        scaled_roll = ((roll - 1) % total_weight) + 1
        running_total = 0
        for entry in valid_entries:
            running_total += int(entry.get("weight", 0))
            if scaled_roll <= running_total:
                return entry
        return valid_entries[-1]

    def roll_location_encounter(self, location: dict) -> dict | None:
        encounters = location.get("encounters", [])
        if not isinstance(encounters, list):
            return None
        return self.roll_from_table(encounters)

    def roll_world_event(self, location: dict) -> dict | None:
        chance = int(location.get("world_event_chance", 0))
        if chance <= 0:
            return None

        if self.dice.roll_percent() > chance:
            return None

        events = location.get("world_events", [])
        if not isinstance(events, list):
            return None
        return self.roll_from_table(events)
