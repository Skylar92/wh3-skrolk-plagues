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


def test_spike_shows_plague_button(tables):
    # hud_campaign shows the plague button and panel only when CanUseUiFeature("NURGLE_PLAGUES")
    assert rows(tables, "ui_features_to_factions_tables") == [{"faction": PESTILENS, "ui_feature": "NURGLE_PLAGUES"}]


RITUAL_KINDS = ("agent_army", "agent_settlement", "target_army", "target_settlement")


def test_spike_has_four_plague_rituals(tables):
    rituals = {r["key"]: r for r in rows(tables, "rituals_tables")}
    assert set(rituals) == {"skrolkpl_spike_ritual_" + s for s in RITUAL_KINDS}
    assert all(r["category"] == "NURGLE_RITUAL" for r in rituals.values())
    assert all(r["expended_resources"] == "skrolkpl_spike_ritual" for r in rituals.values())


def test_spike_binds_direct_nurgle_rituals_only(tables):
    # run 4: the window uses Nurgle's own ritual keys. Run 5: the cultist they spawn (a Nurgle-only
    # dignitary) crashes Skaven UI, so the agent rituals are not granted (carrier agent is a TODO).
    bound = {r["ritual"] for r in rows(tables, "campaign_group_rituals_tables")
             if r["campaign_group"] == FEATURE and r["initially_unlocked"]}
    assert bound == ({"skrolkpl_spike_ritual_" + s for s in RITUAL_KINDS}
                     | {"wh3_main_ritual_nur_plague_target_army", "wh3_main_ritual_nur_plague_target_settlement"})


def test_spike_fills_blessed_effects(tables):
    # run 5: the panel's effect columns stay empty; probe whether they read the blessed fields
    for r in rows(tables, "plague_effects_tables"):
        assert r["positive_blessed_effect_for_factions"] == r["positive_effect_for_factions"]
        assert r["negative_blessed_effect_for_factions"] == r["negative_effect_for_factions"]


def test_spike_script_dumps_interfaces():
    from tools.paths import ROOT
    lua = (ROOT / "src/script/campaign/mod/skrolkpl_spike.lua").read_text(encoding="utf-8")
    assert "getmetatable" in lua and "GetStateText" in lua


def test_spike_does_not_permit_the_cultist(tables):
    assert "faction_agent_permitted_subtypes_tables" not in tables
    assert "campaign_character_art_sets_tables" not in tables


def test_spike_script_hides_summon_button():
    from tools.paths import ROOT
    lua = (ROOT / "src/script/campaign/mod/skrolkpl_spike.lua").read_text(encoding="utf-8")
    assert '"button_summon_cultist"' in lua and "SetVisible(false)" in lua


def test_spike_free_ritual_bundle_zeroes_infection_cost(tables):
    effects = {(r["effect_key"], r["effect_scope"], r["value"]) for r in rows(tables, "effect_bundles_to_effects_junctions_tables")
               if r["effect_bundle_key"] == "skrolkpl_spike_free_rituals"}
    assert effects == {("wh3_main_effect_force_direct_infection_cost", "faction_to_force_own", -100.0),
                       ("wh3_main_effect_force_direct_infection_cost_hidden", "faction_to_region_own", -100.0),
                       ("wh3_dlc25_effect_plague_cultists_infection_cost_reduction_force", "faction_to_force_own", -100.0)}
    assert [r["key"] for r in rows(tables, "effect_bundles_tables")] == ["skrolkpl_spike_free_rituals"]


NURGLE_GRID = ("battle_2", "settlement_4", "force_2", "battle_7", "battle_6", "battle_1", "settlement_5",
               "force_3", "battle_4", "force_1", "force_6", "settlement_1", "settlement_2", "battle_5",
               "force_5", "settlement_3", "force_4", "battle_3")  # nurgle_plagues.symptoms_list order


def test_spike_clones_all_eighteen_grid_symptoms(tables):
    # the plague window's symptom grid has 18 slots, filled from the script's symptom list
    syms = [r["key"] for r in rows(tables, "plague_components_tables") if r["type"] == "SYMPTOM"]
    assert sorted(syms) == sorted("skrolkpl_spike_sym_" + s for s in NURGLE_GRID)


def test_spike_script_grid_matches_components():
    from tools.paths import ROOT
    lua = (ROOT / "src/script/campaign/mod/skrolkpl_spike.lua").read_text(encoding="utf-8")
    for s in NURGLE_GRID:
        assert '"skrolkpl_spike_sym_%s"' % s in lua


def test_spike_symptom_costs_food_and_gold(tables):
    syms = [r for r in rows(tables, "plague_components_tables") if r["type"] == "SYMPTOM"]
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
