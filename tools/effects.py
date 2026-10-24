"""Effects of our own: vanilla behaviour under one tooltip line.

Black Death should read as a single "immune to attrition", but vanilla only splits it in two
(all-but-plague, and plague). Our effect carries the attrition records of both.
"""
from tools.rows import find, row, table_with

ATTRITION_IMMUNITY = "skrolkpl_effect_attrition_immunity"
_IMMUNITY_SOURCES = ("wh3_main_effect_attrition_immunity_all_except_plague",
                     "wh2_dlc16_effect_attrition_immunity_plague")
TEXTS = {"ru": "Защита от небоевых потерь", "en": "Immune to attrition"}


def make_effect_tables(table):
    effects = table("effects_tables")
    records = table("effect_bonus_value_attrition_record_junctions_tables")
    effect_col, record_col = records.col("effect"), records.col("attrition_record")
    seen, ours = set(), []
    for r in records.rows:
        if r[effect_col] in _IMMUNITY_SOURCES and r[record_col] not in seen:
            seen.add(r[record_col])
            ours.append(row(records, r, effect=ATTRITION_IMMUNITY))
    return [table_with(effects, row(effects, find(effects, "effect", _IMMUNITY_SOURCES[0]), effect=ATTRITION_IMMUNITY)),
            table_with(records, *ours)]


def make_effect_loc(lang):
    return [("effects_description_" + ATTRITION_IMMUNITY, TEXTS[lang])]
