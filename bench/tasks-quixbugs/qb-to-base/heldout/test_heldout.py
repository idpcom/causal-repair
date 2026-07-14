"""QuixBugs to_base test (held-out full contract)."""
import json
import signal
import sys

sys.setrecursionlimit(10000)
from to_base import to_base

CASES = json.loads(r"""[[[8227, 18], "1771"], [[73, 8], "111"], [[16, 19], "G"], [[31, 16], "1F"], [[41, 2], "101001"], [[44, 5], "134"], [[27, 23], "14"], [[56, 23], "2A"], [[8237, 24], "E75"], [[8237, 34], "749"]]""")


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
    out = norm(to_base(*args))
    assert out == case[1], f"to_base({{args!r}}) -> {{out!r}}, expected {{case[1]!r}}"


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
