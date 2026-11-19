#!/usr/bin/env python3
"""Determinism check: two consecutive builds of each product must be identical."""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
import unittest

CORE = pathlib.Path(__file__).resolve().parent.parent
BUILD = CORE / "build.py"


class BuildDeterminism(unittest.TestCase):
    def test_products_generate_identically_twice(self):
        for product in ("omm", "caixihui"):
            with self.subTest(product=product), tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
                for root in (a, b):
                    subprocess.run(
                        [sys.executable, str(BUILD), "--product", product, "--root", root],
                        check=True,
                        capture_output=True,
                        text=True,
                        cwd=CORE,
                    )
                pa = sorted(pathlib.Path(a).rglob("*"))
                pb = sorted(pathlib.Path(b).rglob("*"))
                self.assertEqual([p.relative_to(a) for p in pa],
                                 [p.relative_to(b) for p in pb])
                for x, y in zip(pa, pb):
                    if x.is_file():
                        self.assertEqual(x.read_bytes(), y.read_bytes(), x.relative_to(a))


if __name__ == "__main__":
    unittest.main(verbosity=2)
