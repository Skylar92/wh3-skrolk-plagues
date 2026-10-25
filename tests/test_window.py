import xml.etree.ElementTree as ET

import pytest

from tools.keys import PESTILENS
from tools.packfile import read_pack
from tools.paths import GAME_DATA
from tools.window import VANILLA_COUNTER, WINDOW_PATH, make_plague_window

pytestmark = pytest.mark.game


@pytest.fixture(scope="module")
def vanilla():
    return read_pack(GAME_DATA / "ui3.pack")[WINDOW_PATH].decode("utf-8")


def test_counter_says_next_turn_for_pestilens_only(vanilla):
    # the vanilla counter reads "Plagues until new Blessed Symptoms and Symptom locations: 1", but
    # Skrolk's layout changes every turn; Nurgle keeps the vanilla text
    ours = make_plague_window(vanilla)
    ET.fromstring(ours)
    assert vanilla.count(VANILLA_COUNTER) == 1 and VANILLA_COUNTER not in ours
    assert "&quot;%s&quot;" % PESTILENS in ours
    assert "Loc(&quot;skrolkpl_layout&quot;, 1)" in ours
    assert "wh3_dlc25_plagues_instability_turn" in ours   # the vanilla branch stays
    assert len(ours) - len(vanilla) < 400                 # nothing else changed
