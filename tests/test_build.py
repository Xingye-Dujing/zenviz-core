#!/usr/bin/env python3
"""Determinism check: two consecutive builds of each product must be identical."""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
import unittest

CORE = pathlib.Path(__file__).resolve().parent.parent
BUILD = CORE / 'build.py'


class BuildDeterminism(unittest.TestCase):
    def test_products_generate_identically_twice(self):
        for product in ('omm', 'caixihui'):
            with self.subTest(product=product), tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
                for root in (a, b):
                    subprocess.run(
                        [sys.executable, str(BUILD), '--product', product, '--root', root],
                        check=True,
                        capture_output=True,
                        text=True,
                        cwd=CORE,
                    )
                pa = sorted(pathlib.Path(a).rglob('*'))
                pb = sorted(pathlib.Path(b).rglob('*'))
                self.assertEqual([p.relative_to(a) for p in pa], [p.relative_to(b) for p in pb])
                for x, y in zip(pa, pb):
                    if x.is_file():
                        self.assertEqual(x.read_bytes(), y.read_bytes(), x.relative_to(a))

    def test_generated_outputs_keep_the_shared_contract(self):
        """Both products get the same neutral CSS and page app; styling stays inline."""
        with tempfile.TemporaryDirectory() as root:
            subprocess.run(
                [sys.executable, str(BUILD), '--product', 'caixihui', '--root', root],
                check=True,
                capture_output=True,
                text=True,
                cwd=CORE,
            )
            static = pathlib.Path(root) / 'backend/static'
            css = (static / 'css/zenviz.css').read_text(encoding='utf-8')
            js = (static / 'js/zenviz-page.js').read_text(encoding='utf-8')
            html = (static / 'zenviz.html').read_text(encoding='utf-8')
            self.assertIn('.zen-select {', css)
            self.assertNotIn('var(--zen-', css)
            self.assertIn('function applyRadius()', js)
            self.assertIn("['radiusrow', '圆角']", js)
            for token in ('ZenUI', 'ZenUtil', 'data-zen-select', 'lib/data-viz'):
                self.assertNotIn(token, js)
            for token in ('data-omm-app', 'zen/components/', 'zen/zen.css'):
                self.assertNotIn(token, html)

        with tempfile.TemporaryDirectory() as root:
            subprocess.run(
                [sys.executable, str(BUILD), '--product', 'omm', '--root', root],
                check=True,
                capture_output=True,
                text=True,
                cwd=CORE,
            )
            html = (pathlib.Path(root) / 'public/omm-visualization.html').read_text(encoding='utf-8')
            self.assertIn('<style>', html)
            self.assertIn('function applyRadius()', html)
            self.assertNotIn('zen/zen.css', html)


if __name__ == '__main__':
    unittest.main(verbosity=2)
