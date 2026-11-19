#!/usr/bin/env python3
"""Generate the ZENVIZ chart studio for either product from the shared core.

    python build.py --product omm       --root D:/blog/web
    python build.py --product caixihui  --root F:/python_project/crawls/crawler_workflow

Both outputs are deterministic (UTF-8, LF, no timestamps) so a guard test can
regenerate into a temp directory and compare byte-for-byte with the committed
artifacts. Product-specific code lives only in profiles/<product>/.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

CORE = pathlib.Path(__file__).resolve().parent
SHELL = (
    "{{HEAD_SCRIPTS}}|{{VENDOR_SCRIPTS}}|{{FAVICON}}|{{STYLES}}|"
    "{{PARSE_SCRIPT}}|{{SCRIPT}}|{{BRIDGE_SCRIPT}}"
)


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text.replace("\r\n", "\n"))
    print(f"  -> {path}  ({len(text)} chars)")


def load_profile(product: str) -> tuple[dict, str, str, str, str]:
    pdir = CORE / "profiles" / product
    if not pdir.is_dir():
        raise SystemExit(f"unknown product: {product}")
    cfg = json.loads(read(pdir / "config.json"))
    return (
        cfg,
        read(pdir / "head.html"),
        read(pdir / "vendor.html"),
        read(pdir / "tail.js"),
        read(pdir / "bridge.html"),
    )


def inject_tail(js: str, tail: str) -> str:
    """Put the product receiver inside the page IIFE, just before init()."""
    if not tail.strip():
        return js
    marker = "        if (document.readyState === 'loading')"
    if marker not in js:
        raise SystemExit("[build] init marker missing from core/zenviz.js")
    return js.replace(marker, tail.rstrip("\n") + "\n" + marker, 1)


def fill_shell(
    cfg: dict, head: str, vendor: str, styles: str, parse: str, script: str, bridge: str
) -> str:
    shell = read(CORE / "core/shell.html")
    for key, value in {
        "{{HEAD_SCRIPTS}}": head.rstrip("\n"),
        "{{VENDOR_SCRIPTS}}": vendor.strip(),
        "{{FAVICON}}": cfg["favicon"],
        "{{STYLES}}": styles,
        "{{PARSE_SCRIPT}}": parse,
        "{{SCRIPT}}": script,
        "{{BRIDGE_SCRIPT}}": bridge.rstrip("\n"),
    }.items():
        if key not in shell:
            raise SystemExit(f"[build] placeholder missing from shell: {key}")
        shell = shell.replace(key, value)
    for token in ("{{HEAD_SCRIPTS}}", "{{VENDOR_SCRIPTS}}", "{{FAVICON}}",
                  "{{STYLES}}", "{{PARSE_SCRIPT}}", "{{SCRIPT}}", "{{BRIDGE_SCRIPT}}"):
        if token in shell:
            raise SystemExit(f"[build] unresolved placeholder: {token}")
    return shell


def build(product: str, root: pathlib.Path) -> None:
    cfg, head, vendor, tail, bridge = load_profile(product)
    css = read(CORE / "core/zenviz.css").strip("\n")
    parse_js = read(CORE / "core/zenviz-parse.js").strip("\n")
    page_js = read(CORE / "core/zenviz.js").strip("\n")

    print(f"[build] product={product} layout={cfg['layout']} root={root}")

    if cfg["layout"] == "single":
        # OMM: one self-contained html. Keep the product scripts external (as
        # before) but inline the shared CSS + parser + page app.
        html = fill_shell(
            cfg,
            head,
            vendor,
            "<style>\n" + css + "\n    </style>",
            "<script>\n" + parse_js + "\n    </script>",
            "<script>\n" + inject_tail(page_js, tail) + "\n    </script>",
            bridge,
        )
        write(root / "public/omm-visualization.html", html)
        return

    if cfg["layout"] == "split":
        # CaiXiHui: keep the existing file layout (shell + css + js files).
        static = root / "backend/static"
        write(static / "css/zenviz.css", read(CORE / "core/zenviz.css"))
        write(static / "js/zenviz-parse.js", read(CORE / "core/zenviz-parse.js"))
        write(static / "js/zenviz-page.js", read(CORE / "core/zenviz.js"))
        html = fill_shell(
            cfg,
            head,
            vendor,
            '<link rel="stylesheet" href="css/zenviz.css" />',
            '<script src="js/zenviz-parse.js"></script>',
            '<script src="js/zenviz-page.js"></script>',
            bridge,
        )
        write(static / "zenviz.html", html)
        return

    raise SystemExit(f"[build] unknown layout: {cfg['layout']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--product", required=True, choices=["omm", "caixihui"])
    ap.add_argument("--root", required=True, type=pathlib.Path)
    args = ap.parse_args()
    build(args.product, args.root.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
