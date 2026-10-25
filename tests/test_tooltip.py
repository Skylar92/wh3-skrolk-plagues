import xml.etree.ElementTree as ET

import pytest

from tools.packfile import read_pack
from tools.paths import GAME_DATA
from tools.tooltip import PLAGUE_ID, STRAIN_LINES, TOOLTIP_PATH, make_plague_tooltip

pytestmark = pytest.mark.game


@pytest.fixture(scope="module")
def vanilla():
    return read_pack(GAME_DATA / "ui3.pack")[TOOLTIP_PATH].decode("utf-8")


@pytest.fixture(scope="module")
def ours(vanilla):
    return make_plague_tooltip(vanilla)


def test_still_valid_xml(ours):
    ET.fromstring(ours)


def test_rot_lines_sit_in_each_effect_section_after_the_effects(ours):
    # author: the rot belongs among "Plague effects on Pestilens / Non-Pestilens", not under the tooltip
    root = ET.fromstring(ours)
    section = root.find("hierarchy/root/tooltip_dlc25_active_plague/effect_type_list/template_type")
    order = [child.tag for child in section]
    i = order.index("template_effect_bundle")
    assert order[i + 1:] == list(STRAIN_LINES)
    tooltip = root.find("hierarchy/root/tooltip_dlc25_active_plague")
    assert not [c.tag for c in tooltip if c.tag.startswith("skrolkpl_")]  # nothing left under the tooltip


def test_rot_lines_pick_the_side_by_faction_set(ours):
    root = ET.fromstring(ours)
    for n, line in enumerate(STRAIN_LINES, 1):
        comp = root.find("components/" + line)
        cbs = {c.get("callback_id"): (c.get("context_object_id"), c.get("context_function_id"))
               for c in comp.iter("callback_with_context")}
        ctx, label = cbs["ContextTextLabel"]
        assert ctx == "CcoPlagueEffectList"
        assert 'CcoFactionSetRecord("skrolkpl_positive")' in label and '"_ours_%d"' % n in label
        assert 'CcoFactionSetRecord("skrolkpl_negative")' in label and '"_enemy_%d"' % n in label
        assert cbs["ContextVisibilitySetter"][0] == "CcoPlagueEffectList"


def test_rot_lines_are_the_plague_own(ours):
    # author 2026-10-25: each plague has its own rot; a line reads the script value named by the plague's
    # id (its symptoms joined with "+", as skrolkpl.plague_id builds it)
    assert 'Filter(Key.Contains("skrolkpl_sym_")).JoinString(Key, "+")' in PLAGUE_ID
    root = ET.fromstring(ours)
    for line in STRAIN_LINES:
        comp = root.find("components/" + line)
        for c in comp.iter("callback_with_context"):
            assert c.get("context_function_id").startswith("(id = %s) =>" % PLAGUE_ID)
            assert '"skrolkpl_strain_" + id + "_' in c.get("context_function_id")


def test_effect_list_stores_the_plague_for_the_rot_lines(ours):
    root = ET.fromstring(ours)
    comp = root.find("components/effect_type_list")
    stores = [c.get("context_object_id") for c in comp.iter("callback_with_context")
              if c.get("callback_id") == "ContextObjectStore"]
    assert stores == ["CcoCampaignPlagueComposition"]


def test_guids_unique(ours):
    root = ET.fromstring(ours)
    guids = [c.get("this") for c in root.find("components")]
    assert len(guids) > 10 and len(set(guids)) == len(guids)


def test_rest_untouched(vanilla, ours):
    for tag in ("title", "effect_type_list", "infection_duration", "spread_chance", "immunity_duration",
                "template_entry"):
        assert vanilla.count("<%s" % tag) == ours.count("<%s" % tag)
