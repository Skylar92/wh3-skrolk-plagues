"""Read and write Total War PFH5 pack files."""
import lzma
import struct
from compression import zstd

MAGIC = b"PFH5"
TYPE_MOD = 3
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
LZ4_MAGIC = b"\x04\x22\x4d\x18"


def _decompress(blob):
    size = struct.unpack_from("<I", blob, 0)[0]
    body = blob[4:]
    if body[:4] == ZSTD_MAGIC:
        return zstd.decompress(body)
    if body[:4] == LZ4_MAGIC:
        raise ValueError("lz4-compressed pack entries are not supported")
    # legacy lzma1: 5 props bytes then the raw stream; rebuild an "alone" header
    header = body[:5] + struct.pack("<Q", size)
    return lzma.decompress(header + body[5:], format=lzma.FORMAT_ALONE)


def read_pack(path):
    """Return {inner path with '/': decompressed bytes}."""
    data = open(path, "rb").read()
    if data[:4] != MAGIC:
        raise ValueError("not a PFH5 pack: %s" % path)
    _type, dep_count, _dep_size, count, _index_size = struct.unpack_from("<5I", data, 4)
    pos = 28
    for _ in range(dep_count):
        pos = data.index(b"\0", pos) + 1
    entries = []
    for _ in range(count):
        size = struct.unpack_from("<I", data, pos)[0]
        compressed = data[pos + 4]
        pos += 5
        end = data.index(b"\0", pos)
        entries.append((data[pos:end].decode("utf-8"), size, compressed))
        pos = end + 1
    files = {}
    for name, size, compressed in entries:
        blob = data[pos:pos + size]
        pos += size
        files[name.replace("\\", "/")] = _decompress(blob) if compressed else blob
    return files


def write_pack(path, files):
    """Write an uncompressed PFH5 mod pack from {inner path: bytes}."""
    names = sorted(files)
    index = b"".join(
        struct.pack("<IB", len(files[n]), 0) + n.replace("/", "\\").encode("utf-8") + b"\0"
        for n in names
    )
    header = MAGIC + struct.pack("<5II", TYPE_MOD, 0, 0, len(names), len(index), 0)
    with open(path, "wb") as f:
        f.write(header + index + b"".join(files[n] for n in names))
