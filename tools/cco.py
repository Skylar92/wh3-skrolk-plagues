"""Our copy of the plague window's context script (ui/cco/dlc25plagues.cco).

The window's "Effects" columns (Plagues.EffectsForSelection) list the selected symptoms' effects
for a hard-coded pair of faction sets, Nurgle's. Pestilens' plagues split effects by our own sets,
so for Pestilens the columns read those; everyone else keeps Nurgle's sets.
"""
from tools.keys import NEGATIVE_SET, PESTILENS, POSITIVE_SET

CCO_PATH = "ui/cco/dlc25plagues.cco"
_VANILLA_SETS = 'GetIfElse(enemy, "plague_effect_set_nurgle_positive", "plague_effect_set_nurgle_negative")'
_OUR_SETS = ('GetIfElse(PlayersFaction.FactionRecordContext.Key == "%s", '
             'GetIfElse(enemy, "%s", "%s"), %s)' % (PESTILENS, POSITIVE_SET, NEGATIVE_SET, _VANILLA_SETS))


def make_plague_cco(vanilla):
    if vanilla.count(_VANILLA_SETS) != 1:
        raise ValueError("unexpected dlc25plagues.cco: EffectsForSelection faction sets not found")
    return vanilla.replace(_VANILLA_SETS, _OUR_SETS)
