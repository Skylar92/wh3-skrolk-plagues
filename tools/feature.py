"""The rows that give Clan Pestilens Nurgle's plague window.

Found in the spike (plan Task 2, runs 1-6):
- the window and its button show for factions with the NURGLE_PLAGUES UI feature;
- components come from the campaign group's component set; Nurgle's 12 parameter slots
  (duration / spread / immunity, levels 0-3) are reused as they are;
- the window performs Nurgle's own direct rituals; their infection cost is zeroed by a bundle;
- the agent rituals spawn Nurgle's cultist, which crashes Skaven UI, so they are not granted;
- plague effects pick positive/negative by faction set, so we bring our own sets;
- the engine takes the group's faction plague setup set for Pestilens: our own, holding the crafted
  plagues' base and the vanilla Skaven plague (with Nurgle's set the Skaven plague could not start);
  its default, which plague priests spread, is the cauldron pox (tools/cauldron.py adds the pox);
- the engine charges nothing for components; the script charges food and gold instead.
"""
from tools.keys import (CAULDRON_PLAGUE, COMPONENT_SET, FEATURE, FOOD_FACTOR, NEGATIVE_SET, PESTILENS, PLAGUE_SET,
                        POSITIVE_SET, SYMPTOM_COST)
from tools.rows import find, row, table_with

FREE_RITUALS_BUNDLE = "skrolkpl_free_plague_rituals"
FREE_RITUAL_EFFECTS = (("wh3_main_effect_force_direct_infection_cost", "faction_to_force_own"),
                       ("wh3_main_effect_force_direct_infection_cost_hidden", "faction_to_region_own"),
                       ("wh3_dlc25_effect_plague_cultists_infection_cost_reduction_force", "faction_to_force_own"))
DIRECT_RITUALS = ("wh3_main_ritual_nur_plague_target_army", "wh3_main_ritual_nur_plague_target_settlement")
MUTATIONS = tuple("wh3_dlc25_nur_mutation_%s_%d" % (slot, level)
                  for slot in ("duration", "spread", "immunity") for level in range(4))
CRAFTED_BASE = "wh3_dlc25_nur_base_hidden"  # the record every crafted plague infects with
SKAVEN_PLAGUE = "wh2_main_plague_skaven"     # the vanilla cauldron (the AI's)
SET_ITEM_ID_BASE = 2100600000  # faction_set_items ids; vanilla's are spread over the whole I32 range

TEXTS = {
    "ru": {"factor": "Чумы Скролка", "bundle_title": "Чумные ритуалы Скролка",
           "bundle_desc": "Скролк творит чумы за еду и золото, а не за заражения.",
           "positive": "Пестиленс", "negative": "Не-Пестиленс",
           "immunity": "Длительность неуязвимости заражённых отрядов и поселений: %d х."},
    "en": {"factor": "Skrolk's plagues", "bundle_title": "Skrolk's Plague Rites",
           "bundle_desc": "Skrolk brews plagues for food and gold, not infections.",
           "positive": "Pestilens", "negative": "Non-Pestilens",
           "immunity": "Immunity duration for infected forces and settlements: %d turns"},
}
# A vanilla line the plague tooltips share with Nurgle; reworded so it no longer names Nurgle
# (still true for Nurgle's own plagues).
IMMUNITY_LINE = "campaign_localised_strings_string_plague_infection_immunity_duration"


def make_feature_tables(table):
    """Return the feature's db tables; `table(name)` gives a vanilla table."""
    t = table
    out = []
    groups, members = t("campaign_groups_tables"), t("campaign_group_members_tables")
    crit, ui = t("campaign_group_member_criteria_factions_tables"), t("ui_features_to_factions_tables")
    out += [table_with(groups, row(groups, id=FEATURE)),
            table_with(members, row(members, group=FEATURE, id=FEATURE, priority=0.0)),
            table_with(crit, row(crit, faction=PESTILENS, member=FEATURE, context="ACTOR")),
            table_with(ui, row(ui, faction=PESTILENS, ui_feature="NURGLE_PLAGUES"))]

    comp_sets, setup_sets = t("campaign_group_plague_component_setup_sets_tables"), t("plague_component_setup_sets_tables")
    faction_plagues, setups = t("campaign_group_faction_plague_setup_sets_tables"), t("plague_component_setups_tables")
    plague_sets, plague_items = t("faction_plague_setup_sets_tables"), t("faction_plague_setup_set_items_tables")
    out += [table_with(comp_sets, row(comp_sets, campaign_group=FEATURE, set=COMPONENT_SET)),
            table_with(setup_sets, row(setup_sets, key=COMPONENT_SET)),
            table_with(faction_plagues, row(faction_plagues, campaign_group=FEATURE, set=PLAGUE_SET)),
            table_with(plague_sets, row(plague_sets, key=PLAGUE_SET, default=CAULDRON_PLAGUE)),
            table_with(plague_items, *[row(plague_items, set=PLAGUE_SET, item=item) for item in (CRAFTED_BASE, SKAVEN_PLAGUE)]),
            table_with(setups, *[row(setups, find(setups, "component", m), set=COMPONENT_SET) for m in MUTATIONS])]

    sets, items = t("faction_sets_tables"), t("faction_set_items_tables")
    names = t("ui_faction_set_to_localised_names_tables")  # the "%s" in "Plague effects on %s forces"
    out += [table_with(sets, row(sets, key=POSITIVE_SET), row(sets, key=NEGATIVE_SET)),
            table_with(names, row(names, faction_set=POSITIVE_SET), row(names, faction_set=NEGATIVE_SET)),
            table_with(items,
                       row(items, faction=PESTILENS, remove=False, set=POSITIVE_SET, id=SET_ITEM_ID_BASE),
                       row(items, remove=False, set=NEGATIVE_SET, id=SET_ITEM_ID_BASE + 1),
                       row(items, faction=PESTILENS, remove=True, set=NEGATIVE_SET, id=SET_ITEM_ID_BASE + 2))]

    rituals = t("campaign_group_rituals_tables")
    out.append(table_with(rituals, *[row(rituals, campaign_group=FEATURE, ritual=r, unlock_mission=None,
                                         unlock_turn=0, initially_unlocked=True) for r in DIRECT_RITUALS]))

    bundles, junctions = t("effect_bundles_tables"), t("effect_bundles_to_effects_junctions_tables")
    out += [table_with(bundles, row(bundles, find(bundles, "key", "wh3_dlc20_payload_eye_of_the_gods_features_nur"),
                                    key=FREE_RITUALS_BUNDLE)),
            table_with(junctions, *[row(junctions, junctions.rows[0], effect_bundle_key=FREE_RITUALS_BUNDLE,
                                        effect_key=effect, effect_scope=scope, value=-100.0,
                                        advancement_stage="start_turn_completed")
                                    for effect, scope in FREE_RITUAL_EFFECTS])]

    costs, factors, fj = t("resource_costs_tables"), t("pooled_resource_factors_tables"), t("pooled_resource_factor_junctions_tables")
    out += [table_with(costs, row(costs, find(costs, "id", "wh3_dlc25_nur_plague_symptom_addition"),
                                  id=SYMPTOM_COST, treasury_cost=0)),
            table_with(factors, row(factors, key=FOOD_FACTOR, is_hidden=False)),
            table_with(fj, row(fj, find(fj, "unique_id", "skaven_food_menace_below"),
                               unique_id=FOOD_FACTOR, factor=FOOD_FACTOR))]
    return out


def make_feature_loc(lang):
    text = TEXTS[lang]
    return [("pooled_resource_factors_display_name_negative_" + FOOD_FACTOR, text["factor"]),
            ("pooled_resource_factors_display_name_positive_" + FOOD_FACTOR, text["factor"]),
            ("effect_bundles_localised_title_" + FREE_RITUALS_BUNDLE, text["bundle_title"]),
            ("effect_bundles_localised_description_" + FREE_RITUALS_BUNDLE, text["bundle_desc"]),
            ("ui_faction_set_to_localised_names_name_" + POSITIVE_SET, text["positive"]),
            ("ui_faction_set_to_localised_names_name_" + NEGATIVE_SET, text["negative"]),
            (IMMUNITY_LINE, text["immunity"])]
