"""
suspi: jvePilot's driving personality from the ACC distance bars and the Eco level, with its own follow times.

Ported from jvePilot-beta 1508b2a: opendbc/car/chrysler/values.py DRIVE_PERSONALITY, carcontroller.py:145-152,
selfdrive/controls/lib/longitudinal_mpc_lib/long_mpc.py:78-82. Pure logic.
"""
AGGRESSIVE, STANDARD, RELAXED = 0, 1, 2  # log.LongitudinalPersonality enumerants (cereal/log.capnp)

# [eco level][follow bars 0-3] -> personality; jvePilot's raw table [[0,0,1,2],[0,1,1,2],[0,1,2,2]]:
# more bars = longer gap = more relaxed, and higher Eco moves toward relaxed sooner
DRIVE_PERSONALITY = [
  [AGGRESSIVE, AGGRESSIVE, STANDARD, RELAXED],
  [AGGRESSIVE, STANDARD, STANDARD, RELAXED],
  [AGGRESSIVE, STANDARD, RELAXED, RELAXED],
]


def personality(eco_level: int, follow_bars: int) -> int:
  eco = min(max(int(eco_level), 0), 2)
  bars = min(max(int(follow_bars), 0), 3)
  return DRIVE_PERSONALITY[eco][bars]


def t_follow(personality_value: int, relaxed: float, standard: float, aggressive: float) -> float:
  return {RELAXED: relaxed, STANDARD: standard, AGGRESSIVE: aggressive}.get(personality_value, standard)
