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
    lua.execute(render_core(TEMPLATE, KEYS, KEYS[0]))
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
    # no cooldown (author, 2026-10-24): a plague may be made any time its full price can be paid
    s = g.skrolkpl
    assert s.blocked_reason(100, 10000, 20, 2500) is None
    assert s.blocked_reason(19, 10000, 20, 2500) == ("food", 20)
    assert s.blocked_reason(100, 2499, 20, 2500) == ("gold", 2500)
    # slot levels count: 32 food is enough for a bare plague but not for one costing 38
    assert s.blocked_reason(32, 10000, 38, 2500) == ("food", 38)


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


def test_other_rituals_ignored(g):
    first_tick(g)
    n = len(calls(g))
    g.fire("RitualStartedEvent", g.ritual_context("wh2_main_ritual_skv_thirteen", PESTILENS))
    g.fire("RitualStartedEvent", g.ritual_context(DIRECT, "wh_main_emp_empire"))
    assert len(calls(g)) == n


def grid_now(g):
    return py_list(g.CONTEXT_VALUES["random_plague_component_list_" + PESTILENS])


def turn_start(g, turn):
    g.TURN = turn
    g.fire("FactionTurnStart", g.faction_context(PESTILENS))


def make_plague(g, ritual=DIRECT):
    g.fire("RitualStartedEvent", g.ritual_context(ritual, PESTILENS))


def test_grid_kept_within_the_turn(g):
    # author 2026-10-25: the grid changes every turn; within a turn several plagues use one layout
    first_tick(g)
    before = grid_now(g)
    g.RANDOM = g.lua.table_from([25 - i for i in range(30)])
    make_plague(g)
    make_plague(g, "wh3_main_ritual_nur_plague_target_settlement")
    assert grid_now(g) == before


def test_grid_reshuffled_every_turn(g):
    first_tick(g)
    before = grid_now(g)
    g.RANDOM = g.lua.table_from([25 - i for i in range(30)])
    turn_start(g, 2)
    assert grid_now(g) != before


def test_ai_turn_start_does_not_reshuffle(g):
    first_tick(g)
    before = grid_now(g)
    g.RANDOM = g.lua.table_from([25 - i for i in range(30)])
    g.TURN = 2
    g.fire("FactionTurnStart", g.faction_context("wh_main_emp_empire"))
    assert grid_now(g) == before


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
    assert "cooldown_until" not in TEMPLATE and "COOLDOWN_TURNS" not in TEMPLATE


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
    assert g.UI["dy_cost"].text == "Needs 20 [[img:icon_skaven_food]][[/img]]"


def test_infect_enabled_and_price_shown_when_affordable(g):
    first_tick(g)
    g.UI_TEXT["copy_of_dy_value"] = "+0%"  # the fake UI answers every slot with this text
    open_panel(g)
    infect = g.UI["button_infect_target"]
    assert infect.visible is True and infect.disabled is False
    assert g.UI["dy_cost"].text == "20 [[img:icon_skaven_food]][[/img]]  2500 [[img:icon_treasury]][[/img]]"


def test_infect_off_when_slot_levels_make_it_unaffordable(g):
    first_tick(g)
    g.FACTIONS[PESTILENS].food = 32
    g.UI_TEXT["copy_of_dy_value"] = "30"  # every slot at level 3 (spread 30%, others clamp): 20 + 2*9 = 38
    open_panel(g)
    assert g.UI["button_infect_target"].disabled is True
    assert g.UI["dy_cost"].text == "Needs 38 [[img:icon_skaven_food]][[/img]]"


def test_infect_switched_off_right_after_paying_when_next_plague_unaffordable(g):
    # in game the second plague went through although the first left too little food
    first_tick(g)
    g.FACTIONS[PESTILENS].food = 30
    open_panel(g)
    assert g.UI["button_infect_target"].disabled is False
    g.fire("RitualStartedEvent", g.ritual_context(DIRECT, PESTILENS))  # pays 20 of the 30 food
    assert g.UI["button_infect_target"].disabled is True
    assert g.UI["dy_cost"].text == "Needs 20 [[img:icon_skaven_food]][[/img]]"


def test_summon_button_hidden(g):
    first_tick(g)
    open_panel(g)
    assert g.UI["button_summon_cultist"].visible is False


def test_level_note_uses_food_icon(g):
    first_tick(g)
    open_panel(g)
    assert g.UI["tx_mutation_description"].text == "Each slot level: +2 [[img:icon_skaven_food]][[/img]]"


# --- start node, unlocking, guaranteed plague, blessed ---------------------

START = "skrolkpl_sym_k00"  # the test catalogue's stand-in for the start symptom


def test_slot_links_are_symmetric_and_connected(g):
    links = {s: set(py_list(g.skrolkpl.neighbours(s))) for s in range(18)}
    assert all(links[s] for s in links)
    assert all(s in links[n] for s in links for n in links[s])
    seen, todo = {0}, [0]
    while todo:
        for n in links[todo.pop()] - seen:
            seen.add(n); todo.append(n)
    assert seen == set(range(18))
    assert links[0] == {2, 3, 8} and links[1] == {2, 4, 11}  # read from the window (probe, 2026-10-25)


def lset(g, keys):
    return g.lua.table_from({k: True for k in keys})


def test_plague_path_needs_an_open_start_and_two_linked(g):
    grid = lua_list(g, KEYS[:18])            # slot s holds KEYS[s]
    usable = lset(g, KEYS[:18])
    assert g.skrolkpl.has_plague_path(grid, lset(g, [KEYS[0]]), usable)
    # start open but its neighbours (slots 2, 3, 8) unusable and nothing chains on
    assert not g.skrolkpl.has_plague_path(grid, lset(g, [KEYS[0]]), lset(g, [KEYS[0], KEYS[5]]))
    # nothing open
    assert not g.skrolkpl.has_plague_path(grid, lset(g, []), usable)


def test_build_grid_guarantees_a_plague_in_the_worst_case(g):
    # only three symptoms are off cooldown and only one of them is open
    usable_keys = [KEYS[3], KEYS[17], KEYS[24]]
    for seed in range(20):
        g.RANDOM = g.lua.table_from([(seed * 7 + i * 5) % 25 + 1 for i in range(200)])
        grid = g.skrolkpl.build_grid(lua_list(g, KEYS), lset(g, [KEYS[24]]), lset(g, usable_keys))
        assert len(py_list(grid)) == 18 and len(set(py_list(grid))) == 18
        assert g.skrolkpl.has_plague_path(grid, lset(g, [KEYS[24]]), lset(g, usable_keys)), seed


def states(g, key):
    c = g.COMPONENTS[key]
    return {k for k in ("UNLOCKED", "COOLDOWN", "BLESSED") if c[k]}


def test_only_the_start_symptom_is_open_at_first(g):
    first_tick(g)
    open_keys = {k for k in KEYS if "UNLOCKED" in states(g, k)}
    assert open_keys == {START}
    assert "UNLOCKED" in states(g, "wh3_dlc25_nur_mutation_spread_3")


def test_used_symptoms_become_open(g):
    first_tick(g)
    for k in (START, KEYS[5], KEYS[9]):
        g.COMPONENTS[k]["COOLDOWN"] = True   # the engine marks the plague's symptoms
    make_plague(g)
    open_keys = {k for k in KEYS if "UNLOCKED" in states(g, k)}
    assert {START, KEYS[5], KEYS[9]} <= open_keys
    assert len(open_keys) <= 4  # plus at most one, opened because all three now rest


def test_an_extra_symptom_opens_when_every_open_one_rests(g):
    first_tick(g)
    g.COMPONENTS[START]["COOLDOWN"] = True
    turn_start(g, 2)
    open_free = [k for k in KEYS if "UNLOCKED" in states(g, k) and "COOLDOWN" not in states(g, k)]
    assert len(open_free) == 1


def test_every_layout_can_make_a_plague(g):
    first_tick(g)
    for turn in range(2, 12):
        # rest a random-ish handful of symptoms each turn
        for i, k in enumerate(KEYS):
            g.COMPONENTS[k]["COOLDOWN"] = (i + turn) % 5 == 0  # five resting, as after a couple of plagues
        turn_start(g, turn)
        open_keys = [k for k in KEYS if "UNLOCKED" in states(g, k)]
        usable = [k for k in KEYS if "COOLDOWN" not in states(g, k)]
        assert g.skrolkpl.has_plague_path(g.skrolkpl.persistent.grid, lset(g, open_keys), lset(g, usable)), turn


def test_one_blessed_symptom_in_the_grid(g):
    first_tick(g)
    turn_start(g, 2)
    blessed = [k for k in KEYS if "BLESSED" in states(g, k)]
    assert len(blessed) == 1 and blessed[0] in py_list(g.skrolkpl.persistent.grid)


def test_save_from_before_start_node_migrates(g):
    # older saves opened every symptom; on load only the start symptom stays open
    g.SAVED = g.lua.table_from({"skrolkpl": g.lua.table_from({"grid": lua_list(g, KEYS[:18])})})
    for f in g.LOAD_CALLBACKS.values():
        f({})
    first_tick(g)
    assert {k for k in KEYS if "UNLOCKED" in states(g, k)} == {START}


def test_second_plague_possible_in_the_same_turn(g):
    # in game the first plague rested every open symptom, so nothing could start a second one
    first_tick(g)
    g.FACTIONS[PESTILENS].treasury = 100000
    grid = py_list(g.skrolkpl.persistent.grid)
    start_slot = grid.index(START)
    used = [START] + [grid[n] for n in py_list(g.skrolkpl.neighbours(start_slot))][:2]
    for k in used:
        g.COMPONENTS[k]["COOLDOWN"] = True
    make_plague(g)
    assert py_list(g.skrolkpl.persistent.grid) == grid  # the layout stays for the turn
    open_keys = [k for k in KEYS if "UNLOCKED" in states(g, k)]
    usable = [k for k in KEYS if "COOLDOWN" not in states(g, k)]
    assert g.skrolkpl.has_plague_path(g.skrolkpl.persistent.grid, lset(g, open_keys), lset(g, usable))
