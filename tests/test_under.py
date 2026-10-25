import pytest

from conftest import vanilla_table
from tools.under import UNDER_BUNDLE, make_under_loc, make_under_tables

pytestmark = pytest.mark.game


@pytest.fixture(scope="module")
def tables(schema, vanilla_db):
    return {t.name: t for t in make_under_tables(lambda name: vanilla_table(schema, vanilla_db, name))}


def rows(tables, name):
    t = tables[name]
    return [dict(zip([f for f, _ in t.fields], r)) for r in t.rows]


def test_bundle_sits_on_regions_and_shows_to_us(tables):
    (bundle,) = rows(tables, "effect_bundles_tables")
    assert bundle["key"] == UNDER_BUNDLE and bundle["bundle_target"] == "region"
    assert bundle["owner_only"] is False  # the bonus sits on someone else's city; we must see it too


def test_more_spread_and_shorter_immunity_in_the_city(tables):
    effects = {r["effect_key"]: (r["effect_scope"], r["value"]) for r in rows(tables, "effect_bundles_to_effects_junctions_tables")}
    assert effects == {
        "wh2_main_effect_plague_infectivity_mod": ("region_to_region_own", 20.0),
        "wh3_dlc25_effect_plague_immunity_mod_good": ("region_to_region_own", -1.0),
    }


def test_loc_both_languages():
    for lang in ("ru", "en"):
        loc = dict(make_under_loc(lang))
        assert loc["effect_bundles_localised_title_" + UNDER_BUNDLE]
        assert loc["effect_bundles_localised_description_" + UNDER_BUNDLE]
