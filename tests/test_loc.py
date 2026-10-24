import pytest

from tools.loc import decode_loc, encode_loc
from tools.packfile import read_pack
from tools.paths import GAME_DATA


def test_loc_roundtrip():
    entries = [("k1", "Стереть навсегда"), ("k2", "x||y")]
    assert decode_loc(encode_loc(entries)) == entries


@pytest.mark.game
def test_vanilla_loc_roundtrip():
    raw = read_pack(GAME_DATA / "local_ru.pack")["text/localisation__.loc"]
    assert encode_loc(decode_loc(raw)) == raw
