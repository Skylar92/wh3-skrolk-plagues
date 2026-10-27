"""Workshop previews: the assets' preview art scaled to the launcher's 512x512.

tools/build.py writes each next to its pack with the pack's name (dist/skrolk_plagues.png beside
dist/skrolk_plagues.pack): the launcher pairs a pack with its preview by name. Steam rejects previews
of 1 MB or more.
"""
from PIL import Image

from tools.paths import ROOT

SOURCES = {"main": ROOT / "assets" / "preview.png", "ru": ROOT / "assets" / "preview_ru_pack.png"}
SIZE = 512


def make_preview(which="main"):
    return Image.open(SOURCES[which]).convert("RGB").resize((SIZE, SIZE), Image.LANCZOS)


def save_preview(img, path):
    img.save(path, "PNG", optimize=True)
