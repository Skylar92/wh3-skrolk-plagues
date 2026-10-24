import re

import pytest

from tools.build import CORE_SCRIPT, PACK_NAME, SPIKE_SCRIPT, TABLE_FILE, build
from tools.dbtable import decode_table, reference_columns
from tools.loc import decode_loc
from tools.packfile import read_pack
from tools.symptoms import symptom_keys

pytestmark = pytest.mark.game


def _build(tmp_path_factory, variant):
    path = tmp_path_factory.mktemp(variant) / PACK_NAME
    build(path, variant=variant)
    return read_pack(path)


@pytest.fixture(scope="module")
def spike(tmp_path_factory):
    return _build(tmp_path_factory, "spike")


@pytest.fixture(scope="module")
def release(tmp_path_factory):
    return _build(tmp_path_factory, "release")


def table(pack, schema, name):
    return decode_table(schema, name, pack[f"db/{name}/{TABLE_FILE}"])


def test_spike_pack_has_tables_loc_and_script(spike, schema):
    assert table(spike, schema, "campaign_group_members_tables").rows
    assert dict(decode_loc(spike[f"text/db/{TABLE_FILE}.loc"]))
    assert b"skrolkpl" in spike[SPIKE_SCRIPT]


def test_release_merges_tables_shared_by_feature_and_catalogue(release, schema):
    setups = table(release, schema, "plague_component_setups_tables")
    components = {r[setups.col("component")] for r in setups.rows}
    assert set(symptom_keys()) <= components                 # from the catalogue
    assert "wh3_dlc25_nur_mutation_spread_3" in components   # from the feature
    bundles = {r[0] for r in table(release, schema, "effect_bundles_tables").rows}
    assert "skrolkpl_free_plague_rituals" in bundles and "skrolkpl_sym_sk_frenzy_pos" in bundles


def test_release_has_no_spike_leftovers(release):
    assert SPIKE_SCRIPT not in release
    assert not any(b"skrolkpl_spike" in data for data in release.values())


def test_release_script_lists_the_catalogue(release):
    lua = release[CORE_SCRIPT].decode("utf-8")
    assert "--@@" not in lua
    assert sum(1 for k in symptom_keys() if '"%s"' % k in lua) == len(symptom_keys())
    assert not re.search(r"find\([^)]*,\s*1\s*,\s*true\s*\)", lua)


def test_release_loc_names_every_symptom(release):
    loc = dict(decode_loc(release[f"text/db/{TABLE_FILE}.loc"]))
    for key in symptom_keys():
        assert loc.get("plague_components_localised_name_" + key), key


@pytest.mark.parametrize("variant", ["spike", "release"])
def test_pack_references_resolve(variant, tmp_path_factory, schema, vanilla_db):
    """Every reference column in our rows points at a vanilla or our own row.

    The game refuses to load a pack whose rows reference missing keys (crash on start).
    References into tables that are not in db.pack (engine enums such as RITUAL) are skipped.
    """
    pack = _build(tmp_path_factory, variant)

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


def test_release_has_no_duplicate_keys(release, schema):
    from tools.dbtable import key_columns
    for path, data in release.items():
        parts = path.split("/")
        if parts[0] != "db":
            continue
        t = decode_table(schema, parts[1], data)
        cols = [t.col(c) for c in key_columns(schema, t)]
        keys = [tuple(r[i] for i in cols) for r in t.rows]
        assert len(keys) == len(set(keys)), t.name


def test_unknown_variant_rejected(tmp_path):
    with pytest.raises(ValueError):
        build(tmp_path / PACK_NAME, variant="bogus")


def test_release_ships_the_plague_window_script(release):
    from tools.cco import CCO_PATH
    cco = release[CCO_PATH].decode("utf-8")
    assert '"skrolkpl_positive"' in cco and '"plague_effect_set_nurgle_positive"' in cco
