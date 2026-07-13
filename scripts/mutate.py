#!/usr/bin/env python3
"""Deterministic AST mutation of a Python source file.

Used by the Proof-Carrying Repair strength witness: a contract-test suite must
KILL mutants of the patched code (especially removal of `raise` statements that
back documented error contracts). If no mutant can break the tests, the tests
are too weak to be evidence.

Deterministic and stdlib-only: same input always yields the same ordered mutant
list, so runs are reproducible.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

CMP_FLIP = {
    ast.Lt: ast.GtE, ast.GtE: ast.Lt,
    ast.Gt: ast.LtE, ast.LtE: ast.Gt,
    ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
}
BOOL_FLIP = {ast.And: ast.Or, ast.Or: ast.And}


class _Mutator(ast.NodeTransformer):
    def __init__(self, target: int):
        self.target = target      # which mutation site to apply
        self.counter = 0
        self.applied = None       # description of the applied mutation

    def _hit(self, desc: str) -> bool:
        fire = self.counter == self.target
        self.counter += 1
        if fire:
            self.applied = desc
        return fire

    # remove a `raise` -> replace with `pass` (kills error contracts)
    def visit_Raise(self, node: ast.Raise):
        if self._hit(f"remove raise (line {getattr(node, 'lineno', '?')})"):
            return ast.copy_location(ast.Pass(), node)
        return node

    # flip a comparison operator
    def visit_Compare(self, node: ast.Compare):
        self.generic_visit(node)
        if len(node.ops) == 1 and type(node.ops[0]) in CMP_FLIP:
            if self._hit(f"flip {type(node.ops[0]).__name__} (line {getattr(node, 'lineno', '?')})"):
                node.ops = [CMP_FLIP[type(node.ops[0])]()]
        return node

    # nudge an integer constant by +1 (off-by-one / boundary)
    def visit_Constant(self, node: ast.Constant):
        if isinstance(node.value, int) and not isinstance(node.value, bool):
            if self._hit(f"int {node.value}->{node.value + 1} (line {getattr(node, 'lineno', '?')})"):
                return ast.copy_location(ast.Constant(value=node.value + 1), node)
        return node

    # and <-> or
    def visit_BoolOp(self, node: ast.BoolOp):
        self.generic_visit(node)
        if type(node.op) in BOOL_FLIP:
            if self._hit(f"flip {type(node.op).__name__} (line {getattr(node, 'lineno', '?')})"):
                node.op = BOOL_FLIP[type(node.op)]()
        return node


def _count_sites(source: str) -> int:
    m = _Mutator(-1)
    m.visit(ast.parse(source))
    return m.counter


def generate(source: str, limit: int = 20) -> List[Tuple[str, str]]:
    """Return up to `limit` (description, mutated_source) pairs, deterministic."""
    n = _count_sites(source)
    out: List[Tuple[str, str]] = []
    for i in range(min(n, limit)):
        m = _Mutator(i)
        tree = m.visit(ast.parse(source))
        ast.fix_missing_locations(tree)
        try:
            mutated = ast.unparse(tree)
        except Exception:
            continue
        if m.applied and mutated != source:
            out.append((m.applied, mutated))
    return out


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="List deterministic mutants of a Python file")
    p.add_argument("path", type=Path)
    p.add_argument("--limit", type=int, default=20)
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    muts = generate(args.path.read_text(encoding="utf-8"), args.limit)
    for i, (desc, _) in enumerate(muts):
        print(f"{i}: {desc}")
    print(f"{len(muts)} mutants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
