"""[ZYF-OFF-CYF 2026-10-19] Pyfamate cuts its own Zyfamate / mate solver when nnue_1 carries a resident
Zyfamate (Cyfamate, USI options "Cyf_Zyf_*").

AST-extracts the helpers from Pyfamate.py and runs them with stubs (no engines).
Usage: python tests/test_zyf_off_cyf.py
"""
import ast, os, sys, tempfile, types
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "Pyfamate.py"
_src = SRC.read_text(encoding="utf-8-sig")
tree = ast.parse(_src)
WANT = {"_engine_has_resident_zyfamate", "_announces_resident_zyfamate", "_zyf_off_runtime"}
nodes = [n for n in tree.body
         if getattr(n, "name", None) in WANT
         or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_ZYF_RESIDENT_MARK"
                                               for t in n.targets))]
TMP = tempfile.mkdtemp(prefix="zyfoff_")
CALLS = {"serve_shutdown": 0}
g = dict(os=os, _BASE_DIR=TMP, _flog=lambda *a, **k: None, _zyf_off_with_cyfamate=False,
         _zf_serve_shutdown=lambda: CALLS.__setitem__("serve_shutdown", CALLS["serve_shutdown"] + 1))
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SRC), "exec"), g)
assert WANT <= set(g), WANT - set(g)

R = []
def ok(c, name):
    R.append(bool(c)); print(("PASS " if c else "FAIL ") + name)

def write(name, data):
    p = os.path.join(TMP, name)
    with open(p, "wb") as f:
        f.write(data)
    return p

has = g["_engine_has_resident_zyfamate"]
cyf = write("cyfamate.exe", b"MZ\0\0" + b"x" * 5000 + b"option name Cyf_Zyf_Defense type check" + b"y" * 100)
yo = write("YaneuraOu.exe", b"MZ\0\0" + b"option name Cyf_MP_PawnThreat" + b"z" * 5000)
bat = write("engine.bat", b"@echo off\r\nwsl ./cyfamate Cyf_Zyf_\r\n")
empty = write("empty.exe", b"")
ok(has(cyf) is True, "exe with Cyf_Zyf_ -> True")
ok(has(yo) is False, "exe without Cyf_Zyf_ (Cyf_ only) -> False")
ok(has("cyfamate.exe") is True, "relative path resolved against _BASE_DIR")
ok(has(bat) is None, ".bat wrapper -> None (runtime check decides)")
ok(has(empty) is None, "empty file -> None")
ok(has(os.path.join(TMP, "nope.exe")) is None, "missing -> None")
ok(has("") is None and has(None) is None, "empty path -> None")

ann = g["_announces_resident_zyfamate"]
ok(ann(types.SimpleNamespace(announced_options={"USI_Hash", "Cyf_Zyf_Cands"})) is True, "announce Cyf_Zyf_* -> True")
ok(ann(types.SimpleNamespace(announced_options={"USI_Hash", "Cyf_MP_PawnThreat"})) is False, "announce w/o Cyf_Zyf_ -> False")
ok(ann(types.SimpleNamespace()) is False and ann(None) is False, "no announced_options -> False")

class FakeEng:
    def __init__(self, alive):
        self._alive = alive; self.quits = 0
    def quit(self):
        self.quits += 1; self._alive = False

off = g["_zyf_off_runtime"]
ms = FakeEng(alive=True)
ctx = types.SimpleNamespace(mate_solver=ms, _zyfamate=True, _zyfamate_has_tsumero=True, _zyfamate_has_tesuki=True)
off(ctx)
ok(ctx.mate_solver is None and ctx._zyfamate is False, "runtime cut: ctx.mate_solver None, _zyfamate False")
ok(not ctx._zyfamate_has_tsumero and not ctx._zyfamate_has_tesuki, "runtime cut: tsumero / tesuki off")
ok(ms.quits == 1, "runtime cut: live solver quit once")
ok(CALLS["serve_shutdown"] == 1, "runtime cut: csa serve pool shut down")
ok(g["_zyf_off_with_cyfamate"] is True, "runtime cut: module flag set")
ms2 = FakeEng(alive=False)
ctx2 = types.SimpleNamespace(mate_solver=ms2, _zyfamate=False, _zyfamate_has_tsumero=False, _zyfamate_has_tesuki=False)
off(ctx2); off(ctx2)
ok(ms2.quits == 0 and ctx2.mate_solver is None, "runtime cut: not-started solver not quit; idempotent")

# wiring: the import-time gate sits in _mate_solver_enable, the runtime cut follows nnue_1 initialize,
# the makebook digger checks the engine.
ok("and not _zyf_off_with_cyfamate" in _src.split("_mate_solver_enable = (", 1)[1].split(")", 1)[0],
   "wiring: _mate_solver_enable gated by _zyf_off_with_cyfamate")
_i = _src.index('_init_usiok_retry("ctx.nnue_1", ctx.nnue_1, _nnue_1_opts)')
ok("_zyf_off_runtime(ctx)" in _src[_i:_i + 600], "wiring: runtime cut right after nnue_1 initialize")
ok(_src.count("_engine_has_resident_zyfamate(engine_path)") == 1, "wiring: makebook digger checks engine_path")
ok('"Zyfamate_Off_With_Cyfamate":     "true"' in _src, "default Zyfamate_Off_With_Cyfamate = true")

print(f"{sum(R)}/{len(R)} PASS")
sys.exit(0 if all(R) else 1)
