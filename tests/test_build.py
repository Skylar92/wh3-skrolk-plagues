import pytest

from tools.build import PACK_NAME, SPIKE_SCRIPT, TABLE_FILE, build
from tools.dbtable import decode_table
from tools.loc import decode_loc
from tools.packfile import read_pack

pytestmark = pytest.mark.game


@pytest.fixture(scope="module")
def pack(tmp_path_factory):
    path = tmp_path_factory.mktemp("dist") / PACK_NAME
    build(path, variant="spike")
    return read_pack(path)


def test_spike_pack_has_tables_loc_and_script(pack, schema):
    members = decode_table(schema, "campaign_group_members_tables",
                           pack[f"db/campaign_group_members_tables/{TABLE_FILE}"])
    assert members.rows
    assert dict(decode_loc(pack[f"text/db/{TABLE_FILE}.loc"]))
    assert b"skrolkpl" in pack[SPIKE_SCRIPT]


def test_pack_references_resolve(pack, schema, vanilla_db):
    """Every reference column in our rows points at a vanilla or our own row.

    The game refuses to load a pack whose rows reference missing keys (crash on start).
    References into tables that are not in db.pack (engine enums such as RITUAL) are skipped.
    """
    from tools.dbtable import reference_columns
    def known(ref_table, ref_col):
        values = set()
        for source in (vanilla_db, pack):
            for path, data in source.items():
                parts = path.split("/")
                if len(parts) == 3 and parts[0] == "db" and parts[1] == ref_table:
                    t = decode_table(schema, ref_table, data)
                    values |= {r[t.col(ref_col)] for r in t.rows}
        return values

    in_db = {path.split("/")[1] for path in vanilla_db if path.startswith("db/")}
    missing = []
    for path, data in pack.items():
        parts = path.split("/")
        if parts[0] != "db":
            continue
        t = decode_table(schema, parts[1], data)
        for col, (ref_table, ref_col) in reference_columns(schema, t).items():
            if ref_table not in in_db:
                continue
            values = known(ref_table, ref_col)
            missing += [(t.name, col, r[t.col(col)]) for r in t.rows
                        if r[t.col(col)] not in (None, "") and r[t.col(col)] not in values]
    assert missing == []


def test_unknown_variant_rejected(tmp_path):
    with pytest.raises(ValueError):
        build(tmp_path / PACK_NAME, variant="release")
