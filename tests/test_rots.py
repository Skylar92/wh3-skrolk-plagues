import pytest

from conftest import vanilla_table
from tools.rots import (COUNT_WEIGHTS, INCIDENT_STABLE, INCIDENT_STRAIN, ROTS, STRAIN_BUNDLES, TARGET_BUNDLES,
                        make_rot_loc, make_rot_tables)

pytestmark = pytest.mark.game

ALLOWED_SCOPES = {"force_to_force_own", "region_to_region_own", "region_to_province_own_unseen",
                  "province_to_region_own_unseen", "province_to_province_own_unseen"}


@pytest.fixture(scope="module")
def vanilla(schema, vanilla_db):
    return lambda name: vanilla_table(schema, vanilla_db, name)


@pytest.fixture(scope="module")
def tables(vanilla):
    return {t.name: t for t in make_rot_tables(vanilla)}


def rows(tables, name):
    t = tables[name]
    return [dict(zip([f for f, _ in t.fields], r)) for r in t.rows]


def test_count_weights_from_the_spec():
    assert COUNT_WEIGHTS == (50, 30, 15, 5)


def test_six_of_each_kind_plus_a_rare_gift():
    kinds = [r.kind for r in ROTS]
    assert kinds.count("gift") >= 6 and kinds.count("rot") >= 6 and kinds.count("reverse") >= 6
    assert any(r.kind == "gift" and r.weight < 4 for r in ROTS)  # the rare, strong one


def test_good_and_bad_for_us_weigh_the_same():
    # author: the strain should help as often as it hurts; gifts are good for us, rot and reverse bad
    totals = {k: sum(r.weight for r in ROTS if r.kind == k) for k in ("gift", "rot", "reverse")}
    assert abs(totals["gift"] - (totals["rot"] + totals["reverse"])) <= 2, totals
    assert abs(totals["rot"] - totals["reverse"]) <= 2, totals


def test_kinds_have_the_right_signs():
    for r in ROTS:
        if r.kind == "gift":
            assert r.ours and r.enemy, r.id            # plus to us, minus to the enemy
        elif r.kind == "rot":
            assert r.ours and not r.enemy, r.id        # a minus to us only
        else:
            assert r.ours and r.enemy, r.id            # minus to us, a different plus to the enemy
            assert {e for e, _, _ in r.ours}.isdisjoint({e for e, _, _ in r.enemy}), r.id


def test_effects_exist_and_scopes_are_own(vanilla):
    known = {row[0] for row in vanilla("effects_tables").rows}
    for r in ROTS:
        for effect, scope, _ in r.ours + r.enemy:
            assert effect in known, (r.id, effect)
            assert scope in ALLOWED_SCOPES, (r.id, scope)


def test_one_rot_bundle_per_target_kind(tables):
    # the script fills these with the strain's summed effects (custom bundles); no rows of their own
    target = {r["key"]: r["bundle_target"] for r in rows(tables, "effect_bundles_tables")}
    assert target[TARGET_BUNDLES[("ours", "force")]] == "force"
    assert target[TARGET_BUNDLES[("enemy", "force")]] == "force"
    assert target[TARGET_BUNDLES[("ours", "region")]] == "region"
    assert target[TARGET_BUNDLES[("enemy", "region")]] == "region"
    assert {target[k] for k in STRAIN_BUNDLES.values()} == {"faction"}
    assert set(target) == set(TARGET_BUNDLES.values()) | set(STRAIN_BUNDLES.values())
    assert "effect_bundles_to_effects_junctions_tables" not in tables


def test_incidents(tables):
    incidents = {r["key"]: r for r in rows(tables, "incidents_tables")}
    assert set(incidents) == {INCIDENT_STRAIN, INCIDENT_STABLE}
    assert all(r["ui_image"] == "nur/plague_infected" for r in incidents.values())


def test_loc_both_languages():
    for lang in ("ru", "en"):
        loc = dict(make_rot_loc(lang))
        assert loc["incidents_localised_title_" + INCIDENT_STRAIN]
        assert loc["incidents_localised_description_" + INCIDENT_STABLE]
        assert loc["effect_bundles_localised_title_" + STRAIN_BUNDLES["ours"]]
        assert loc["effect_bundles_localised_title_" + STRAIN_BUNDLES["enemy"]]
        for key in TARGET_BUNDLES.values():
            assert loc["effect_bundles_localised_title_" + key]
