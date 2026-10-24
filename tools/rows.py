"""Small helpers for building new db rows next to vanilla ones."""
from tools.dbtable import Table


def empty_like(table):
    return Table(table.name, table.version, table.guid, list(table.fields), [], table.versioned)


def row(table, template=None, **values):
    """A row for `table`: `template`'s values (or all None) with the given columns set."""
    out = list(template) if template else [None] * len(table.fields)
    for col, value in values.items():
        out[table.col(col)] = value
    return out


def find(table, col, value):
    i = table.col(col)
    return next(r for r in table.rows if r[i] == value)


def table_with(table, *rows):
    out = empty_like(table)
    out.rows.extend(rows)
    return out
