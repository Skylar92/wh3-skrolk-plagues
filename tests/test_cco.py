import pytest

from tools.cco import CCO_PATH, make_plague_cco
from tools.packfile import read_pack
from tools.paths import GAME_DATA

pytestmark = pytest.mark.game


@pytest.fixture(scope="module")
def vanilla():
    return read_pack(GAME_DATA / "ui.pack")[CCO_PATH].decode("utf-8")


def test_effect_columns_use_our_sets_for_pestilens(vanilla):
    # the window lists effects whose faction set is hard-coded to Nurgle's; Pestilens gets ours
    cco = make_plague_cco(vanilla)
    effects = cco[cco.index("EffectsForSelection"):cco.index("IngredientForSlot")]
    assert 'PlayersFaction.FactionRecordContext.Key == "wh2_main_skv_clan_pestilens"' in effects
    assert '"skrolkpl_positive"' in effects and '"skrolkpl_negative"' in effects
    # Nurgle keeps his own sets
    assert '"plague_effect_set_nurgle_positive"' in effects and '"plague_effect_set_nurgle_negative"' in effects


def test_rest_of_the_file_unchanged(vanilla):
    cco = make_plague_cco(vanilla)
    before, after = vanilla.split("EffectsForSelection")[0], cco.split("EffectsForSelection")[0]
    assert before == after
    assert vanilla[vanilla.index("IngredientForSlot"):] == cco[cco.index("IngredientForSlot"):]


def test_unknown_vanilla_shape_refused(vanilla):
    with pytest.raises(ValueError):
        make_plague_cco(vanilla.replace("plague_effect_set_nurgle_positive", "something_else"))
