from pathlib import Path

import pytest
from lupa.lua51 import LuaRuntime

from tools.render import render_core
from tools.rots import ROTS

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
    icons = {"wh_main_effect_force_stat_armour": ("armour.png", "armour.png"),
             "wh_main_effect_force_stat_leadership": ("leadership.png", "leadership.png")}
    lua.execute(render_core(TEMPLATE, KEYS, KEYS[0], ROTS, None, icons))
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
    # the window lays the published list out backwards; the script's grid is the slot order
    return py_list(g.CONTEXT_VALUES["random_plague_component_list_" + PESTILENS])[::-1]


def test_window_gets_the_grid_backwards(g):
    # in game the self-check showed slot n holding list entry 18 - n (all 18 mismatched): publish the
    # grid reversed so slot n shows grid entry n + 1, as SLOT_LINKS assumes
    first_tick(g)
    published = py_list(g.CONTEXT_VALUES["random_plague_component_list_" + PESTILENS])
    assert published == py_list(g.skrolkpl.persistent.grid)[::-1]


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


# --- strain rot -------------------------------------------------------------

EMPIRE = "wh_main_emp_empire"


@pytest.mark.parametrize("roll,count", [(1, 0), (50, 0), (51, 1), (80, 1), (81, 2), (95, 2), (96, 3), (100, 3)])
def test_rot_count_follows_50_30_15_5(g, roll, count):
    g.RANDOM = g.lua.table_from([roll] + [1] * 20)
    assert len(py_list(g.skrolkpl.roll_strain())) == count


def test_rolled_rots_are_distinct(g):
    g.RANDOM = g.lua.table_from([100] + [1] * 30)   # three rots, always the first by weight
    strain = py_list(g.skrolkpl.roll_strain())
    assert len(strain) == 3 and len(set(strain)) == 3


# two plagues of Skrolk's, as the infection events show them: symptoms plus a mutation slot
PLAGUE_A = ["skrolkpl_sym_k03", "skrolkpl_sym_k01", "wh3_dlc25_nur_mutation_duration_1", "skrolkpl_sym_k02"]
PLAGUE_B = ["skrolkpl_sym_k04", "skrolkpl_sym_k05", "skrolkpl_sym_k06"]
ID_A = "skrolkpl_sym_k01+skrolkpl_sym_k02+skrolkpl_sym_k03"
ID_B = "skrolkpl_sym_k04+skrolkpl_sym_k05+skrolkpl_sym_k06"


def set_strain(g, ids, plague=ID_A, turns=3):
    g.skrolkpl.persistent.strains[plague] = g.lua.table_from(
        {"rots": g.lua.table_from(ids), "turns": turns})


def strain_of(g, plague):
    entry = g.skrolkpl.persistent.strains[plague]
    return None if entry is None else py_list(entry.rots)


def infect_force(g, cqi, faction, creator=PESTILENS, symptoms=PLAGUE_A, removed=False, creation=False):
    g.fire("MilitaryForceInfectionEvent",
           g.force_infection(cqi, faction, creator, removed, lua_list(g, symptoms), creation))


def infect_region(g, key, owner, creator=PESTILENS, symptoms=PLAGUE_A, creation=False):
    g.fire("RegionInfectionEvent", g.region_infection(key, owner, creator, lua_list(g, symptoms), creation))


FORCE_OURS, FORCE_ENEMY = "skrolkpl_strain_force_ours", "skrolkpl_strain_force_enemy"
REGION_OURS, REGION_ENEMY = "skrolkpl_strain_region_ours", "skrolkpl_strain_region_enemy"


def applied(g, kind):
    """[(bundle key, target, {effect: value}, duration)] for apply_custom_effect_bundle_to_<kind>."""
    out = []
    for c in calls(g, "apply_custom_" + kind):
        b = c[1]
        effects = {e[1]: e[3] for e in b.effects.values()}
        out.append((b.key, c[2], effects, b.duration))
    return out


def test_plague_id_is_its_symptoms_sorted(g):
    # a plague is known by its three symptoms; the tooltip rebuilds the same id from them
    plague = g.force_infection(1, EMPIRE, PESTILENS, False, lua_list(g, PLAGUE_A)).plague()
    assert g.skrolkpl.plague_id(plague) == ID_A


def test_plague_without_our_symptoms_has_no_id(g):
    plague = g.force_infection(1, EMPIRE, PESTILENS, False, lua_list(g, ["wh2_main_skv_plague_skrolk"])).plague()
    assert g.skrolkpl.plague_id(plague) is None


def test_infected_enemy_army_gets_the_enemy_side(g):
    first_tick(g)
    set_strain(g, ["swift_paws"])
    infect_force(g, 7, EMPIRE)
    assert applied(g, "force") == [(FORCE_ENEMY, 7, {"wh_main_effect_force_all_campaign_movement_range": -10.0}, 3)]


def test_one_rot_bundle_per_target_with_summed_effects(g):
    # author: one "strain rot" bundle on the army, values summed like the message and the tooltip
    first_tick(g)
    set_strain(g, ["horned_blessing", "cowed_and_steeled"])
    infect_force(g, 8, PESTILENS)
    assert applied(g, "force") == [(FORCE_OURS, 8, {"wh_main_effect_force_stat_leadership": 5.0,
                                                    "wh_main_effect_force_stat_melee_defence": 6.0}, 3)]


def test_rot_lasts_as_long_as_the_plague(g):
    # author: the plague mutated as a whole, so its rot lasts the plague's duration (3 + duration level)
    first_tick(g)
    g.FACTIONS[PESTILENS].treasury = 100000
    g.FACTIONS[PESTILENS].food = 1000
    g.skrolkpl.pending_levels = g.lua.table_from([2, 0, 0])
    g.RANDOM = g.lua.table_from([60] + [1] * 30)
    make_plague(g)
    infect_force(g, 9, EMPIRE, creation=True)
    durations = [a[3] for a in applied(g, "force") if a[1] == 9]
    assert durations and all(d == 5 for d in durations)
    assert g.LAUNCHED.payload.bundle.duration == 5


def test_infected_own_army_gets_our_side(g):
    first_tick(g)
    set_strain(g, ["swift_paws"])
    infect_force(g, 8, PESTILENS)
    assert applied(g, "force") == [(FORCE_OURS, 8, {"wh_main_effect_force_all_campaign_movement_range": 10.0}, 3)]


def test_rot_removed_when_plague_ends(g):
    first_tick(g)
    set_strain(g, ["swift_paws"])
    infect_force(g, 7, EMPIRE)
    infect_force(g, 7, EMPIRE, removed=True)
    assert ("remove_effect_bundle_from_force", FORCE_ENEMY, 7) in calls(g)


def test_foreign_plague_takes_the_rot_away(g):
    first_tick(g)
    set_strain(g, ["swift_paws"])
    infect_force(g, 7, EMPIRE)
    infect_force(g, 7, EMPIRE, creator="wh3_main_nur_poxmakers_of_nurgle", symptoms=[])
    assert ("remove_effect_bundle_from_force", FORCE_ENEMY, 7) in calls(g)


def test_settlement_rot_follows_plague_state(g):
    first_tick(g)
    set_strain(g, ["fecundity"])
    infect_region(g, "r1", EMPIRE)
    assert applied(g, "region") == [(REGION_ENEMY, "r1", {"wh3_main_effect_province_growth_plague": -15.0}, 3)]
    g.fire("RegionPlagueStateChanged", g.region_plague_state("r1", False))
    assert ("remove_effect_bundle_from_region", REGION_ENEMY, "r1") in calls(g)


def test_army_effects_stay_off_settlements(g):
    first_tick(g)
    set_strain(g, ["swift_paws"])   # an army-only rot
    infect_region(g, "r1", EMPIRE)
    assert applied(g, "region") == []


def new_plague(g, rolls, symptoms=PLAGUE_B, cqi=8, infection_first=False):
    g.FACTIONS[PESTILENS].treasury = 100000
    g.FACTIONS[PESTILENS].food = 1000
    g.RANDOM = g.lua.table_from(rolls)
    if infection_first:
        infect_force(g, cqi, EMPIRE, symptoms=symptoms, creation=True)
        make_plague(g)
    else:
        make_plague(g)
        infect_force(g, cqi, EMPIRE, symptoms=symptoms, creation=True)


def test_each_plague_keeps_its_own_rot(g):
    # author 2026-10-25: a second plague replaced the first plague's rot on its targets; each plague
    # carries its own strain
    first_tick(g)
    set_strain(g, ["swift_paws"])
    infect_force(g, 7, EMPIRE)
    g.CALLS = g.lua.table_from([])
    new_plague(g, [81] + [1] * 30)   # two rots for plague B
    assert strain_of(g, ID_A) == ["swift_paws"]
    assert len(strain_of(g, ID_B)) == 2
    assert not [c for c in calls(g) if c[0].startswith("remove_effect_bundle_from_force") and c[2] == 7]
    assert [a[1] for a in applied(g, "force")] == [8]


def test_rot_found_when_the_infection_comes_before_the_ritual(g):
    # the game may report the new plague's first infection before the ritual event
    first_tick(g)
    new_plague(g, [81] + [1] * 30, infection_first=True)
    assert len(strain_of(g, ID_B)) == 2
    assert [a[1] for a in applied(g, "force")] == [8]


def test_spread_keeps_the_plague_rot(g):
    first_tick(g)
    new_plague(g, [81] + [1] * 30)
    rots = strain_of(g, ID_B)
    infect_force(g, 11, EMPIRE, symptoms=PLAGUE_B)   # spread, not a new plague
    assert strain_of(g, ID_B) == rots
    assert [a[1] for a in applied(g, "force")] == [8, 11]


def test_same_symptoms_again_give_the_plague_a_new_rot(g):
    # the same three symptoms after their rest: one id, so the newest strain holds on all its targets
    first_tick(g)
    set_strain(g, ["swift_paws"], plague=ID_B)
    infect_force(g, 7, EMPIRE, symptoms=PLAGUE_B)
    g.CALLS = g.lua.table_from([])
    new_plague(g, [81] + [1] * 30)
    assert strain_of(g, ID_B) != ["swift_paws"]
    assert sorted(a[1] for a in applied(g, "force")) == [7, 8]


def test_plague_with_no_targets_left_is_forgotten(g):
    first_tick(g)
    set_strain(g, ["swift_paws"])
    infect_force(g, 7, EMPIRE)
    infect_force(g, 7, EMPIRE, removed=True)
    turn_start(g, 2)
    assert strain_of(g, ID_A) is None
    assert g.CONTEXT_VALUES["skrolkpl_strain_" + ID_A + "_enemy_1"] == ""


def plates(g):
    return {b.key: {e[1]: e[3] for e in b.effects.values()} for b in g.LAUNCHED.payload.bundles.values()}


def test_strain_message_shows_us_and_the_enemy_in_one_event(g):
    # in game a reverse strain showed our attack -5 but not the enemy's replenishment +10%:
    # one event, a plate for each side, values summed
    first_tick(g)
    g.skrolkpl.announce_strain(g.lua.table_from(["feverish_foes"]), 3)
    assert ("launch_custom_incident", "skrolkpl_incident_strain_changed", PESTILENS) in calls(g)
    assert plates(g) == {
        "skrolkpl_strain_ours": {"wh_main_effect_force_stat_melee_attack": -5.0},
        "skrolkpl_strain_enemy": {"wh_main_effect_force_all_campaign_replenishment_rate": 10.0},
    }


def test_strain_message_sums_and_skips_an_empty_enemy_plate(g):
    first_tick(g)
    g.skrolkpl.announce_strain(g.lua.table_from(["burrow_panic", "the_shakes"]), 3)  # rot only: nothing for them
    assert plates(g) == {"skrolkpl_strain_ours": {"wh_main_effect_force_stat_leadership": -6.0,
                                                  "wh_main_effect_force_stat_melee_defence": -5.0}}


def test_clean_strain_message(g):
    first_tick(g)
    g.RANDOM = g.lua.table_from([10] + [1] * 30)
    make_plague(g)
    assert ("trigger_incident", PESTILENS, "skrolkpl_incident_strain_stable", True) in calls(g)


def test_strain_and_infected_survive_save(g):
    first_tick(g)
    set_strain(g, ["swift_paws"])
    infect_force(g, 7, EMPIRE)
    for f in g.SAVE_CALLBACKS.values():
        f({})
    g.skrolkpl.persistent.strains = g.lua.table_from({})
    for f in g.LOAD_CALLBACKS.values():
        f({})
    assert strain_of(g, ID_A) == ["swift_paws"]
    assert g.skrolkpl.persistent.infected.forces["7"].plague == ID_A


def test_old_save_with_one_strain_for_all_loads(g):
    # saves from before per-plague strains: strain = rot ids, infected = {[cqi] = ours}
    g.SAVED = g.lua.table_from({"skrolkpl": g.lua.table_from({
        "grid": lua_list(g, KEYS[:18]), "unlocked": g.lua.table_from({START: True}),
        "strain": lua_list(g, ["swift_paws"]), "strain_turns": 3,
        "infected": g.lua.table_from({"forces": g.lua.table_from({"7": False}),
                                      "regions": g.lua.table_from({})})})})
    for f in g.LOAD_CALLBACKS.values():
        f({})
    first_tick(g)
    infect_force(g, 7, EMPIRE, removed=True)
    assert ("remove_effect_bundle_from_force", FORCE_ENEMY, 7) in calls(g)


def tooltip_lines(g, plague, side):
    return [g.CONTEXT_VALUES["skrolkpl_strain_%s_%s_%d" % (plague, side, i)] for i in range(1, 7)]


def test_strain_text_published_for_the_plague_tooltip(g):
    # the tooltip copy shows these script values on infections of that plague
    g.LOCALISED = g.lua.table_from({
        "effects_description_wh_main_effect_force_stat_armour": "Armour: %+n",
        "effects_description_wh_main_effect_force_stat_leadership": "Leadership: %+n",
    })
    first_tick(g)
    set_strain(g, ["thick_hide", "burrow_panic"])
    g.skrolkpl.publish_strains()
    ours, enemy = tooltip_lines(g, ID_A, "ours"), tooltip_lines(g, ID_A, "enemy")
    assert "[[col:green]]Armour: +10" in ours[0] and "[[col:red]]Leadership: -6" in ours[1]
    assert ours[0].startswith("[[img:")  # the effect's own icon, like the plague's effect lines
    assert ours[2:] == [""] * 4
    assert "[[col:red]]Armour: -10" in enemy[0] and enemy[1:] == [""] * 5


def test_tooltip_lines_for_any_symptom_order(g):
    # the tooltip joins the plague's symptoms in the order the game lists them, which we do not know
    import itertools
    first_tick(g)
    set_strain(g, ["thick_hide"])
    g.skrolkpl.publish_strains()
    for order in itertools.permutations(ID_A.split("+")):
        assert tooltip_lines(g, "+".join(order), "ours")[0] != ""


def test_two_plagues_two_sets_of_tooltip_lines(g):
    first_tick(g)
    set_strain(g, ["thick_hide"])
    set_strain(g, ["swift_paws"], plague=ID_B)
    g.skrolkpl.publish_strains()
    assert tooltip_lines(g, ID_A, "ours")[0] != tooltip_lines(g, ID_B, "ours")[0]


def test_clean_strain_hides_the_tooltip_lines(g):
    first_tick(g)
    set_strain(g, [])
    g.skrolkpl.publish_strains()
    assert all(l == "" for side in ("ours", "enemy") for l in tooltip_lines(g, ID_A, side))


def test_strain_message_bundles_leave_the_faction(g):
    # in game the message's bundles stayed on the faction bar for the plague's duration
    first_tick(g)
    g.RANDOM = g.lua.table_from([60] + [1] * 30)
    make_plague(g)
    removed = {c[1] for c in calls(g, "remove_effect_bundle") if c[2] == PESTILENS}
    assert {"skrolkpl_strain_ours", "skrolkpl_strain_enemy"} <= removed


def test_saved_grid_with_dropped_symptoms_is_rebuilt(g):
    # 2026-10-25 dropped two Nurgle twins from the catalogue; older saves may still place them
    g.SAVED = g.lua.table_from({"skrolkpl": g.lua.table_from({
        "grid": lua_list(g, KEYS[:17] + ["skrolkpl_sym_settlement_1"]),
        "unlocked": g.lua.table_from({START: True})})})
    for f in g.LOAD_CALLBACKS.values():
        f({})
    first_tick(g)
    assert set(py_list(g.skrolkpl.persistent.grid)) <= set(KEYS)


def test_strains_are_sometimes_all_bad_sometimes_all_good_sometimes_mixed(g):
    # author saw only mixed strains in a few tries; over many rolls every kind of outcome must turn up
    import random
    rng = random.Random(13)
    g.RANDOM_FN = lambda n: rng.randint(1, n)
    good = {r.id for r in ROTS if r.kind == "gift"}
    outcome = {"clean": 0, "all_good": 0, "all_bad": 0, "mixed": 0}
    for _ in range(10000):
        strain = py_list(g.skrolkpl.roll_strain())
        if not strain:
            outcome["clean"] += 1
        elif all(r in good for r in strain):
            outcome["all_good"] += 1
        elif not any(r in good for r in strain):
            outcome["all_bad"] += 1
        else:
            outcome["mixed"] += 1
    assert 4500 < outcome["clean"] < 5500                     # 50 %
    # one rot: half gifts; two or three: mostly mixed, sometimes one-sided
    assert outcome["all_bad"] > 1500 and outcome["all_good"] > 1500 and outcome["mixed"] > 600, outcome


def test_strain_lines_sum_the_same_effect(g):
    # in game: Blessing (leadership +10, defence +6 / enemy -10, -6) and Cowed and Steeled (our leadership
    # -5 / enemy defence +4) showed "-5" and "+10" lines; the message summed them to +5. Sum in the tooltip.
    g.LOCALISED = g.lua.table_from({
        "effects_description_wh_main_effect_force_stat_leadership": "Leadership: %+n",
        "effects_description_wh_main_effect_force_stat_melee_defence": "Defence: %+n",
    })
    first_tick(g)
    set_strain(g, ["horned_blessing", "cowed_and_steeled"])
    g.skrolkpl.publish_strains()
    ours, enemy = tooltip_lines(g, ID_A, "ours"), tooltip_lines(g, ID_A, "enemy")
    assert [l for l in ours if l] == [l for l in ours[:2]] and ours[2] == ""
    assert "[[col:green]]Leadership: +5[[/col]]" in ours[0] and "[[col:green]]Defence: +6[[/col]]" in ours[1]
    assert "[[col:red]]Leadership: -10[[/col]]" in enemy[0] and "[[col:red]]Defence: -2[[/col]]" in enemy[1]
    assert enemy[2] == ""


def test_strain_effects_that_cancel_out_leave_no_line(g):
    first_tick(g)
    set_strain(g, ["swift_paws", "sluggish"])   # movement +10 and -10 for us
    g.skrolkpl.publish_strains()
    assert tooltip_lines(g, ID_A, "ours") == [""] * 6
