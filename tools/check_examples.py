#!/usr/bin/env python3
"""Type-check every Haskell, TypeScript, and C++ code block in skills/**/*.md.

Each fenced block tagged ```haskell, ```typescript, or ```cpp is compiled on
its own, so every block must be self-contained (imports/includes included).
Put `<!-- check:skip -->` on the line before a block to exclude it (for
signature-only sketches or deliberately ill-typed code).

Toolchain (override with environment variables):
  GHC        ghc with QuickCheck, hedgehog, containers, mtl, free, polysemy,
             polysemy-plugin, effectful, lens, optics, aeson, text
  GHCFLAGS   extra ghc flags, e.g. -Werror=incomplete-patterns
  TS_DIR     directory with node_modules containing typescript, fast-check,
             effect, @types/node
  CXX        g++ >= 14 (C++23 <expected>)
  CXXFLAGS   extra flags, e.g. -I/path/to/rapidcheck/include

Usage: tools/check_examples.py [--lang haskell|typescript|cpp] [paths...]
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FENCE = re.compile(r"^```(haskell|typescript|cpp)\s*$")
SKIP = "<!-- check:skip -->"


@dataclass
class Block:
    lang: str
    source: Path
    line: int  # 1-based line of the opening fence
    code: str

    @property
    def where(self) -> str:
        return f"{self.source.relative_to(ROOT)}:{self.line}"


def extract(path: Path) -> list[Block]:
    blocks, lines = [], path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        m = FENCE.match(lines[i])
        if not m:
            i += 1
            continue
        start = i
        prev = next((l.strip() for l in reversed(lines[:start]) if l.strip()), "")
        i += 1
        body = []
        while i < len(lines) and lines[i].strip() != "```":
            body.append(lines[i])
            i += 1
        if prev != SKIP:
            blocks.append(Block(m.group(1), path, start + 1, "\n".join(body) + "\n"))
        i += 1
    return blocks


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def haskell_source(block: Block, module: str) -> str:
    if re.search(r"^module\s", block.code, re.M):
        return block.code
    lines = block.code.splitlines()
    k = 0  # keep leading pragmas / comments / blank lines above the header
    while k < len(lines) and (lines[k].startswith("{-#") or not lines[k].strip() or lines[k].startswith("--")):
        k += 1
    return "\n".join(lines[:k] + [f"module {module} where"] + lines[k:]) + "\n"


def check_haskell(blocks: list[Block], work: Path) -> list[tuple[Block, str]]:
    ghc = os.environ.get("GHC", "ghc")

    def one(ix_block):
        ix, b = ix_block
        d = work / f"hs{ix}"
        d.mkdir()
        module = f"Example{ix}"
        src = haskell_source(b, module)
        declared = re.search(r"^module\s+([\w.]+)", src, re.M).group(1)
        f = d / (declared.replace(".", "/") + ".hs")
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(src)
        extra = os.environ.get("GHCFLAGS", "").split()
        code, out = run([ghc, "-fno-code", "-v0", *extra, "-i" + str(d), str(f)], cwd=d)
        return (b, out) if code else None

    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
        return [r for r in pool.map(one, enumerate(blocks)) if r]


def check_cpp(blocks: list[Block], work: Path) -> list[tuple[Block, str]]:
    cxx = os.environ.get("CXX", "g++")
    flags = os.environ.get("CXXFLAGS", "").split()

    def one(ix_block):
        ix, b = ix_block
        f = work / f"example{ix}.cpp"
        f.write_text(b.code)
        code, out = run([cxx, "-std=c++23", "-fsyntax-only", "-Wall", *flags, str(f)])
        return (b, out) if code else None

    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
        return [r for r in pool.map(one, enumerate(blocks)) if r]


def check_typescript(blocks: list[Block], work: Path) -> list[tuple[Block, str]]:
    ts_dir = Path(os.environ.get("TS_DIR", ROOT / "tools" / "ts"))
    tsc = ts_dir / "node_modules" / ".bin" / "tsc"
    d = Path(tempfile.mkdtemp(prefix="examples-", dir=ts_dir))
    try:
        files = {}
        for ix, b in enumerate(blocks):
            code = b.code
            if not re.search(r"^\s*(import|export)\s", code, re.M):
                code += "\nexport {};\n"
            name = f"example{ix}.ts"
            (d / name).write_text(code)
            files[name] = b
        cmd = [str(tsc), "--noEmit", "--strict", "--noUncheckedIndexedAccess",
               "--exactOptionalPropertyTypes", "--target", "es2022",
               "--module", "nodenext", "--moduleResolution", "nodenext",
               "--skipLibCheck", "--types", "node", *files]
        _, out = run(cmd, cwd=d)
        failures: dict[str, list[str]] = {}
        for line in out.splitlines():
            m = re.match(r"(example\d+\.ts)\((\d+),\d+\)", line)
            if m:
                failures.setdefault(m.group(1), []).append(line)
        return [(files[n], "\n".join(msgs)) for n, msgs in failures.items()]
    finally:
        shutil.rmtree(d, ignore_errors=True)


CHECKERS = {"haskell": check_haskell, "typescript": check_typescript, "cpp": check_cpp}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=sorted(CHECKERS))
    ap.add_argument("paths", nargs="*", type=Path)
    args = ap.parse_args()
    paths = [p.resolve() for p in args.paths] or sorted((ROOT / "skills").rglob("*.md"))
    mds = [p for q in paths for p in ([q] if q.is_file() else sorted(q.rglob("*.md")))]
    blocks = [b for p in mds for b in extract(p)]
    failed = 0
    with tempfile.TemporaryDirectory() as tmp:
        for lang, checker in CHECKERS.items():
            if args.lang and lang != args.lang:
                continue
            todo = [b for b in blocks if b.lang == lang]
            if not todo:
                continue
            work = Path(tmp) / lang
            work.mkdir()
            errors = checker(todo, work)
            failed += len(errors)
            print(f"{lang}: {len(todo) - len(errors)}/{len(todo)} blocks OK")
            for b, msg in sorted(errors, key=lambda e: e[0].where):
                print(f"  FAIL {b.where}\n" + "\n".join("    " + l for l in msg.splitlines()[:25]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
