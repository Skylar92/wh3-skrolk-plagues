from pathlib import Path

import pytest
from lupa.lua51 import LuaRuntime

from tools.render import render_core

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = (ROOT / "src/script/campaign/mod/skrolkpl.lua").read_text(encoding="utf-8")
MOCK = (ROOT / "tests/lua/mock_game.lua").read_text(encoding="utf-8")
PESTILENS = "wh2_main_skv_clan_pestilens"
KEYS = ["skrolkpl_sym_k%02d" % i for i in range(25)]
DIRECT = "wh3_main_ritual_nur_plague_target_army"


@pytest.fixture
def g():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCK)
    lua.execute(render_core(TEMPLATE, KEYS))
    g = lua.globals()
    g.lua = lua
    return g


def calls(g, name=None):
    out = [tuple(c[i] for i in range(1, len(c) + 1)) for c in g.CALLS.values()]
    return [c for c in out if name is None or c[0] == name]


def first_tick(g):
    for f in g.FIRST_TICK.values():
        f()


def lua_list(g, values):
    return g.lua.table_from(list(values))


def py_list(t):
    return [t[i] for i in range(1, len(t) + 1)]


# --- pure helpers ---------------------------------------------------------

@pytest.mark.parametrize("text,step,level", [
    ("+30%", 10, 3), ("+0%", 10, 0), ("+10%", 10, 1), ("3 х.", 1, 3), ("0 x.", 1, 0),
    ("6 x.", 1, 3), ("", 1, 0), ("tx_none", 1, 0),
])
def test_level_from_text(g, text, step, level):
    assert g.skrolkpl.level_from_text(text, step) == level


@pytest.mark.parametrize("levels,price", [
    ((0, 0, 0), (20, 2500)), ((3, 3, 3), (38, 2500)), ((1, 2, 0), (26, 2500)),
])
def test_price(g, levels, price):
    assert g.skrolkpl.price(*levels) == price


def test_pick_grid_takes_eighteen_distinct_known_keys(g):
    grid = py_list(g.skrolkpl.pick_grid(lua_list(g, KEYS), 18))
    assert len(grid) == 18 and len(set(grid)) == 18 and set(grid) <= set(KEYS)


def test_pick_grid_shuffles(g):
    first = py_list(g.skrolkpl.pick_grid(lua_list(g, KEYS), 18))
    g.RANDOM = g.lua.table_from([25 - i for i in range(30)])
    second = py_list(g.skrolkpl.pick_grid(lua_list(g, KEYS), 18))
    assert first != second


def test_blocked_only_when_unaffordable(g):
    # no cooldown (author, 2026-10-24): a plague may be made any time it can be paid for
    s = g.skrolkpl
    assert s.blocked_reason(100, 10000) is None
    assert s.blocked_reason(19, 10000) == ("food", 20)
    assert s.blocked_reason(100, 2499) == ("gold", 2500)


def test_take_never_goes_negative(g):
    assert g.skrolkpl.take(2, 300, 20, 4000) == (2, 300)
    assert g.skrolkpl.take(52, 5000, 20, 4000) == (20, 4000)


# --- game flow ------------------------------------------------------------

def test_first_tick_sets_up_human_pestilens(g):
    first_tick(g)
    assert ("override_ui", "disable_nurgle_plagues_button", False) in calls(g)
    assert ("apply_effect_bundle", "skrolkpl_free_plague_rituals", PESTILENS, 0) in calls(g)
    unlocked = {c[2] for c in calls(g, "set_plague_component_state") if c[3] == "UNLOCKED"}
    assert set(KEYS) <= unlocked
    assert "wh3_dlc25_nur_mutation_spread_3" in unlocked
    grid = py_list(g.CONTEXT_VALUES["random_plague_component_list_" + PESTILENS])
    assert len(grid) == 18


def test_ai_pestilens_left_alone(g):
    g.FACTIONS[PESTILENS].human = False
    first_tick(g)
    g.fire("RitualStartedEvent", g.ritual_context(DIRECT, PESTILENS))
    assert calls(g) == []


def test_plague_ritual_charges_price(g):
    first_tick(g)
    g.skrolkpl.pending_levels = g.lua.table_from([1, 2, 0])
    g.fire("RitualStartedEvent", g.ritual_context(DIRECT, PESTILENS))
    assert ("faction_add_pooled_resource", PESTILENS, "skaven_food", "skrolkpl_plague_food", -26) in calls(g)
    assert ("treasury_mod", PESTILENS, -2500) in calls(g)


def test_two_plagues_in_one_turn_both_charged(g):
    first_tick(g)
    g.FACTIONS[PESTILENS].treasury = 10000
    g.fire("RitualStartedEvent", g.ritual_context(DIRECT, PESTILENS))
    g.fire("RitualStartedEvent", g.ritual_context("wh3_main_ritual_nur_plague_target_settlement", PESTILENS))
    assert [c for c in calls(g) if c[0] == "treasury_mod"] == [("treasury_mod", PESTILENS, -2500)] * 2


def test_charge_capped_when_short(g):
    first_tick(g)
    g.FACTIONS[PESTILENS].food = 2
    g.FACTIONS[PESTILENS].treasury = 300
    g.fire("RitualStartedEvent", g.ritual_context(DIRECT, PESTILENS))
    assert ("faction_add_pooled_resource", PESTILENS, "skaven_food", "skrolkpl_plague_food", -2) in calls(g)
    assert ("treasury_mod", PESTILENS, -300) in calls(g)


def test_grid_reshuffled_after_plague(g):
    first_tick(g)
    before = py_list(g.CONTEXT_VALUES["random_plague_component_list_" + PESTILENS])
    g.RANDOM = g.lua.table_from([25 - i for i in range(30)])
    g.fire("RitualStartedEvent", g.ritual_context(DIRECT, PESTILENS))
    after = py_list(g.CONTEXT_VALUES["random_plague_component_list_" + PESTILENS])
    assert before != after


def test_other_rituals_ignored(g):
    first_tick(g)
    n = len(calls(g))
    g.fire("RitualStartedEvent", g.ritual_context("wh2_main_ritual_skv_thirteen", PESTILENS))
    g.fire("RitualStartedEvent", g.ritual_context(DIRECT, "wh_main_emp_empire"))
    assert len(calls(g)) == n


def test_state_roundtrip(g):
    first_tick(g)
    grid = py_list(g.skrolkpl.persistent.grid)
    for f in g.SAVE_CALLBACKS.values():
        f({})
    g.skrolkpl.persistent.grid = None
    for f in g.LOAD_CALLBACKS.values():
        f({})
    assert py_list(g.skrolkpl.persistent.grid) == grid


def test_fresh_state_when_nothing_saved(g):
    for f in g.LOAD_CALLBACKS.values():
        f({})
    assert g.skrolkpl.persistent.grid is None
    first_tick(g)
    assert len(py_list(g.skrolkpl.persistent.grid)) == 18


def test_no_cooldown_left():
    assert "cooldown_until" not in TEMPLATE and "COOLDOWN" not in TEMPLATE


def test_no_plain_find():
    import re
    assert not re.search(r"find\([^)]*,\s*1\s*,\s*true\s*\)", TEMPLATE)


# --- the plague window ----------------------------------------------------

def open_panel(g):
    g.PANEL_OPEN = True
    g.fire("PanelOpenedCampaign", g.lua.table_from({"string": "dlc25_nurgle_plagues"}))


def test_infect_stays_visible_but_disabled_when_unaffordable(g):
    first_tick(g)
    g.FACTIONS[PESTILENS].food = 5
    open_panel(g)
    infect = g.UI["button_infect_target"]
    assert infect.visible is True
    assert infect.disabled is True and infect.state == "inactive"
    assert g.UI["dy_cost"].text == "Needs 20 food"


def test_infect_enabled_and_price_shown_when_affordable(g):
    first_tick(g)
    g.UI_TEXT["copy_of_dy_value"] = "+0%"  # the fake UI answers every slot with this text
    open_panel(g)
    infect = g.UI["button_infect_target"]
    assert infect.visible is True and infect.disabled is False
    assert g.UI["dy_cost"].text == "20 food, 2500 gold"


def test_window_reopened_after_plague_to_show_new_grid(g):
    first_tick(g)
    open_panel(g)
    g.fire("RitualStartedEvent", g.ritual_context(DIRECT, PESTILENS))
    # the window reads the grid only when it opens: close it with its own button, reopen from the HUD
    assert calls(g, "click") == [("click", "button_close"), ("click", "button_nurgle_plagues")]


def test_infect_switched_off_right_after_paying_when_next_plague_unaffordable(g):
    # in game the second plague went through although the first left too little food
    first_tick(g)
    g.FACTIONS[PESTILENS].food = 30
    open_panel(g)
    assert g.UI["button_infect_target"].disabled is False
    g.fire("RitualStartedEvent", g.ritual_context(DIRECT, PESTILENS))  # pays 20 of the 30 food
    assert g.UI["button_infect_target"].disabled is True
    assert g.UI["dy_cost"].text == "Needs 20 food"


def test_summon_button_hidden(g):
    first_tick(g)
    open_panel(g)
    assert g.UI["button_summon_cultist"].visible is False
