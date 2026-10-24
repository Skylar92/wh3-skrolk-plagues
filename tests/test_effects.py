import pytest

from conftest import vanilla_table
from tools.effects import ATTRITION_IMMUNITY, make_effect_loc, make_effect_tables

pytestmark = pytest.mark.game


@pytest.fixture(scope="module")
def vanilla(schema, vanilla_db):
    return lambda name: vanilla_table(schema, vanilla_db, name)


@pytest.fixture(scope="module")
def tables(vanilla):
    return {t.name: t for t in make_effect_tables(vanilla)}


def rows(t):
    return [dict(zip([f for f, _ in t.fields], r)) for r in t.rows]


def records(t, effect):
    return {r["attrition_record"] for r in rows(t) if r["effect"] == effect}


def test_one_effect_covers_both_vanilla_immunities(tables, vanilla):
    ours = records(tables["effect_bonus_value_attrition_record_junctions_tables"], ATTRITION_IMMUNITY)
    v = vanilla("effect_bonus_value_attrition_record_junctions_tables")
    expected = (records(v, "wh3_main_effect_attrition_immunity_all_except_plague")
                | records(v, "wh2_dlc16_effect_attrition_immunity_plague"))
    assert ours == expected and {"disease", "nurgle_plague", "snow", "desert"} <= ours
    assert {r["bonus_value_id"] for r in rows(tables["effect_bonus_value_attrition_record_junctions_tables"])} == {"immunity"}


def test_effect_row_cloned(tables):
    assert [r["effect"] for r in rows(tables["effects_tables"])] == [ATTRITION_IMMUNITY]


def test_effect_text_is_one_short_line():
    assert dict(make_effect_loc("ru"))["effects_description_" + ATTRITION_IMMUNITY] == "Защита от небоевых потерь"
    assert dict(make_effect_loc("en"))["effects_description_" + ATTRITION_IMMUNITY] == "Immune to attrition"
