import pytest

from tools.dbtable import decode_table, encode_table

TABLES = [
    "culture_settlement_occupation_options_tables",
    "campaign_group_member_criteria_culture_settlement_occupation_options_tables",
    "effect_bundles_tables",
    "effect_bundles_to_effects_junctions_tables",
    "cultures_tables",
    "effects_tables",  # no version marker
    "effect_bonus_value_basic_junction_tables",  # no version marker
]


@pytest.mark.game
@pytest.mark.parametrize("name", TABLES)
def test_roundtrip_identical(name, schema, vanilla_db):
    raw = vanilla_db[f"db/{name}/data__"]
    assert encode_table(schema, decode_table(schema, name, raw)) == raw


@pytest.mark.game
def test_occupation_options_shape(schema, vanilla_db):
    t = decode_table(schema, "culture_settlement_occupation_options_tables",
                     vanilla_db["db/culture_settlement_occupation_options_tables/data__"])
    assert t.version == 7 and len(t.rows) == 444
    assert t.fields[t.col("id")][1] == "I64"
