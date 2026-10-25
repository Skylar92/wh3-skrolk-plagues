"""Skrolk's cauldron plague: the Great Cauldron's strengthened plague (author 2026-10-25).

For the human Pestilens the Great Plague Cauldron spawns this plague instead of the vanilla Skaven one,
and the campaign script keeps the city above it infected until the city is razed. A crafted plague
cannot be spawned by script (crafted plagues share one empty record, wh3_dlc25_nur_base_hidden), so this
is a plague record of its own: Skrolk's vanilla plague about x1.5, plus weapon strength for us and melee
defence and public order against everyone else. It spreads by the vanilla Skaven parameters, but with no
immunity after it ends: the script must be able to infect the cauldron city again at once. Away from the
cauldron city it ends like any plague.

spawn_plague_* finds a plague's effects through the faction's plague setup set, as Glottkin's gardens
do, so the setup joins Pestilens' set (tools/feature.py).
"""
from tools.keys import CAULDRON_PLAGUE, NEGATIVE_SET, PLAGUE_SET, POSITIVE_SET
from tools.rows import find, row, table_with


F, R = "force_to_force_own", "region_to_region_own"
P, RP = "province_to_province_own_unseen", "region_to_province_own_unseen"
# (target, side) -> (vanilla bundle to copy, effects)
BUNDLES = {
    ("force", "pos"): ("wh2_main_bundle_plague_skaven_skv_force_pestilens", (
        ("wh_dlc08_effect_ability_enable_frenzy", F, 1.0),
        ("wh_main_effect_force_stat_leadership", F, 12.0),
        ("wh2_twa03_effect_vigour_loss_reduction_pestilens_units", F, -50.0),
        ("wh_main_effect_force_all_campaign_replenishment_rate_horde", "force_to_general_own", 10.0),
        ("wh_main_effect_force_stat_weapon_strength", F, 10.0))),
    ("force", "neg"): ("wh2_main_bundle_plague_skaven_all_force", (
        ("wh2_main_effect_force_all_campaign_enable_disease_attrition", F, 1.0),
        ("wh_main_effect_force_stat_leadership", F, -14.0),
        ("wh_main_effect_force_stat_melee_defence", F, -6.0))),
    ("settlement", "pos"): ("wh2_main_bundle_plague_skaven_skv_pestilens", (
        ("wh2_main_effect_building_construction_time_mod_all", R, -50.0),
        ("wh3_main_effect_province_growth_plague", P, 40.0),
        ("wh_main_effect_economy_gdp_mod_all", R, 25.0))),
    ("settlement", "neg"): ("wh2_main_bundle_plague_skaven_all", (
        ("wh3_main_effect_province_growth_plague", P, -50.0),
        ("wh_main_effect_economy_gdp_mod_all", R, -75.0),
        ("wh_main_effect_public_order_events", RP, -6.0))),
}

TEXTS = {
    "ru": {"title": "Великий мор котла",
           "desc": "[[img:icon_plague]][[/img]]Великий мор из котла Скролка. Город над котлом он не покидает, "
                   "пока город не разрушат; на других армиях и поселениях проходит, как обычная чума."},
    "en": {"title": "Great Cauldron Pox",
           "desc": "The [[img:icon_plague]][[/img]]Great Pox from Skrolk's cauldron. It never leaves the city above "
                   "the cauldron until the city is razed; elsewhere it passes like any plague."},
}


def bundle_key(target, side):
    return "%s_%s_%s" % (CAULDRON_PLAGUE, target, side)


def make_cauldron_tables(table):
    t = table
    plagues, setups, items = t("plagues_tables"), t("plague_setups_tables"), t("faction_plague_setup_set_items_tables")
    params = t("plague_parameters_tables")
    effect_setups, effects, sets = t("plague_effect_setups_tables"), t("plague_effects_tables"), t("faction_set_effect_bundles_tables")
    bundles, junctions = t("effect_bundles_tables"), t("effect_bundles_to_effects_junctions_tables")
    out = [table_with(params, row(params, find(params, "key", "skaven_parameters"), key=CAULDRON_PLAGUE,
                                  immunity_duration=0)),
           table_with(plagues, row(plagues, find(plagues, "name", "wh2_main_plague_skaven"), name=CAULDRON_PLAGUE,
                                   parameters=CAULDRON_PLAGUE)),
           table_with(setups, row(setups, key=CAULDRON_PLAGUE, plague=CAULDRON_PLAGUE, effect=CAULDRON_PLAGUE)),
           table_with(items, row(items, set=PLAGUE_SET, item=CAULDRON_PLAGUE)),
           table_with(effect_setups, row(effect_setups, key=CAULDRON_PLAGUE, force_effects=CAULDRON_PLAGUE + "_force",
                                         region_effects=CAULDRON_PLAGUE + "_settlement",
                                         garrison_effects=CAULDRON_PLAGUE + "_force"))]
    effect_template = find(effects, "key", "wh2_main_plague_skaven_force")
    out.append(table_with(effects, *[row(effects, effect_template, key=CAULDRON_PLAGUE + "_" + target,
                                         positive_effect_for_factions=bundle_key(target, "pos"),
                                         negative_effect_for_factions=bundle_key(target, "neg"))
                                     for target in ("force", "settlement")]))
    out.append(table_with(sets, *[row(sets, key=bundle_key(target, side), effect_bundle=bundle_key(target, side),
                                      faction_set=POSITIVE_SET if side == "pos" else NEGATIVE_SET)
                                  for target, side in BUNDLES]))
    out.append(table_with(bundles, *[row(bundles, find(bundles, "key", template), key=bundle_key(target, side))
                                     for (target, side), (template, _) in BUNDLES.items()]))
    out.append(table_with(junctions, *[row(junctions, junctions.rows[0], effect_bundle_key=bundle_key(target, side),
                                           effect_key=effect, effect_scope=scope, value=value,
                                           advancement_stage="start_turn_completed")
                                       for (target, side), (_, es) in BUNDLES.items() for effect, scope, value in es]))
    return out


def make_cauldron_loc(lang):
    t = TEXTS[lang]
    out = []
    for target, side in BUNDLES:
        out += [("effect_bundles_localised_title_" + bundle_key(target, side), t["title"]),
                ("effect_bundles_localised_description_" + bundle_key(target, side), t["desc"])]
    return out
