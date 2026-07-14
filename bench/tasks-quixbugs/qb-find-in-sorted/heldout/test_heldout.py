"""QuixBugs find_in_sorted test (held-out full contract)."""
import json
import signal
import sys

sys.setrecursionlimit(10000)
from find_in_sorted import find_in_sorted

CASES = json.loads(r"""[[[[3, 4, 5, 5, 5, 5, 6], 5], 3], [[[1, 2, 3, 4, 6, 7, 8], 5], -1], [[[1, 2, 3, 4, 6, 7, 8], 4], 3], [[[2, 4, 6, 8, 10, 12, 14, 16, 18, 20], 18], 8], [[[3, 5, 6, 7, 8, 9, 12, 13, 14, 24, 26, 27], 0], -1], [[[3, 5, 6, 7, 8, 9, 12, 12, 14, 24, 26, 27], 12], 6], [[[24, 26, 28, 50, 59], 101], -1]]""")


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
    out = norm(find_in_sorted(*args))
    assert out == case[1], f"find_in_sorted({{args!r}}) -> {{out!r}}, expected {{case[1]!r}}"


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
