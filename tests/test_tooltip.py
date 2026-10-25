import re
import xml.etree.ElementTree as ET

import pytest

from tools.packfile import read_pack
from tools.paths import GAME_DATA
from tools.tooltip import STRAIN_LINES, TOOLTIP_PATH, make_plague_tooltip

pytestmark = pytest.mark.game


@pytest.fixture(scope="module")
def vanilla():
    return read_pack(GAME_DATA / "ui3.pack")[TOOLTIP_PATH].decode("utf-8")


@pytest.fixture(scope="module")
def ours(vanilla):
    return make_plague_tooltip(vanilla)


def test_still_valid_xml(ours):
    ET.fromstring(ours)


def test_strain_lines_follow_immunity_in_the_hierarchy(ours):
    root = ET.fromstring(ours)
    tooltip = root.find("hierarchy/root/tooltip_dlc25_active_plague")
    order = [child.tag for child in tooltip]
    i = order.index("immunity_duration")
    assert order[i + 1:i + 1 + len(STRAIN_LINES)] == [line for line, _ in STRAIN_LINES]


def test_strain_lines_show_script_text_only_for_skrolk_plagues(ours):
    root = ET.fromstring(ours)
    for line, script_object in STRAIN_LINES:
        comp = root.find("components/" + line)
        on_map = {c.get("callback_id"): c.get("context_function_id") for c in comp.iter("callback_with_context")
                  if c.get("context_object_id") == "CcoCampaignPlagueInfection"}
        assert 'ScriptObjectContext("%s").StringValue' % script_object in on_map["ContextTextLabel"]
        visible = on_map["ContextVisibilitySetter"]
        assert 'Key.Contains("skrolkpl_sym_")' in visible and script_object in visible
        in_window = [c.get("context_function_id") for c in comp.iter("callback_with_context")
                     if c.get("context_object_id") == "CcoCampaignPlagueComposition"]
        assert in_window == ["false"]  # the window's composition tooltip is not a live infection


def test_guids_unique(ours):
    root = ET.fromstring(ours)
    guids = [c.get("this") for c in root.find("components")]
    assert len(guids) > 10 and len(set(guids)) == len(guids)


def test_rest_untouched(vanilla, ours):
    for tag in ("title", "effect_type_list", "infection_duration", "spread_chance", "immunity_duration"):
        assert vanilla.count("<%s" % tag) == ours.count("<%s" % tag)
