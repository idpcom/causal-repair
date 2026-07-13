import pytest

from profile import get_display_name


def test_strips_normal_name():
    assert get_display_name("alice") == "Alice"


def test_legacy_null_name_uses_anonymous():
    assert get_display_name("legacy") == "Anonymous"


def test_missing_user_still_raises_key_error():
    with pytest.raises(KeyError):
        get_display_name("missing")
