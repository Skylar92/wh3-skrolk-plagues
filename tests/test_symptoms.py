import pytest

from conftest import vanilla_table
from tools.keys import COMPONENT_SET, NEGATIVE_SET, POSITIVE_SET, SYMPTOM_COST
from tools.symptoms import SYMPTOMS, make_symptom_loc, make_symptom_tables, symptom_keys

pytestmark = pytest.mark.game

ALLOWED_SCOPES = {"force_to_force_own", "region_to_region_own", "region_to_province_own_unseen",
                  "province_to_region_own_unseen", "province_to_province_own_unseen"}
NURGLE_BOUND = {"battle_7", "force_5", "settlement_2"}  # Nurgle spell, Nurgle recruits, Nurgle corruption


@pytest.fixture(scope="module")
def tables(schema, vanilla_db):
    return {t.name: t for t in make_symptom_tables(lambda name: vanilla_table(schema, vanilla_db, name))}


@pytest.fixture(scope="module")
def vanilla(schema, vanilla_db):
    return lambda name: vanilla_table(schema, vanilla_db, name)


def rows(tables, name):
    t = tables[name]
    return [dict(zip([f for f, _ in t.fields], r)) for r in t.rows]


def by_sid(sid):
    return next(s for s in SYMPTOMS if s.id == sid)


def test_catalogue_size_and_keys():
    keys = symptom_keys()
    assert len(keys) == 23 and len(set(keys)) == 23
    assert all(k.startswith("skrolkpl_sym_") for k in keys)


def test_no_two_symptoms_look_alike():
    # in game two nodes with one icon (Nurgle's growth and our Ratspawn Brood) read as the same symptom
    icons = [s.icon for s in SYMPTOMS]
    assert len(set(icons)) == len(icons)


def test_nurgle_duplicates_of_skrolk_symptoms_dropped():
    # Nurgle's growth (settlement_1) and income (settlement_5) duplicate Skrolk's own growth and income
    assert not {s.nurgle for s in SYMPTOMS} & {"settlement_1", "settlement_5"}


def test_no_nurgle_bound_symptoms():
    assert not {s.nurgle for s in SYMPTOMS} & NURGLE_BOUND


def test_every_component_is_a_symptom_in_our_set(tables):
    comps = rows(tables, "plague_components_tables")
    assert {r["key"] for r in comps} == set(symptom_keys())
    assert {r["type"] for r in comps} == {"SYMPTOM"}
    assert {r["cost"] for r in comps} == {SYMPTOM_COST}
    assert {r["set"] for r in rows(tables, "plague_component_setups_tables")} == {COMPONENT_SET}


def test_effects_split_by_our_faction_sets(tables):
    fseb = rows(tables, "faction_set_effect_bundles_tables")
    assert {r["faction_set"] for r in fseb if r["key"].endswith("_pos")} == {POSITIVE_SET}
    assert {r["faction_set"] for r in fseb if r["key"].endswith("_neg")} == {NEGATIVE_SET}
    effects = {r["key"]: r for r in rows(tables, "plague_effects_tables")}
    assert set(effects) == set(symptom_keys())


def test_force_and_region_shapes(tables, vanilla):
    # The window's effect columns stayed empty for force-only symptoms; vanilla battle symptoms
    # also carry garrison effects. Nurgle clones copy vanilla's shape; ours: force + garrison.
    setups = {r["key"]: r for r in rows(tables, "plague_effect_setups_tables")}
    v = vanilla("plague_effect_setups_tables")
    vanilla_shape = {r[0]: [x is not None for x in r[1:]] for r in v.rows}
    for s in SYMPTOMS:
        r = setups["skrolkpl_sym_" + s.id]
        shape = [r[c] is not None for c in ("force_effects", "region_effects", "garrison_effects")]
        if s.nurgle:
            assert shape == vanilla_shape["wh3_dlc25_nur_" + s.nurgle], s.id
        elif s.kind == "force":
            assert shape == [True, False, True], s.id
        else:
            assert shape == [False, True, False], s.id


def test_nurgle_symptoms_reuse_vanilla_bundles(tables):
    fseb = {r["key"]: r["effect_bundle"] for r in rows(tables, "faction_set_effect_bundles_tables")}
    assert fseb["skrolkpl_sym_battle_1_pos"] == "wh3_dlc25_nur_battle_1_positive"
    assert fseb["skrolkpl_sym_battle_1_neg"] == "wh3_dlc25_nur_battle_1_negative"


def test_vanilla_skaven_values(tables):
    j = rows(tables, "effect_bundles_to_effects_junctions_tables")

    def eff(bundle):
        return {(r["effect_key"], r["value"]) for r in j if r["effect_bundle_key"] == bundle}

    assert eff("skrolkpl_sym_sk_growth_pos") == {("wh3_main_effect_province_growth_plague", 25.0)}
    assert eff("skrolkpl_sym_sk_growth_neg") == {("wh3_main_effect_province_growth_plague", -30.0)}
    assert eff("skrolkpl_sym_sk_income_pos") == {("wh_main_effect_economy_gdp_mod_all", 15.0)}
    assert eff("skrolkpl_sym_sk_income_neg") == {("wh_main_effect_economy_gdp_mod_all", -50.0)}
    assert ("wh_main_effect_force_stat_leadership", 8.0) in eff("skrolkpl_sym_sk_frenzy_pos")
    assert ("wh_main_effect_force_stat_leadership", -9.0) in eff("skrolkpl_sym_sk_frenzy_neg")


def test_skaven_corruption_replaces_nurgle_corruption(tables):
    j = rows(tables, "effect_bundles_to_effects_junctions_tables")
    corr = [r for r in j if r["effect_bundle_key"].startswith("skrolkpl_sym_horned_rat")]
    assert {r["effect_key"] for r in corr} == {"wh3_main_effect_corruption_skaven_events_bad"}
    assert "nurgle" not in " ".join(r["effect_key"] for r in j)


def test_only_own_scopes_and_vanilla_effects(tables, vanilla):
    known = {r[0] for r in vanilla("effects_tables").rows} | {"skrolkpl_effect_attrition_immunity"}
    for r in rows(tables, "effect_bundles_to_effects_junctions_tables"):
        assert r["effect_scope"] in ALLOWED_SCOPES, r
        assert r["effect_key"] in known, r


def test_new_bundles_target_matches_kind(tables):
    target = {r["key"]: r["bundle_target"] for r in rows(tables, "effect_bundles_tables")}
    assert target["skrolkpl_sym_sk_frenzy_pos"] == "force"
    assert target["skrolkpl_sym_sk_growth_neg"] == "region"


def test_icons_exist_in_game(vanilla_db):
    from tools.packfile import read_pack
    from tools.paths import GAME_DATA
    ui = {p.lower() for p in read_pack(GAME_DATA / "ui.pack")}
    for s in SYMPTOMS:
        assert s.icon.lower() in ui, s.icon


def test_loc_names_in_both_languages():
    for lang in ("ru", "en"):
        loc = dict(make_symptom_loc(lang, vanilla={}))
        for s in SYMPTOMS:
            if s.nurgle is None:
                assert loc["plague_components_localised_name_skrolkpl_sym_" + s.id]
                assert loc["plague_components_description_skrolkpl_sym_" + s.id]


def test_nurgle_clone_names_copied_from_vanilla():
    vanilla = {"plague_components_localised_name_wh3_dlc25_nur_battle_1": "Bleeding",
               "plague_components_description_wh3_dlc25_nur_battle_1": "Heart"}
    loc = dict(make_symptom_loc("en", vanilla))
    assert loc["plague_components_localised_name_skrolkpl_sym_battle_1"] == "Bleeding"


def test_blessed_effects_are_doubled(tables):
    # blessed symptoms work twice as hard (like Nurgle's); the effect columns now come from our .cco
    effects = {r["key"]: r for r in rows(tables, "plague_effects_tables")}
    fseb = {r["key"]: r for r in rows(tables, "faction_set_effect_bundles_tables")}
    j = rows(tables, "effect_bundles_to_effects_junctions_tables")
    for s in SYMPTOMS:
        key = "skrolkpl_sym_" + s.id
        e = effects[key]
        assert e["positive_blessed_effect_for_factions"] == key + "_pos_blessed"
        assert e["negative_blessed_effect_for_factions"] == key + "_neg_blessed"
        assert fseb[key + "_pos_blessed"]["faction_set"] == "skrolkpl_positive"
        assert fseb[key + "_neg_blessed"]["faction_set"] == "skrolkpl_negative"
        if s.nurgle:
            assert fseb[key + "_pos_blessed"]["effect_bundle"] == "wh3_dlc25_nur_%s_positive_blessed" % s.nurgle
    thirteen = {(r["effect_key"], r["value"]) for r in j if r["effect_bundle_key"] == "skrolkpl_sym_thirteen_pos_blessed"}
    assert thirteen == {("wh_main_effect_force_stat_weapon_strength", 26.0)}
    frenzy = {(r["effect_key"], r["value"]) for r in j if r["effect_bundle_key"] == "skrolkpl_sym_sk_frenzy_pos_blessed"}
    assert frenzy == {("wh_dlc08_effect_ability_enable_frenzy", 1.0), ("wh_main_effect_force_stat_leadership", 16.0)}


def test_black_death_spares_ours_from_all_attrition(tables):
    j = rows(tables, "effect_bundles_to_effects_junctions_tables")
    ours = {r["effect_key"] for r in j if r["effect_bundle_key"] == "skrolkpl_sym_black_death_pos"}
    enemy = {r["effect_key"] for r in j if r["effect_bundle_key"] == "skrolkpl_sym_black_death_neg"}
    assert ours == {"skrolkpl_effect_attrition_immunity"}  # one line: "immune to attrition"
    assert enemy == {"wh2_main_effect_force_all_campaign_enable_disease_attrition"}


def test_descriptions_are_body_parts():
    # the window names a plague from the symptoms' names and descriptions ("Sweating Eyes");
    # Nurgle's descriptions are body parts, so ours must be one short word too
    for lang in ("ru", "en"):
        for s in SYMPTOMS:
            if s.nurgle is None:
                part = s.names[lang][1]
                assert " " not in part and len(part) <= 12, (s.id, part)
