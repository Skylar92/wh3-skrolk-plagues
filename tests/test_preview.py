import pytest

from tools.build import PACK_NAME, TRANSLATION_PACKS, preview_name
from tools.preview import SOURCES, make_preview, save_preview


@pytest.mark.parametrize("which", sorted(SOURCES))
def test_preview_size_and_weight(tmp_path, which):
    out = tmp_path / "preview.png"
    save_preview(make_preview(which), out)
    assert make_preview(which).size == (512, 512)
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert out.stat().st_size < 1_000_000


def test_preview_is_deterministic():
    assert make_preview().tobytes() == make_preview().tobytes()


def test_preview_names_pair_with_the_packs():
    # the launcher pairs a pack with its preview by name
    assert preview_name(PACK_NAME) == "skrolk_plagues.png"
    assert preview_name(TRANSLATION_PACKS["ru"]) == "!skrolk_plagues_ru.png"
    assert set(SOURCES) == {"main"} | set(TRANSLATION_PACKS)
