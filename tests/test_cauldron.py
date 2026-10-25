import pytest

from conftest import vanilla_table
from tools.cauldron import CAULDRON_PLAGUE, make_cauldron_loc, make_cauldron_tables
from tools.keys import NEGATIVE_SET, PLAGUE_SET, POSITIVE_SET

pytestmark = pytest.mark.game

F, R = "force_to_force_own", "region_to_region_own"
P = "province_to_province_own_unseen"


@pytest.fixture(scope="module")
def vanilla(schema, vanilla_db):
    return lambda name: vanilla_table(schema, vanilla_db, name)


@pytest.fixture(scope="module")
def tables(vanilla):
    return {t.name: t for t in make_cauldron_tables(vanilla)}


def rows(tables, name):
    t = tables[name]
    return [dict(zip([f for f, _ in t.fields], r)) for r in t.rows]


def test_a_plague_record_the_script_can_spawn(tables):
    # the probe showed crafted plagues share one empty record; the cauldron needs a record of its own
    (plague,) = rows(tables, "plagues_tables")
    assert plague["name"] == CAULDRON_PLAGUE and plague["parameters"] == CAULDRON_PLAGUE
    (setup,) = rows(tables, "plague_setups_tables")
    assert setup == {"key": CAULDRON_PLAGUE, "plague": CAULDRON_PLAGUE, "effect": CAULDRON_PLAGUE}


def test_no_immunity_so_the_city_takes_it_again(tables, vanilla):
    # with the Skaven parameters the city would be immune for 5 turns after the pox ends, and the script
    # could not infect it again: the pox would vanish for 5 turns. Everything else stays Skaven.
    (params,) = rows(tables, "plague_parameters_tables")
    t = vanilla("plague_parameters_tables")
    skaven = dict(zip([f for f, _ in t.fields], next(r for r in t.rows if r[0] == "skaven_parameters")))
    assert params == dict(skaven, key=CAULDRON_PLAGUE, immunity_duration=0)


def test_one_description_fits_armies_and_cities():
    # in game the tooltip showed the army text ("This force is infected") for the plague in general
    for lang in ("ru", "en"):
        texts = {v for k, v in make_cauldron_loc(lang) if "description" in k}
        assert len(texts) == 1


def test_pestilens_plague_set_knows_it(tables):
    # spawn_plague_* finds a plague's effects through the faction's plague setup set (as Glottkin's
    # gardens do): the pox joins our set
    assert rows(tables, "faction_plague_setup_set_items_tables") == [{"set": PLAGUE_SET, "item": CAULDRON_PLAGUE}]
    assert "faction_plague_setup_sets_tables" not in tables


def test_effects_split_by_our_faction_sets(tables):
    (setup,) = rows(tables, "plague_effect_setups_tables")
    assert setup["force_effects"] == setup["garrison_effects"] == CAULDRON_PLAGUE + "_force"
    assert setup["region_effects"] == CAULDRON_PLAGUE + "_settlement"
    by_key = {r["key"]: r for r in rows(tables, "faction_set_effect_bundles_tables")}
    for effect in rows(tables, "plague_effects_tables"):
        assert by_key[effect["positive_effect_for_factions"]]["faction_set"] == POSITIVE_SET
        assert by_key[effect["negative_effect_for_factions"]]["faction_set"] == NEGATIVE_SET


def bundle_effects(tables, side, target):
    by_key = {r["key"]: r for r in rows(tables, "faction_set_effect_bundles_tables")}
    effect = next(r for r in rows(tables, "plague_effects_tables") if r["key"] == CAULDRON_PLAGUE + "_" + target)
    bundle = by_key[effect[side + "_effect_for_factions"]]["effect_bundle"]
    return {r["effect_key"]: (r["effect_scope"], r["value"])
            for r in rows(tables, "effect_bundles_to_effects_junctions_tables") if r["effect_bundle_key"] == bundle}


def test_effects_as_agreed(tables):
    # author 2026-10-25: Skrolk's vanilla plague about x1.5, plus weapon strength for us and melee
    # defence and public order against the enemy
    assert bundle_effects(tables, "positive", "force") == {
        "wh_dlc08_effect_ability_enable_frenzy": (F, 1.0),
        "wh_main_effect_force_stat_leadership": (F, 12.0),
        "wh2_twa03_effect_vigour_loss_reduction_pestilens_units": (F, -50.0),
        "wh_main_effect_force_all_campaign_replenishment_rate_horde": ("force_to_general_own", 10.0),
        "wh_main_effect_force_stat_weapon_strength": (F, 10.0),
    }
    assert bundle_effects(tables, "negative", "force") == {
        "wh2_main_effect_force_all_campaign_enable_disease_attrition": (F, 1.0),
        "wh_main_effect_force_stat_leadership": (F, -14.0),
        "wh_main_effect_force_stat_melee_defence": (F, -6.0),
    }
    assert bundle_effects(tables, "positive", "settlement") == {
        "wh2_main_effect_building_construction_time_mod_all": (R, -50.0),
        "wh3_main_effect_province_growth_plague": (P, 40.0),
        "wh_main_effect_economy_gdp_mod_all": (R, 25.0),
    }
    assert bundle_effects(tables, "negative", "settlement") == {
        "wh3_main_effect_province_growth_plague": (P, -50.0),
        "wh_main_effect_economy_gdp_mod_all": (R, -75.0),
        "wh_main_effect_public_order_events": ("region_to_province_own_unseen", -6.0),
    }


def test_effects_exist(tables, vanilla):
    known = {r[0] for r in vanilla("effects_tables").rows}
    for r in rows(tables, "effect_bundles_to_effects_junctions_tables"):
        assert r["effect_key"] in known, r["effect_key"]


def test_bundles_target_what_they_sit_on(tables):
    target = {r["key"]: r["bundle_target"] for r in rows(tables, "effect_bundles_tables")}
    assert len(target) == 4
    for key, kind in target.items():
        assert kind == ("force" if "_force_" in key else "region"), key


def test_loc_both_languages():
    for lang in ("ru", "en"):
        loc = dict(make_cauldron_loc(lang))
        assert len(loc) == 8 and all(loc.values())
