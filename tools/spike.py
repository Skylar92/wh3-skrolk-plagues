"""Spike pack: give Clan Pestilens the vanilla Nurgle plague window, paid in food and gold.

Throwaway probe for the in-game gate (plan Task 2). Every row is new and keyed skrolkpl_*;
vanilla Nurgle rows are referenced, never overridden.
"""
from tools.dbtable import Table

PESTILENS = "wh2_main_skv_clan_pestilens"
FEATURE = "skrolkpl_feature"
SPIKE_SET = "skrolkpl_spike"
NURGLE_SET = "nurgle_new"
NURGLE_PLAGUES = "wh3_main_nurgle_plagues"
SYMPTOM_COST = "skrolkpl_spike_symptom"
RITUAL_COST = "skrolkpl_spike_ritual"
FOOD_FACTOR = "skrolkpl_plague"
FOOD_JUNCTION = "skrolkpl_food_plague"
# wh3_dlc25_nur_<id>, in vanilla nurgle_plagues.symptoms_list order: the window's 18-slot symptom grid
SPIKE_SYMPTOMS = ("battle_2", "settlement_4", "force_2", "battle_7", "battle_6", "battle_1", "settlement_5",
                  "force_3", "battle_4", "force_1", "force_6", "settlement_1", "settlement_2", "battle_5",
                  "force_5", "settlement_3", "force_4", "battle_3")
RITUALS = ("agent_army", "agent_settlement", "target_army", "target_settlement")
NUR_RITUAL = "wh3_main_ritual_nur_plague_"
SPIKE_RITUAL = "skrolkpl_spike_ritual_"
FACTOR_NAME = "Plague of Skrolk"
POSITIVE_SET = "skrolkpl_positive"
NEGATIVE_SET = "skrolkpl_negative"
FREE_RITUALS_BUNDLE = "skrolkpl_spike_free_rituals"
FREE_RITUAL_EFFECTS = (("wh3_main_effect_force_direct_infection_cost", "faction_to_force_own"),
                       ("wh3_main_effect_force_direct_infection_cost_hidden", "faction_to_region_own"),
                       ("wh3_dlc25_effect_plague_cultists_infection_cost_reduction_force", "faction_to_force_own"))
SET_ITEM_ID_BASE = 2100600000  # faction_set_items ids; vanilla's are spread over the whole I32 range


def _empty_like(table):
    return Table(table.name, table.version, table.guid, list(table.fields), [], table.versioned)


def _row(table, **values):
    """A row for `table` with the given columns set and every other column copied from `template`."""
    template = values.pop("template", None)
    row = list(template) if template else [None] * len(table.fields)
    for col, value in values.items():
        row[table.col(col)] = value
    return row


def _with(table, *rows):
    out = _empty_like(table)
    out.rows.extend(rows)
    return out


def _find(table, col, value):
    i = table.col(col)
    return [r for r in table.rows if r[i] == value]


def symptom_key(sid):
    return "skrolkpl_spike_sym_" + sid


def make_spike_tables(table):
    """Return the spike's new db tables; `table(name)` gives a vanilla table."""
    out = []
    groups = table("campaign_groups_tables")
    out.append(_with(groups, _row(groups, id=FEATURE)))
    members = table("campaign_group_members_tables")
    out.append(_with(members, _row(members, group=FEATURE, id=FEATURE, priority=0.0)))
    crit = table("campaign_group_member_criteria_factions_tables")
    out.append(_with(crit, _row(crit, faction=PESTILENS, member=FEATURE, context="ACTOR")))

    ui = table("ui_features_to_factions_tables")  # hud_campaign gates the plague button on this feature
    out.append(_with(ui, _row(ui, faction=PESTILENS, ui_feature="NURGLE_PLAGUES")))

    comp_sets = table("campaign_group_plague_component_setup_sets_tables")
    out.append(_with(comp_sets, _row(comp_sets, campaign_group=FEATURE, set=SPIKE_SET)))
    setup_sets = table("plague_component_setup_sets_tables")
    out.append(_with(setup_sets, _row(setup_sets, key=SPIKE_SET)))
    faction_sets = table("campaign_group_faction_plague_setup_sets_tables")
    out.append(_with(faction_sets, _row(faction_sets, campaign_group=FEATURE, set=NURGLE_PLAGUES)))

    # Plague effects choose positive/negative by the infected faction's set membership, not by the
    # plague's creator, so Nurgle's own sets would hand Skrolk the negatives. We bring our own sets.
    sets = table("faction_sets_tables")
    out.append(_with(sets, _row(sets, key=POSITIVE_SET), _row(sets, key=NEGATIVE_SET)))
    items = table("faction_set_items_tables")
    out.append(_with(items,
                     _row(items, faction=PESTILENS, remove=False, set=POSITIVE_SET, id=SET_ITEM_ID_BASE),
                     _row(items, remove=False, set=NEGATIVE_SET, id=SET_ITEM_ID_BASE + 1),
                     _row(items, faction=PESTILENS, remove=True, set=NEGATIVE_SET, id=SET_ITEM_ID_BASE + 2)))

    comps = table("plague_components_tables")
    setups = table("plague_component_setups_tables")
    # component setup -> plague_effect_setups (force/region/garrison) -> plague_effects -> faction set bundles
    effect_setups = table("plague_effect_setups_tables")
    effects = table("plague_effects_tables")
    fseb = table("faction_set_effect_bundles_tables")
    new_comps, new_setups = _empty_like(comps), _empty_like(setups)
    new_effect_setups, new_effects, new_fseb = _empty_like(effect_setups), _empty_like(effects), _empty_like(fseb)
    for sid in SPIKE_SYMPTOMS:
        source = "wh3_dlc25_nur_" + sid
        ours = "skrolkpl_spike_" + sid
        new_comps.rows.append(_row(comps, template=_find(comps, "key", source)[0],
                                   key=symptom_key(sid), cost=SYMPTOM_COST))
        new_setups.rows.append(_row(setups, component=symptom_key(sid), set=SPIKE_SET, effects=ours))
        vanilla_setup = _find(effect_setups, "key", source)[0]
        new_effect_setups.rows.append([ours if v == source else v for v in vanilla_setup])
        new_effects.rows.append(_row(effects, key=ours, positive_effect_for_factions=ours + "_pos",
                                     negative_effect_for_factions=ours + "_neg"))
        new_fseb.rows.append(_row(fseb, effect_bundle=source + "_positive", faction_set=POSITIVE_SET,
                                  key=ours + "_pos"))
        new_fseb.rows.append(_row(fseb, effect_bundle=source + "_negative", faction_set=NEGATIVE_SET,
                                  key=ours + "_neg"))
    out += [new_effect_setups, new_effects, new_fseb]
    for r in _find(setups, "set", NURGLE_SET):
        if r[setups.col("component")].startswith("wh3_dlc25_nur_mutation_"):
            new_setups.rows.append(_row(setups, template=r, set=SPIKE_SET))
    out += [new_comps, new_setups]

    costs = table("resource_costs_tables")
    nur_cost = _find(costs, "id", "wh3_dlc25_nur_plague_symptom_addition")[0]
    out.append(_with(costs, _row(costs, template=nur_cost, id=SYMPTOM_COST, treasury_cost=-1000),
                     _row(costs, template=nur_cost, id=RITUAL_COST, treasury_cost=0)))
    factors = table("pooled_resource_factors_tables")
    out.append(_with(factors, _row(factors, key=FOOD_FACTOR, is_hidden=False)))
    fj = table("pooled_resource_factor_junctions_tables")
    menace = _find(fj, "unique_id", "skaven_food_menace_below")[0]
    out.append(_with(fj, _row(fj, template=menace, unique_id=FOOD_JUNCTION, factor=FOOD_FACTOR)))
    pj = table("resource_cost_pooled_resource_junctions_tables")
    out.append(_with(pj, _row(pj, template=pj.rows[0], amount=-5, pooled_resource_factor=FOOD_JUNCTION,
                              resource_cost=SYMPTOM_COST, context="absolute",
                              ui_resource_transaction_pooled_resource="default")))

    rituals = table("rituals_tables")
    group_rituals = table("campaign_group_rituals_tables")
    new_rituals, new_group = _empty_like(rituals), _empty_like(group_rituals)
    for name in RITUALS:
        new_rituals.rows.append(_row(rituals, template=_find(rituals, "key", NUR_RITUAL + name)[0],
                                     key=SPIKE_RITUAL + name, expended_resources=RITUAL_COST))
        new_group.rows.append(_row(group_rituals, campaign_group=FEATURE, ritual=SPIKE_RITUAL + name,
                                   unlock_mission=None, unlock_turn=0, initially_unlocked=True))
    # Run 3: the Infect button found no ritual of ours, so also grant Nurgle's own keys and zero
    # their infection cost with the same effects Nurgle's skills use (the script applies the bundle).
    for name in RITUALS:
        new_group.rows.append(_row(group_rituals, campaign_group=FEATURE, ritual=NUR_RITUAL + name,
                                   unlock_mission=None, unlock_turn=0, initially_unlocked=True))
    out += [new_rituals, new_group]

    bundles = table("effect_bundles_tables")
    source = _find(bundles, "key", "wh3_dlc20_payload_eye_of_the_gods_features_nur")[0]
    out.append(_with(bundles, _row(bundles, template=source, key=FREE_RITUALS_BUNDLE)))
    junctions = table("effect_bundles_to_effects_junctions_tables")
    out.append(_with(junctions, *[
        _row(junctions, template=junctions.rows[0], effect_bundle_key=FREE_RITUALS_BUNDLE, effect_key=effect,
             effect_scope=scope, value=-100.0, advancement_stage="start_turn_completed")
        for effect, scope in FREE_RITUAL_EFFECTS]))
    return out


def make_spike_loc(vanilla):
    """Loc entries for the spike: vanilla names copied onto our clones, plus the food factor's name."""
    renames = {"wh3_dlc25_nur_" + sid: symptom_key(sid) for sid in SPIKE_SYMPTOMS}
    renames.update({NUR_RITUAL + name: SPIKE_RITUAL + name for name in RITUALS})
    entries = []
    for key, text in vanilla.items():
        for src, dst in renames.items():
            if key.endswith("_" + src):
                entries.append((key[:-len(src)] + dst, text))
    entries += [("pooled_resource_factors_display_name_negative_" + FOOD_FACTOR, FACTOR_NAME),
                ("pooled_resource_factors_display_name_positive_" + FOOD_FACTOR, FACTOR_NAME)]
    return entries
