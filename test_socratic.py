"""Socratic enhancement tests — run: python3 test_socratic.py"""
import sys, importlib.util

spec = importlib.util.spec_from_file_location("meboya", "/root/.hermes/plugins/meboya/__init__.py")
mb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mb)  # may warn on mnemosyne import; ok

fails = []
def check(name, cond, detail=""):
    tag = "PASS" if cond else "FAIL"
    print(f"  [{tag}] {name}" + (f"  {detail}" if detail and not cond else ""))
    if not cond: fails.append(name)

print("=== fixture: build high-risk ===")
inj = mb._socratic_injection("bangun REST API auth dengan JWT")
check("trigger fires", inj is not None)
doms = inj.split("Domain files loaded:")[1].split("\n\n")[0] if inj else ""
for d in ["00-requirements", "07-testing", "04-api", "05-security"]:
    check(f"includes {d}", f"- {d}" in doms, doms)
check("no raw question leak marker", "--MEBOYA/SOCRATIC" in (inj or ""))
tok = len(inj or "") / 4  # rough chars→tokens
print(f"  [INFO] injection chars={len(inj or '')} (~{tok:.0f} tok est)")

print("=== fixture: non-build chat ===")
check("chat: no injection", mb._socratic_injection("cuaca gimana hari ini") is None)
check("short msg: no injection", mb._socratic_injection("ok") is None)

print("=== fixture: simple build (no domain words) ===")
inj2 = mb._socratic_injection("buatkan script python backup sederhana")
check("fires on trigger", inj2 is not None)
doms2 = inj2.split("Domain files loaded:")[1].split("\n\n")[0] if inj2 else ""
check("only base domains", doms2.count("- ") == 2 and "- 00-requirements" in doms2 and "- 07-testing" in doms2, doms2)

print("=== fixture: infra migration ===")
inj3 = mb._socratic_injection("migrasi route istio ke HTTPRoute internal, cek rollback dan monitor")
check("fires", inj3 is not None)
doms3 = inj3.split("Domain files loaded:")[1].split("\n\n")[0] if inj3 else ""
check("includes 06-infra", "- 06-infra" in doms3, doms3)
check("includes 08-observability", "- 08-observability" in doms3, doms3)

print("=== fixture: missing file robustness ===")
import os
saved = mb.SOCRATIC_DIR
mb.SOCRATIC_DIR = "/nonexistent"
check("missing dir -> None", mb._socratic_injection("build sesuatu") is None)
mb.SOCRATIC_DIR = saved

print()
if fails:
    print(f"FAILED: {fails}"); sys.exit(1)
print("ALL PASS")
