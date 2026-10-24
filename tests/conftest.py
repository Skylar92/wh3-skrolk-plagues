import pytest

from tools.dbtable import load_schema
from tools.packfile import read_pack
from tools.paths import GAME_DATA, SCHEMA


@pytest.fixture(scope="session")
def schema():
    return load_schema(SCHEMA)


@pytest.fixture(scope="session")
def vanilla_db():
    return read_pack(GAME_DATA / "db.pack")


def vanilla_table(schema, vanilla_db, name):
    from tools.dbtable import decode_table
    return decode_table(schema, name, vanilla_db[f"db/{name}/data__"])
