from tools.ui_texts import LOC_PREFIX, UI_TEXTS, make_ui_loc


def test_every_text_in_english_and_russian():
    for name, texts in UI_TEXTS.items():
        assert set(texts) == {"en", "ru"} and all(texts.values()), name


def test_formats_keep_their_number():
    for name in ("skrolkpl_food", "skrolkpl_gold", "skrolkpl_layout"):
        for lang, text in UI_TEXTS[name].items():
            assert text.count("%d") == 1, (name, lang)


def test_loc_keys_are_the_ones_the_script_and_window_read():
    # the script reads campaign_localised_strings_string_<name>; the window's Loc("<name>") the same key
    for lang in ("en", "ru"):
        loc = dict(make_ui_loc(lang))
        assert set(loc) == {LOC_PREFIX + name for name in UI_TEXTS}
        assert all(key.startswith("campaign_localised_strings_string_skrolkpl_") for key in loc)
