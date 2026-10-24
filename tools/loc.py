"""Encode and decode Total War .loc localisation files."""
import struct

HEADER = b"\xff\xfeLOC\x00" + struct.pack("<I", 1)


def _read_str(data, pos):
    n = struct.unpack_from("<H", data, pos)[0]
    pos += 2
    return data[pos:pos + n * 2].decode("utf-16-le"), pos + n * 2


def _write_str(value):
    raw = value.encode("utf-16-le")
    return struct.pack("<H", len(raw) // 2) + raw


def decode_loc(data):
    if data[:10] != HEADER:
        raise ValueError("not a .loc file")
    count = struct.unpack_from("<I", data, 10)[0]
    pos, entries = 14, []
    for _ in range(count):
        key, pos = _read_str(data, pos)
        text, pos = _read_str(data, pos)
        pos += 1  # tooltip flag, always written as 0
        entries.append((key, text))
    return entries


def encode_loc(entries):
    out = bytearray(HEADER + struct.pack("<I", len(entries)))
    for key, text in entries:
        out += _write_str(key) + _write_str(text) + b"\x00"
    return bytes(out)
