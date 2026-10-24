"""Decode and encode Total War: WARHAMMER III db tables using the RPFM schema."""
import re
import struct
from dataclasses import dataclass

GUID_MARKER = b"\xfd\xfe\xfc\xff"
VERSION_MARKER = b"\xfc\xfd\xfe\xff"

_FIXED = {
    "Boolean": "<?", "I16": "<h", "I32": "<i", "I64": "<q",
    "F32": "<f", "F64": "<d", "ColourRGB": "<I",
}


@dataclass
class Table:
    name: str
    version: int
    guid: str | None
    fields: list[tuple[str, str]]
    rows: list[list]
    versioned: bool = True  # old tables have no version marker (version 0)

    def col(self, name):
        for i, (field, _) in enumerate(self.fields):
            if field == name:
                return i
        raise KeyError(name)


class Schema:
    def __init__(self, text):
        self._text = text
        self._cache = {}

    def fields(self, table, version):
        key = (table, version)
        if key not in self._cache:
            self._cache[key] = self._parse(table, version)
        return self._cache[key]

    def _parse(self, table, version):
        return re.findall(r'name: "([^"]+)",\s*field_type: ([A-Za-z0-9_]+)', self._block(table, version))

    def references(self, table, version):
        """{column: (referenced table with _tables suffix, referenced column)} for one table version."""
        fields = re.split(r"\n\s*\(\n\s*name: ", self._block(table, version))[1:]
        out = {}
        for f in fields:
            ref = re.search(r'is_reference: Some\(\("([^"]+)", "([^"]+)"\)\)', f)
            if ref:
                out[f.split('"')[1]] = (ref.group(1) + "_tables", ref.group(2))
        return out

    def _block(self, table, version):
        start = self._text.find('"%s": [' % table)
        if start < 0:
            raise KeyError("table not in schema: " + table)
        block = self._text[start:self._text.find("\n        ],", start)]
        for vblock in re.split(r"\n            \(\n                version: ", block)[1:]:
            if int(vblock.split(",")[0]) == version:
                return vblock.split("localised_fields:")[0]
        raise KeyError("version %d of %s not in schema" % (version, table))


def reference_columns(schema, table):
    return schema.references(table.name, table.version)


def load_schema(path):
    return Schema(open(path, encoding="utf-8").read())


def _read_str(data, pos, wide):
    n = struct.unpack_from("<H", data, pos)[0]
    pos += 2
    size = n * 2 if wide else n
    raw = data[pos:pos + size]
    return raw.decode("utf-16-le" if wide else "utf-8"), pos + size


def _write_str(value, wide):
    raw = value.encode("utf-16-le" if wide else "utf-8")
    return struct.pack("<H", len(raw) // 2 if wide else len(raw)) + raw


def decode_table(schema, name, data):
    pos, guid, version, versioned = 0, None, 0, False
    if data[:4] == GUID_MARKER:
        guid, pos = _read_str(data, 4, wide=True)
    if data[pos:pos + 4] == VERSION_MARKER:
        version = struct.unpack_from("<i", data, pos + 4)[0]
        versioned = True
        pos += 8
    pos += 1  # always 0x01
    count = struct.unpack_from("<I", data, pos)[0]
    pos += 4
    fields = schema.fields(name, version)
    rows = []
    for _ in range(count):
        row = []
        for _, ftype in fields:
            if ftype in _FIXED:
                fmt = _FIXED[ftype]
                row.append(struct.unpack_from(fmt, data, pos)[0])
                pos += struct.calcsize(fmt)
            elif ftype in ("StringU8", "StringU16"):
                value, pos = _read_str(data, pos, ftype.endswith("U16"))
                row.append(value)
            elif ftype in ("OptionalStringU8", "OptionalStringU16"):
                present = data[pos]
                pos += 1
                if present:
                    value, pos = _read_str(data, pos, ftype.endswith("U16"))
                    row.append(value)
                else:
                    row.append(None)
            else:
                raise ValueError("unsupported field type %s in %s" % (ftype, name))
        rows.append(row)
    if pos != len(data):
        raise ValueError("%s: decoded %d of %d bytes" % (name, pos, len(data)))
    return Table(name, version, guid, list(fields), rows, versioned)


def encode_table(schema, table):
    out = bytearray()
    if table.guid is not None:
        out += GUID_MARKER + _write_str(table.guid, wide=True)
    if table.versioned:
        out += VERSION_MARKER + struct.pack("<i", table.version)
    out += b"\x01"
    out += struct.pack("<I", len(table.rows))
    for row in table.rows:
        for (_, ftype), value in zip(table.fields, row):
            if ftype in _FIXED:
                out += struct.pack(_FIXED[ftype], value)
            elif ftype in ("StringU8", "StringU16"):
                out += _write_str(value, ftype.endswith("U16"))
            elif value is None:
                out += b"\x00"
            else:
                out += b"\x01" + _write_str(value, ftype.endswith("U16"))
    return bytes(out)
