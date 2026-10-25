"""Texts the campaign script and the plague window show, kept in the loc file.

The main pack's loc is English; a translation pack replaces the whole loc file, so these go with it. The
script reads campaign_localised_strings_string_<name> (falling back to English when the key is missing);
the window's counter reads the same key through Loc("<name>").
"""
LOC_PREFIX = "campaign_localised_strings_string_"
FOOD_ICON = "[[img:icon_skaven_food]][[/img]]"
GOLD_ICON = "[[img:icon_treasury]][[/img]]"

UI_TEXTS = {
    # headers over the window's effect columns
    "skrolkpl_ours": {"en": "Clan Pestilens", "ru": "Клан Пестиленс"},
    "skrolkpl_others": {"en": "Other factions", "ru": "Прочие фракции"},
    # under the slot levels
    "skrolkpl_level_note": {"en": "Each slot level: +2 " + FOOD_ICON, "ru": "Каждый уровень слота: +2 " + FOOD_ICON},
    # the price when it cannot be paid
    "skrolkpl_food": {"en": "Needs %d " + FOOD_ICON, "ru": "Нужно %d " + FOOD_ICON},
    "skrolkpl_gold": {"en": "Needs %d " + GOLD_ICON, "ru": "Нужно %d " + GOLD_ICON},
    # after each strain rot line in the plague tooltip
    "skrolkpl_rot_mark": {"en": " (rot)", "ru": " (порча)"},
    # the window's counter: Skrolk's symptom layout changes every turn
    "skrolkpl_layout": {"en": "New [[img:icon_plague]][[/img]]Symptom locations and Blessed Symptom in: [[b]]%d[[/b]] turn",
                        "ru": "Новое расположение [[img:icon_plague]][[/img]]симптомов и благословенный симптом через: "
                              "[[b]]%d[[/b]] ход"},
}


def make_ui_loc(lang):
    return [(LOC_PREFIX + name, texts[lang]) for name, texts in UI_TEXTS.items()]


def script_names():
    """The texts the campaign script reads, without the prefix: {short name: English}."""
    return {name[len("skrolkpl_"):]: texts["en"] for name, texts in UI_TEXTS.items() if name != "skrolkpl_layout"}
