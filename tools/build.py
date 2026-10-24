"""Build skrolk_plagues.pack from the installed game's vanilla data.

usage: python -m tools.build --spike [--install]

Writes dist/skrolk_plagues.pack; --install copies it into the game's data folder.
Only the spike variant exists until the in-game gate (plan Task 2) is passed.
"""
import shutil
import sys

from tools.dbtable import decode_table, encode_table, load_schema
from tools.loc import decode_loc, encode_loc
from tools.packfile import read_pack, write_pack
from tools.paths import GAME_DATA, ROOT, SCHEMA
from tools.spike import make_spike_loc, make_spike_tables

PACK_NAME = "skrolk_plagues.pack"
TABLE_FILE = "skrolk_plagues"
SPIKE_SCRIPT = "script/campaign/mod/skrolkpl_spike.lua"
VARIANTS = ("spike",)


def _vanilla_tables():
    schema = load_schema(SCHEMA)
    vanilla = read_pack(GAME_DATA / "db.pack")

    def table(name):
        return decode_table(schema, name, vanilla[f"db/{name}/data__"])

    return schema, table


def _vanilla_loc():
    entries = {}
    for path, data in read_pack(GAME_DATA / "local_en.pack").items():
        if path.endswith(".loc"):
            entries.update(decode_loc(data))
    return entries


def build(out_path, variant="spike"):
    if variant not in VARIANTS:
        raise ValueError("unknown variant: %s" % variant)
    schema, table = _vanilla_tables()
    files = {f"db/{t.name}/{TABLE_FILE}": encode_table(schema, t) for t in make_spike_tables(table)}
    files[f"text/db/{TABLE_FILE}.loc"] = encode_loc(make_spike_loc(_vanilla_loc()))
    files[SPIKE_SCRIPT] = (ROOT / "src" / SPIKE_SCRIPT).read_bytes()
    write_pack(out_path, files)
    return files


def main(argv, dist=ROOT / "dist"):
    if "--spike" not in argv:
        raise SystemExit("only --spike can be built until the in-game gate is passed")
    dist.mkdir(exist_ok=True)
    build(dist / PACK_NAME, variant="spike")
    print("built %s" % (dist / PACK_NAME))
    if "--install" in argv:
        shutil.copyfile(dist / PACK_NAME, GAME_DATA / PACK_NAME)
        print("installed %s" % (GAME_DATA / PACK_NAME))


if __name__ == "__main__":
    main(sys.argv[1:])
