#!/usr/bin/env python3
"""Run the whole test suite with ONE command and a correct exit code.

Why this exists
---------------
The tests under ``tests/`` are pytest-style module-level functions, not
``unittest.TestCase`` subclasses, and the repo has no CI. Two consequences
bit us:

* ``python3 -m unittest discover`` finds ZERO of them. It prints
  "NO TESTS RAN" and exits 5 — a run that asserts nothing and is easy to
  misread as "clean".
* ``pytest`` is not vendored and is not guaranteed to be installed, so the
  documented ``pytest`` path is not always available.

The only reliable way to run the suite was to invoke each file by hand
(``python3 tests/test_salary_score.py`` ...), which makes it trivial to forget
a file and gain false confidence.

This runner discovers every ``tests/test_*.py``, imports it, and calls every
``test_*`` function it defines (the same functions pytest would collect). It
reports an exact per-file and total test COUNT — so a file that defines no
tests, or a suite that silently runs nothing, cannot masquerade as a pass —
and exits non-zero if any test fails, any file errors on import, or no tests
are found at all. That makes the suite usable as a merge gate.

Usage::

    python3 run_tests.py
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import traceback

ROOT = pathlib.Path(__file__).resolve().parent
TESTS_DIR = ROOT / "tests"


def _load(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(f"_suite_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # may raise — caught by caller
    return module


def main() -> int:
    # Make `from config import ...` / `from scorer import ...` resolve the same
    # way the test files expect, no matter what the caller's CWD is.
    sys.path.insert(0, str(ROOT))

    files = sorted(TESTS_DIR.glob("test_*.py"))
    if not files:
        print(f"ERROR: no test files found under {TESTS_DIR}", file=sys.stderr)
        return 1

    total = passed = 0
    failures: list[str] = []
    empty_files: list[str] = []

    for f in files:
        try:
            module = _load(f)
        except Exception:
            failures.append(f"{f.name} (import error)")
            print(f"ERROR {f.name}: failed to import")
            traceback.print_exc()
            continue

        fns = [v for k, v in sorted(vars(module).items())
               if k.startswith("test_") and callable(v)]
        if not fns:
            empty_files.append(f.name)
            print(f"WARN  {f.name}: defines no test_* functions")
            continue

        for fn in fns:
            total += 1
            try:
                fn()
                passed += 1
            except Exception:
                failures.append(f"{f.name}::{fn.__name__}")
                print(f"FAIL  {f.name}::{fn.__name__}")
                traceback.print_exc()

    print()
    print(f"{passed}/{total} tests passed across {len(files)} files")
    if empty_files:
        print("WARN: files with no tests: " + ", ".join(empty_files))
    if failures:
        print("FAILED: " + ", ".join(failures))
        return 1
    if total == 0:
        print("ERROR: discovered test files but ran zero tests", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
