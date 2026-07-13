"""Hidden contract test (never shown to the model)."""
import sys

import kvstore
import search


def check():
    kvstore.set_item("apple", 1)
    kvstore.set_item("apricot", 2)
    assert search.find("ap") == ["apple", "apricot"]
    kvstore.set_item("avocado", 3)
    assert search.find("a") == ["apple", "apricot", "avocado"]
    kvstore.delete_item("apple")
    assert search.find("a") == ["apricot", "avocado"], "deleted keys must vanish from search"
    try:
        kvstore.delete_item("nope")
    except KeyError:
        pass
    else:
        raise AssertionError('kvstore.delete_item("nope")' + ' must raise KeyError')


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:  # noqa: BLE001
        print(f"HELDOUT FAIL: {exc!r}")
        sys.exit(1)
    print("HELDOUT OK")
