"""QuixBugs powerset test (held-out full contract)."""
import json
import signal
import sys

sys.setrecursionlimit(10000)
from powerset import powerset

CASES = json.loads(r"""[[[["a", "b", "c"]], [[], ["c"], ["b"], ["b", "c"], ["a"], ["a", "c"], ["a", "b"], ["a", "b", "c"]]], [[["a", "b"]], [[], ["b"], ["a"], ["a", "b"]]], [[["a"]], [[], ["a"]]], [[[]], [[]]], [[["x", "df", "z", "m"]], [[], ["m"], ["z"], ["z", "m"], ["df"], ["df", "m"], ["df", "z"], ["df", "z", "m"], ["x"], ["x", "m"], ["x", "z"], ["x", "z", "m"], ["x", "df"], ["x", "df", "m"], ["x", "df", "z"], ["x", "df", "z", "m"]]]]""")


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
    out = norm(powerset(*args))
    assert out == case[1], f"powerset({{args!r}}) -> {{out!r}}, expected {{case[1]!r}}"


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
