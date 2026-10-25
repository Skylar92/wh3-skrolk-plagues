"""The Under-Empire's part in Skrolk's plagues (spec goal 13).

A city with Clan Pestilens' undercity beneath it spreads plague more easily and catches it again
sooner. The campaign script puts UNDER_BUNDLE on every region with our undercity each turn and takes it
off where the undercity is gone. The effects are the ones Nurgle cult buildings use for spread
(region_to_region_own), in their "bad for the owner" colours: the city belongs to someone else.
"""
from tools.rows import find, row, table_with

UNDER_BUNDLE = "skrolkpl_undercity_plague"
UNDER_TEMPLATE = "wh3_main_bundle_endgame_prevent_under_empire_raid"  # a region bundle with the undercity icon
UNDER_EFFECTS = (("wh2_main_effect_plague_infectivity_mod", "region_to_region_own", 20.0),
                 ("wh3_dlc25_effect_plague_immunity_mod_good", "region_to_region_own", -1.0))

TEXTS = {
    "ru": {"title": "Чумные норы",
           "desc": "Под этим городом роются норы Клана Пестиленс: чума отсюда расходится легче, "
                   "а город быстрее подхватывает её снова."},
    "en": {"title": "Plague Burrows",
           "desc": "Clan Pestilens' burrows riddle the ground beneath this city: plague spreads from here "
                   "more easily, and the city catches it again sooner."},
}


def make_under_tables(table):
    bundles, junctions = table("effect_bundles_tables"), table("effect_bundles_to_effects_junctions_tables")
    bundle = row(bundles, find(bundles, "key", UNDER_TEMPLATE), key=UNDER_BUNDLE, owner_only=False)
    return [table_with(bundles, bundle),
            table_with(junctions, *[row(junctions, junctions.rows[0], effect_bundle_key=UNDER_BUNDLE,
                                        effect_key=effect, effect_scope=scope, value=value,
                                        advancement_stage="start_turn_completed")
                                    for effect, scope, value in UNDER_EFFECTS])]


def make_under_loc(lang):
    t = TEXTS[lang]
    return [("effect_bundles_localised_title_" + UNDER_BUNDLE, t["title"]),
            ("effect_bundles_localised_description_" + UNDER_BUNDLE, t["desc"])]
