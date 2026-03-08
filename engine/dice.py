import random


class DiceEngine:
    """Engine-owned dice roller. The narrator only reports these results."""

    @staticmethod
    def roll_d20(modifier: int = 0) -> dict:
        die = random.randint(1, 20)
        return {
            "die": die,
            "modifier": int(modifier),
            "total": die + int(modifier),
        }

    @staticmethod
    def roll_percent() -> int:
        return random.randint(1, 100)
