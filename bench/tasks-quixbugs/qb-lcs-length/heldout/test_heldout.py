"""QuixBugs lcs_length test (held-out full contract)."""
import json
import signal
import sys

sys.setrecursionlimit(10000)
from lcs_length import lcs_length

CASES = json.loads(r"""[[["witch", "sandwich"], 2], [["meow", "homeowner"], 4], [["fun", ""], 0], [["fun", "function"], 3], [["cyborg", "cyber"], 3], [["physics", "physics"], 7], [["space age", "pace a"], 6], [["flippy", "floppy"], 3], [["acbdegcedbg", "begcfeubk"], 3]]""")


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
    out = norm(lcs_length(*args))
    assert out == case[1], f"lcs_length({{args!r}}) -> {{out!r}}, expected {{case[1]!r}}"


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
