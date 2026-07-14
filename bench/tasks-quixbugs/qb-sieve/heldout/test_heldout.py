"""QuixBugs sieve test (held-out full contract)."""
import json
import signal
import sys

sys.setrecursionlimit(10000)
from sieve import sieve

CASES = json.loads(r"""[[[1], []], [[2], [2]], [[4], [2, 3]], [[7], [2, 3, 5, 7]], [[20], [2, 3, 5, 7, 11, 13, 17, 19]], [[50], [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]]]""")


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
    out = norm(sieve(*args))
    assert out == case[1], f"sieve({{args!r}}) -> {{out!r}}, expected {{case[1]!r}}"


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
