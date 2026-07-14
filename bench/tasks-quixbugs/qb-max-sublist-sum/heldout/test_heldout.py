"""QuixBugs max_sublist_sum test (held-out full contract)."""
import json
import signal
import sys

sys.setrecursionlimit(10000)
from max_sublist_sum import max_sublist_sum

CASES = json.loads(r"""[[[[4, -5, 2, 1, -1, 3]], 5], [[[0, -1, 2, -1, 3, -1, 0]], 4], [[[3, 4, 5]], 12], [[[4, -2, -8, 5, -2, 7, 7, 2, -6, 5]], 19], [[[-4, -4, -5]], 0], [[[-2, 1, -3, 4, -1, 2, 1, -5, 4]], 6]]""")


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
    out = norm(max_sublist_sum(*args))
    assert out == case[1], f"max_sublist_sum({{args!r}}) -> {{out!r}}, expected {{case[1]!r}}"


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
