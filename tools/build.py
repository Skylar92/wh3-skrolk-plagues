"""Build skrolk_plagues.pack and its translation packs from the installed game's vanilla data.

usage: python -m tools.build [--spike] [--always-rot] [--install]

Writes dist/skrolk_plagues.pack (texts in English) and one translation pack per TRANSLATION_PACKS entry, each
with its Workshop preview (the pack's name with .png, tools/preview.py); --install copies them into the game's data folder. A translation pack holds only the loc file, at the
main pack's path: the game loads it first (its name sorts first) and takes its file.
The release pack is the default; --spike builds the throwaway probe from plan Task 2.
--always-rot: a test build where every new plague rots.
"""
import shutil
import sys

from tools.cco import CCO_PATH, make_plague_cco
from tools.dbtable import decode_table, encode_table, load_schema
from tools.effects import make_effect_loc, make_effect_tables
from tools.feature import make_feature_loc, make_feature_tables
from tools.loc import decode_loc, encode_loc
from tools.packfile import read_pack, write_pack
from tools.preview import make_preview, save_preview
from tools.paths import GAME_DATA, ROOT, SCHEMA
from tools.render import render_core
from tools.rots import ROTS, make_rot_loc, make_rot_tables
from tools.rows import empty_like
from tools.spike import make_spike_loc, make_spike_tables
from tools.tooltip import TOOLTIP_PATH, make_plague_tooltip
from tools.ui_texts import make_ui_loc
from tools.window import WINDOW_PATH, make_plague_window
from tools.under import make_under_loc, make_under_tables
from tools.cauldron import make_cauldron_loc, make_cauldron_tables
from tools.symptoms import START_SYMPTOM, make_symptom_loc, make_symptom_tables, symptom_keys

PACK_NAME = "skrolk_plagues.pack"
TABLE_FILE = "skrolk_plagues"
SPIKE_SCRIPT = "script/campaign/mod/skrolkpl_spike.lua"
CORE_SCRIPT = "script/campaign/mod/skrolkpl.lua"
VARIANTS = ("spike", "release")
LANGS = ("en", "ru")
LOC_PATH = f"text/db/{TABLE_FILE}.loc"
TRANSLATION_PACKS = {"ru": "!skrolk_plagues_ru.pack"}


def _vanilla_tables():
    schema = load_schema(SCHEMA)
    vanilla = read_pack(GAME_DATA / "db.pack")

    def table(name):
        return decode_table(schema, name, vanilla[f"db/{name}/data__"])

    return schema, table


def _vanilla_loc(lang):
    entries = {}
    for path, data in read_pack(GAME_DATA / f"local_{lang}.pack").items():
        if path.endswith(".loc"):
            entries.update(decode_loc(data))
    return entries


def merge_tables(tables):
    """One table per name: rows of same-named tables concatenated in order."""
    merged = {}
    for t in tables:
        if t.name not in merged:
            merged[t.name] = empty_like(t)
        merged[t.name].rows.extend(t.rows)
    return list(merged.values())


def release_loc(lang):
    return (make_feature_loc(lang) + make_effect_loc(lang) + make_symptom_loc(lang, _vanilla_loc(lang))
            + make_rot_loc(lang) + make_under_loc(lang) + make_cauldron_loc(lang) + make_ui_loc(lang))


def build_translation(out_path, lang):
    files = {LOC_PATH: encode_loc(release_loc(lang))}
    write_pack(out_path, files)
    return files


def build(out_path, variant="release", lang="en", always_rot=False):
    if variant not in VARIANTS:
        raise ValueError("unknown variant: %s" % variant)
    if lang not in LANGS:
        raise ValueError("unknown language: %s" % lang)
    schema, table = _vanilla_tables()
    if variant == "spike":
        tables = make_spike_tables(table)
        loc = make_spike_loc(_vanilla_loc("en"))
        scripts = {SPIKE_SCRIPT: (ROOT / "src" / SPIKE_SCRIPT).read_bytes()}
    else:
        tables = merge_tables(make_feature_tables(table) + make_effect_tables(table) + make_symptom_tables(table)
                              + make_rot_tables(table) + make_under_tables(table)
                              + make_cauldron_tables(table))
        loc = release_loc(lang)
        core = (ROOT / "src" / CORE_SCRIPT).read_text(encoding="utf-8")
        effects = table("effects_tables")
        positive_good = {r[effects.col("effect")]: r[effects.col("is_positive_value_good")] for r in effects.rows}
        icons = {r[effects.col("effect")]: (r[effects.col("icon")], r[effects.col("icon_negative")]) for r in effects.rows}
        scripts = {CORE_SCRIPT: render_core(core, symptom_keys(), START_SYMPTOM, ROTS, positive_good, icons,
                                               always_rot).encode("utf-8"),
                   CCO_PATH: make_plague_cco(read_pack(GAME_DATA / "ui.pack")[CCO_PATH].decode("utf-8")).encode("utf-8"),
                   TOOLTIP_PATH: make_plague_tooltip(
                       read_pack(GAME_DATA / "ui3.pack")[TOOLTIP_PATH].decode("utf-8")).encode("utf-8"),
                   WINDOW_PATH: make_plague_window(
                       read_pack(GAME_DATA / "ui3.pack")[WINDOW_PATH].decode("utf-8")).encode("utf-8")}
    files = {f"db/{t.name}/{TABLE_FILE}": encode_table(schema, t) for t in tables}
    files[LOC_PATH] = encode_loc(loc)
    files.update(scripts)
    write_pack(out_path, files)
    return files


def preview_name(pack_name):
    return pack_name.replace(".pack", ".png")


def main(argv, dist=ROOT / "dist"):
    variant = "spike" if "--spike" in argv else "release"
    always_rot = "--always-rot" in argv  # test build: every new plague rots
    dist.mkdir(exist_ok=True)
    build(dist / PACK_NAME, variant=variant, always_rot=always_rot)
    print("built %s (%s%s)" % (dist / PACK_NAME, variant, ", always rot" if always_rot else ""))
    save_preview(make_preview(), dist / preview_name(PACK_NAME))
    names = [PACK_NAME, preview_name(PACK_NAME)]
    if variant == "release":
        for lang, name in TRANSLATION_PACKS.items():
            build_translation(dist / name, lang)
            save_preview(make_preview(lang), dist / preview_name(name))
            print("built %s (%s)" % (dist / name, lang))
            names += [name, preview_name(name)]
    if "--install" in argv:
        for name in names:  # the launcher wants each preview next to its pack
            shutil.copyfile(dist / name, GAME_DATA / name)
            print("installed %s" % (GAME_DATA / name))


if __name__ == "__main__":
    main(sys.argv[1:])
