"""
suspi: jvePilot's driving personality from the ACC distance bars and the Eco level, with its own follow times.

Ported from jvePilot-beta 1508b2a: opendbc/car/chrysler/values.py DRIVE_PERSONALITY, carcontroller.py:145-152,
selfdrive/controls/lib/longitudinal_mpc_lib/long_mpc.py:78-82. Pure logic.
"""
RELAXED, STANDARD, AGGRESSIVE = 0, 1, 2  # log.LongitudinalPersonality enumerants

# [eco level][follow bars 0-3] -> personality
DRIVE_PERSONALITY = [
  [RELAXED, RELAXED, STANDARD, AGGRESSIVE],
  [RELAXED, STANDARD, STANDARD, AGGRESSIVE],
  [RELAXED, STANDARD, AGGRESSIVE, AGGRESSIVE],
]


def personality(eco_level: int, follow_bars: int) -> int:
  eco = min(max(int(eco_level), 0), 2)
  bars = min(max(int(follow_bars), 0), 3)
  return DRIVE_PERSONALITY[eco][bars]


def t_follow(personality_value: int, relaxed: float, standard: float, aggressive: float) -> float:
  return {RELAXED: relaxed, STANDARD: standard, AGGRESSIVE: aggressive}.get(personality_value, standard)
