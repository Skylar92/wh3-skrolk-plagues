import pytest

from conftest import vanilla_table
from tools.spike import FEATURE, PESTILENS, SPIKE_SET, make_spike_loc, make_spike_tables

pytestmark = pytest.mark.game


@pytest.fixture(scope="module")
def tables(schema, vanilla_db):
    return {t.name: t for t in make_spike_tables(lambda name: vanilla_table(schema, vanilla_db, name))}


def rows(tables, name):
    t = tables[name]
    return [dict(zip([f for f, _ in t.fields], r)) for r in t.rows]


def test_spike_pack_binds_pestilens(tables):
    assert {"id": FEATURE} in rows(tables, "campaign_groups_tables")
    assert {"group": FEATURE, "id": FEATURE, "priority": 0.0} in rows(tables, "campaign_group_members_tables")
    assert {"faction": PESTILENS, "member": FEATURE, "context": "ACTOR"} in rows(
        tables, "campaign_group_member_criteria_factions_tables")
    assert {"campaign_group": FEATURE, "set": SPIKE_SET} in rows(
        tables, "campaign_group_plague_component_setup_sets_tables")
    assert {"campaign_group": FEATURE, "set": "wh3_main_nurgle_plagues"} in rows(
        tables, "campaign_group_faction_plague_setup_sets_tables")


def test_spike_has_four_plague_rituals(tables):
    rituals = {r["key"]: r for r in rows(tables, "rituals_tables")}
    assert set(rituals) == {"skrolkpl_spike_ritual_" + s for s in
                            ("agent_army", "agent_settlement", "target_army", "target_settlement")}
    assert all(r["category"] == "NURGLE_RITUAL" for r in rituals.values())
    assert all(r["expended_resources"] == "skrolkpl_spike_ritual" for r in rituals.values())
    bound = {r["ritual"] for r in rows(tables, "campaign_group_rituals_tables")
             if r["campaign_group"] == FEATURE and r["initially_unlocked"]}
    assert bound == set(rituals)


def test_spike_symptom_costs_food_and_gold(tables):
    syms = [r for r in rows(tables, "plague_components_tables") if r["type"] == "SYMPTOM"]
    assert {r["key"] for r in syms} == {"skrolkpl_spike_sym_battle_1", "skrolkpl_spike_sym_force_4",
                                        "skrolkpl_spike_sym_settlement_1"}
    assert {r["cost"] for r in syms} == {"skrolkpl_spike_symptom"}
    costs = {r["id"]: r for r in rows(tables, "resource_costs_tables")}
    assert costs["skrolkpl_spike_symptom"]["treasury_cost"] == -1000
    food = [r for r in rows(tables, "resource_cost_pooled_resource_junctions_tables")
            if r["resource_cost"] == "skrolkpl_spike_symptom"]
    assert [(r["amount"], r["pooled_resource_factor"]) for r in food] == [(-5, "skrolkpl_food_plague")]
    junction = rows(tables, "pooled_resource_factor_junctions_tables")
    assert [(r["unique_id"], r["resource"]) for r in junction] == [("skrolkpl_food_plague", "skaven_food")]


def test_spike_set_uses_own_effects_and_nurgle_mutations(tables):
    setups = rows(tables, "plague_component_setups_tables")
    assert all(r["set"] == SPIKE_SET for r in setups)
    by_comp = {r["component"]: r["effects"] for r in setups}
    assert by_comp["skrolkpl_spike_sym_battle_1"] == "skrolkpl_spike_battle_1"
    effect_setups = {r["key"]: r for r in rows(tables, "plague_effect_setups_tables")}
    # same force/region/garrison shape as the vanilla symptom
    assert effect_setups["skrolkpl_spike_battle_1"] == {
        "key": "skrolkpl_spike_battle_1", "force_effects": "skrolkpl_spike_battle_1",
        "region_effects": None, "garrison_effects": "skrolkpl_spike_battle_1"}
    assert effect_setups["skrolkpl_spike_settlement_1"]["region_effects"] == "skrolkpl_spike_settlement_1"
    assert sum(1 for c in by_comp if c.startswith("wh3_dlc25_nur_mutation_")) == 12


def test_spike_effects_split_by_our_faction_sets(tables):
    # Plague effects pick positive/negative by faction set, not by who made the plague:
    # Pestilens must be in our positive set and out of our negative one.
    items = rows(tables, "faction_set_items_tables")
    assert {(r["faction"], r["remove"], r["set"]) for r in items} == {
        (PESTILENS, False, "skrolkpl_positive"),
        (None, False, "skrolkpl_negative"),
        (PESTILENS, True, "skrolkpl_negative"),
    }
    effects = {r["key"]: r for r in rows(tables, "plague_effects_tables")}
    assert effects["skrolkpl_spike_battle_1"]["positive_effect_for_factions"] == "skrolkpl_spike_battle_1_pos"
    fseb = {(r["key"], r["faction_set"], r["effect_bundle"]) for r in rows(tables, "faction_set_effect_bundles_tables")}
    assert ("skrolkpl_spike_battle_1_pos", "skrolkpl_positive", "wh3_dlc25_nur_battle_1_positive") in fseb
    assert ("skrolkpl_spike_battle_1_neg", "skrolkpl_negative", "wh3_dlc25_nur_battle_1_negative") in fseb


def test_spike_faction_set_ids_are_new(tables, schema, vanilla_db):
    ours = {r["id"] for r in rows(tables, "faction_set_items_tables")}
    assert len(ours) == 3
    vt = vanilla_table(schema, vanilla_db, "faction_set_items_tables")
    assert ours.isdisjoint({r[vt.col("id")] for r in vt.rows})


def test_spike_does_not_override_vanilla_keys(tables):
    keyed = {"campaign_groups_tables": "id", "plague_components_tables": "key", "rituals_tables": "key",
             "resource_costs_tables": "id", "plague_component_setup_sets_tables": "key",
             "pooled_resource_factors_tables": "key", "faction_sets_tables": "key",
             "plague_effects_tables": "key"}
    for name, col in keyed.items():
        assert all(r[col].startswith("skrolkpl_") for r in rows(tables, name)), name


def test_spike_loc_copies_vanilla_names(schema, vanilla_db):
    from tools.packfile import read_pack
    from tools.paths import GAME_DATA
    from tools.loc import decode_loc
    vanilla = {}
    for path, data in read_pack(GAME_DATA / "local_en.pack").items():
        if path.endswith(".loc"):
            vanilla.update(decode_loc(data))
    loc = dict(make_spike_loc(vanilla))
    assert loc  # something was copied
    assert loc["plague_components_localised_name_skrolkpl_spike_sym_battle_1"] == \
        vanilla["plague_components_localised_name_wh3_dlc25_nur_battle_1"]
    assert loc["pooled_resource_factors_display_name_negative_skrolkpl_plague"] == "Plague of Skrolk"
    assert all("skrolkpl_" in k for k in loc)
