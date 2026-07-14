"""QuixBugs get_factors test (held-out full contract)."""
import json
import signal
import sys

sys.setrecursionlimit(10000)
from get_factors import get_factors

CASES = json.loads(r"""[[[1], []], [[100], [2, 2, 5, 5]], [[101], [101]], [[104], [2, 2, 2, 13]], [[2], [2]], [[3], [3]], [[17], [17]], [[63], [3, 3, 7]], [[74], [2, 37]], [[73], [73]], [[9837], [3, 3, 1093]]]""")


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
    out = norm(get_factors(*args))
    assert out == case[1], f"get_factors({{args!r}}) -> {{out!r}}, expected {{case[1]!r}}"


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
