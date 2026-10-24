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


def test_unknown_variant_rejected(tmp_path):
    with pytest.raises(ValueError):
        build(tmp_path / PACK_NAME, variant="release")
