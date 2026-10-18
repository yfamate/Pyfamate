"""Regression checks for bugs found while debugging the 2026-10-17 merges (PR #1-#11).

AST-extracts the touched definitions from Pyfamate.py and runs them with stubs
(no engines, no GPU). Usage: python tests/test_merge_debug_20261018.py
"""
import ast, collections, dataclasses, enum, json, math, os, queue, re, sys, threading, time, types
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "Pyfamate.py"
_src = SRC.read_text(encoding="utf-8-sig")
tree = ast.parse(_src)
WANT = {"ShogiBoard", "_dead_end_piece", "_sprt_sennichite_verdict_core", "_clamp", "_clamp01",
        "_mate_move_accepted", "_u_harvest_mate", "_u_council_mate_ponder"}
g = {}
g.update(dataclasses=dataclasses, enum=enum, os=os, re=re, json=json, math=math, queue=queue, sys=sys,
         threading=threading, time=time, collections=collections,
         _flog=lambda *a, **k: None, _dlog=lambda *a, **k: None, _ZOBRIST_VERIFY=False)
_seg = ast.get_source_segment
nodes = []
for n in tree.body:
    if isinstance(n, (ast.Import, ast.Assign, ast.For, ast.AnnAssign)) and (
            "_zb" in (_seg(_src, n) or "") or "_ZB_" in (_seg(_src, n) or "")):
        nodes.append(n)   # Zobrist tables used by ShogiBoard
    elif getattr(n, "name", None) in WANT:
        nodes.append(n)
    elif isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id.startswith("_RE_") for t in n.targets):
        nodes.append(n)
code = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)]
                  + nodes, type_ignores=[])
exec(compile(ast.fix_missing_locations(code), str(SRC), "exec"), g)
missing = WANT - set(g)
assert not missing, missing
R = {}


def check(name, cond, detail=None):
    R[name] = bool(cond)
    print(("PASS " if cond else "FAIL ") + name + ("" if detail is None else "  %r" % (detail,)))


SB = g["ShogiBoard"]

# 1. [#11] mate-solver first move that completes 連続王手の千日手 is refused again.
#    Zyfamate#2 only sees history from USI `position ... moves`; Pyfamate calls `solve <bare SFEN>`.
cyc = "2i1i 1a2a 1i2i 2a1a " * 3
bp = SB(sfen="sfen 8k/9/9/9/9/9/9/9/4K2R1 b - 1 moves " + cyc.strip())
check("fixture_perpetual", bp.is_perpetual_check_move("2i1i") is True)
ctx = types.SimpleNamespace(cfg=types.SimpleNamespace(mate_solver_join_timeout_s=0.1), current_position="p")
g["_get_tracking_board"] = lambda c: bp
done = threading.Thread(target=lambda: None); done.start(); done.join()


def _st(mv):
    return types.SimpleNamespace(ctx=ctx, mate_thread=done, ledger=None, eff_s=0.0,
                                 mate_state=types.SimpleNamespace(result="mate", best_move=mv))


check("harvest_mate_refuses_perpetual_first_move", g["_u_harvest_mate"](_st("2i1i")) is None)
check("harvest_mate_keeps_other_mate_move", g["_u_harvest_mate"](_st("2i2h")) == "2i2h")
g["_mate_ponder_harvest"] = lambda c, p: ("mate", "2i1i")
stp = types.SimpleNamespace(ctx=ctx, verdict="5i4h", ponder_move="x")
g["_u_council_mate_ponder"](stp)
check("mpon_refuses_perpetual_first_move", stp.verdict == "5i4h", stp.verdict)
g["_mate_ponder_harvest"] = lambda c, p: ("mate", "2i2h")
g["_u_council_mate_ponder"](stp)
check("mpon_keeps_other_mate_move", stp.verdict == "2i2h" and stp.ponder_move is None, stp.verdict)

bad = [k for k, v in R.items() if not v]
print("%d/%d PASS" % (len(R) - len(bad), len(R)))
sys.exit(1 if bad else 0)
