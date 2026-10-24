import pytest

from conftest import vanilla_table
from tools.feature import FREE_RITUALS_BUNDLE, MUTATIONS, make_feature_loc, make_feature_tables
from tools.keys import (COMPONENT_SET, FEATURE, FOOD_FACTOR, NEGATIVE_SET, PESTILENS, POSITIVE_SET,
                        SYMPTOM_COST)

pytestmark = pytest.mark.game


@pytest.fixture(scope="module")
def tables(schema, vanilla_db):
    return {t.name: t for t in make_feature_tables(lambda name: vanilla_table(schema, vanilla_db, name))}


def rows(tables, name):
    t = tables[name]
    return [dict(zip([f for f, _ in t.fields], r)) for r in t.rows]


def test_pestilens_joins_the_feature_group(tables):
    assert rows(tables, "campaign_groups_tables") == [{"id": FEATURE}]
    assert {"faction": PESTILENS, "member": FEATURE, "context": "ACTOR"} in rows(
        tables, "campaign_group_member_criteria_factions_tables")


def test_plague_window_is_shown(tables):
    assert rows(tables, "ui_features_to_factions_tables") == [{"faction": PESTILENS, "ui_feature": "NURGLE_PLAGUES"}]


def test_component_set_bound_with_nurgle_parameter_slots(tables):
    assert {"campaign_group": FEATURE, "set": COMPONENT_SET} in rows(
        tables, "campaign_group_plague_component_setup_sets_tables")
    setups = rows(tables, "plague_component_setups_tables")
    assert {r["component"] for r in setups} == set(MUTATIONS) and len(MUTATIONS) == 12
    assert {r["set"] for r in setups} == {COMPONENT_SET}


def test_only_direct_nurgle_rituals(tables):
    # the panel resolves Nurgle's own ritual keys; the agent ones spawn a cultist that crashes Skaven UI
    bound = {r["ritual"] for r in rows(tables, "campaign_group_rituals_tables") if r["campaign_group"] == FEATURE}
    assert bound == {"wh3_main_ritual_nur_plague_target_army", "wh3_main_ritual_nur_plague_target_settlement"}


def test_faction_sets(tables):
    items = {(r["faction"], r["remove"], r["set"]) for r in rows(tables, "faction_set_items_tables")}
    assert items == {(PESTILENS, False, POSITIVE_SET), (None, False, NEGATIVE_SET), (PESTILENS, True, NEGATIVE_SET)}


def test_free_rituals_bundle(tables):
    j = {(r["effect_key"], r["value"]) for r in rows(tables, "effect_bundles_to_effects_junctions_tables")
         if r["effect_bundle_key"] == FREE_RITUALS_BUNDLE}
    assert j == {("wh3_main_effect_force_direct_infection_cost", -100.0),
                 ("wh3_main_effect_force_direct_infection_cost_hidden", -100.0),
                 ("wh3_dlc25_effect_plague_cultists_infection_cost_reduction_force", -100.0)}


def test_food_factor_spends_skaven_food(tables):
    assert rows(tables, "pooled_resource_factors_tables") == [{"key": FOOD_FACTOR, "is_hidden": False}]
    j = rows(tables, "pooled_resource_factor_junctions_tables")
    assert [(r["unique_id"], r["factor"], r["resource"], r["maximum"]) for r in j] == [
        (FOOD_FACTOR, FOOD_FACTOR, "skaven_food", 0)]


def test_symptom_cost_is_free_in_the_engine(tables):
    # the engine never charged component costs (spike run 5); the script charges instead
    costs = rows(tables, "resource_costs_tables")
    assert [(r["id"], r["treasury_cost"]) for r in costs] == [(SYMPTOM_COST, 0)]


def test_feature_loc_both_languages():
    for lang in ("ru", "en"):
        loc = dict(make_feature_loc(lang))
        assert loc["pooled_resource_factors_display_name_negative_" + FOOD_FACTOR]
        assert loc["effect_bundles_localised_title_" + FREE_RITUALS_BUNDLE]
