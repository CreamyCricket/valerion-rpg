from engine.dice import DiceEngine
from player.character import Character


class CombatEngine:
    """Resolves engine-owned combat, including d20 attack rolls, HP, and loot."""
    PLAYER_DEFENSE = 10
    DEFAULT_ENEMY_DEFENSE = 10

    def __init__(self):
        self.dice = DiceEngine()

    def fight(
        self,
        player: Character,
        enemy_id: str,
        enemies_data: dict,
        items_data: dict,
        starting_enemy_hp: int | None = None,
    ) -> dict:
        enemy_data = enemies_data.get(enemy_id)
        if not enemy_data:
            return {
                "victory": False,
                "enemy_id": enemy_id,
                "enemy_name": enemy_id,
                "log": ["No such enemy."],
                "loot": [],
                "enemy_hp": 0,
            }

        enemy_hp = int(enemy_data.get("hp", 1))
        if starting_enemy_hp is not None:
            enemy_hp = max(0, min(enemy_hp, int(starting_enemy_hp)))
        enemy_max_hp = enemy_hp
        enemy_attack = int(enemy_data.get("attack", 1))
        enemy_defense = int(enemy_data.get("defense", self.DEFAULT_ENEMY_DEFENSE))
        enemy_name = enemy_data.get("name", enemy_id)
        behavior = str(enemy_data.get("behavior", "aggressive")).strip().lower()
        xp_reward = int(enemy_data.get("xp", max(5, enemy_hp * 5)))

        log = []
        turn = 1
        enemy_fled = False
        while player.is_alive() and enemy_hp > 0:
            player_attack = max(1, player.attack_value(items_data))
            player_roll = self.dice.roll_d20(player_attack)
            effective_enemy_defense = enemy_defense + 2 if behavior == "defensive" else enemy_defense
            if player_roll["total"] >= effective_enemy_defense:
                player_damage = player_attack
                enemy_hp -= player_damage
                enemy_hp_after = max(0, enemy_hp)
                log.append(
                    f"Turn {turn}: You roll {player_roll['die']} + {player_roll['modifier']} = {player_roll['total']} "
                    f"against {enemy_name} DEF {effective_enemy_defense} and hit for {player_damage} damage "
                    f"(enemy HP: {enemy_hp_after})."
                )
            else:
                log.append(
                    f"Turn {turn}: You roll {player_roll['die']} + {player_roll['modifier']} = {player_roll['total']} "
                    f"against {enemy_name} DEF {effective_enemy_defense} and miss."
                )

            if enemy_hp <= 0:
                break

            if behavior == "cowardly" and enemy_hp <= max(1, int(enemy_max_hp * 0.3)):
                enemy_fled = True
                log.append(f"Turn {turn}: {enemy_name} breaks and flees.")
                break

            enemy_attack_modifier = enemy_attack
            if behavior == "aggressive":
                enemy_attack_modifier += 2
            elif behavior == "defensive":
                enemy_attack_modifier = max(1, enemy_attack_modifier - 1)
            elif behavior == "hunter":
                if player.hp <= max(1, player.max_hp // 2):
                    enemy_attack_modifier += 2
                else:
                    enemy_attack_modifier += 1

            player_defense = player.defense_value(items_data)
            enemy_roll = self.dice.roll_d20(enemy_attack_modifier)
            if enemy_roll["total"] >= player_defense:
                player.hp = max(0, player.hp - enemy_attack)
                log.append(
                    f"Turn {turn}: {enemy_name} rolls {enemy_roll['die']} + {enemy_roll['modifier']} = {enemy_roll['total']} "
                    f"against your DEF {player_defense} and hits for {enemy_attack} damage "
                    f"(your HP: {player.hp}/{player.max_hp})."
                )
            else:
                log.append(
                    f"Turn {turn}: {enemy_name} rolls {enemy_roll['die']} + {enemy_roll['modifier']} = {enemy_roll['total']} "
                    f"against your DEF {player_defense} and misses."
                )
            turn += 1

        victory = enemy_hp <= 0 and player.is_alive()
        loot = enemy_data.get("loot", []) if victory else []

        return {
            "victory": victory,
            "enemy_fled": enemy_fled,
            "enemy_id": enemy_id,
            "enemy_name": enemy_name,
            "behavior": behavior,
            "log": log,
            "loot": loot,
            "enemy_hp": max(0, enemy_hp),
            "xp_reward": xp_reward if victory else 0,
        }
