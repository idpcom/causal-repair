"""QuixBugs is_valid_parenthesization test (held-out full contract)."""
import json
import signal
import sys

sys.setrecursionlimit(10000)
from is_valid_parenthesization import is_valid_parenthesization

CASES = json.loads(r"""[[["((()()))()"], true], [[")()("], false], [["(("], false]]""")


def norm(x):
    if isinstance(x, (map, filter, zip)) or str(type(x)) == "<class 'generator'>":
        x = list(x)
    if isinstance(x, tuple):
        x = list(x)
    if isinstance(x, list):
        return [norm(i) for i in x]
    return x


def run_case(case):
    args = case[0] if isinstance(case[0], list) else [case[0]]
    out = norm(is_valid_parenthesization(*args))
    assert out == case[1], f"is_valid_parenthesization({{args!r}}) -> {{out!r}}, expected {{case[1]!r}}"


if __name__ == "__main__":
    failed = 0
    for case in CASES:
        signal.alarm(8)
        try:
            run_case(case)
        except Exception as exc:  # noqa: BLE001
            print(f"HELDOUT FAIL: {{exc!r}}"[:300])
            failed = 1
            break
        finally:
            signal.alarm(0)
    if failed:
        sys.exit(1)
    print("HELDOUT OK")
