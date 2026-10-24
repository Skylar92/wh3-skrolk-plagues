import struct

import pytest

from tools.packfile import read_pack, write_pack
from tools.paths import GAME_DATA


def test_roundtrip(tmp_path):
    files = {"db/a_tables/x": b"\x01\x02", "script/campaign/mod/z.lua": b"-- hi"}
    write_pack(tmp_path / "t.pack", files)
    assert read_pack(tmp_path / "t.pack") == files


def test_header_is_mod_pack(tmp_path):
    write_pack(tmp_path / "t.pack", {"a/b": b"x"})
    raw = (tmp_path / "t.pack").read_bytes()
    assert raw[:4] == b"PFH5" and struct.unpack_from("<I", raw, 4)[0] == 3


@pytest.mark.game
def test_reads_vanilla_script_pack():
    files = read_pack(GAME_DATA / "data_script.pack")
    lua = files["script/campaign/wh3_dlc29_archaon_narrative.lua"]
    assert b"block_occupation_effect_bundle" in lua
