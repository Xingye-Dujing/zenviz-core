#!/usr/bin/env python3
"""One-time extraction of the shared ZENVIZ core from the two product files.

Run once (from anywhere):
    python tools/bootstrap.py

Inputs (read-only):
    D:/blog/web/public/omm-visualization.html
    F:/python_project/crawls/crawler_workflow/backend/static/js/zenviz-parse.js

Outputs (overwritten):
    core/shell.html        HTML skeleton with {{PLACEHOLDERS}}
    core/zenviz.css        shared styles
    core/zenviz.js         shared page app (IIFE)
    profiles/omm/*         OMM product overlay
    profiles/caixihui/*    CaiXiHui product overlay

The extracted code is intentionally kept in OMM's original style (single quotes,
no trailing semicolons) so the generated OMM single file stays byte-stable.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OMM_HTML = pathlib.Path("D:/blog/web/public/omm-visualization.html")
CJH_PARSE = pathlib.Path(
    "F:/python_project/crawls/crawler_workflow/backend/static/js/zenviz-parse.js"
)


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text.replace("\r\n", "\n"))
    print(f"wrote {path.relative_to(ROOT)}  ({len(text)} chars)")


def find_block(text: str, start_marker: str, end_marker: str, label: str) -> tuple[int, int]:
    a = text.find(start_marker)
    if a < 0:
        raise SystemExit(f"[{label}] start marker not found: {start_marker!r}")
    b = text.find(end_marker, a)
    if b < 0:
        raise SystemExit(f"[{label}] end marker not found: {end_marker!r}")
    return a, b


def convert_py_legend_block(py_js: str) -> str:
    """Port CaiXiHui's legend layout into OMM's source style.

    The CaiXiHui implementation replaces OMM's balanceLegendLayout family: it
    resets stale grids before measuring, uses CSS custom properties for the
    padding, and realigns to flex-start when the balanced grid still overflows.
    """
    a = py_js.index("        const LEGEND_GAP_X = 7;")
    b = py_js.index("        /* The frame is re-fitted on resize", a)
    block = py_js[a:b].rstrip() + "\n"

    # Python side was reformatted with Prettier (double quotes, semicolons).
    # Convert mechanically to the OMM style used throughout the core file.
    out = []
    for line in block.splitlines():
        line = line.replace('"', "'")
        if line.rstrip().endswith(";"):
            line = line.rstrip()[:-1]
        out.append(line)
    block = "\n".join(out)

    # Callers in OMM use rebalanceOverlayLegend(); keep that entry point so the
    # two call sites (fitChartFrame / fitPreviewFrame) need no changes.
    block += """
        function rebalanceOverlayLegend() {
          const legend = document.querySelector('#chart-overlay .layout-legend')
          if (!legend || legend.classList.contains('stream')) return
          try {
            fitLegendLayout(legend, legend.parentElement)
          } catch (e) {}
        }
"""
    return block


def main() -> None:
    html = read(OMM_HTML)
    py_js = read(CJH_PARSE.parent / "zenviz-page.js")
    parse_js = read(CJH_PARSE)

    # ---------------------------------------------------------------- CSS ----
    css = re.search(r"<style>(.*?)</style>", html, re.S).group(1)
    css = css.strip("\n") + "\n"

    # CaiXiHui had fixed the top bar: an overflowing centred flex row cannot be
    # scrolled to, and its scrollbar must stay visible. Port that fix in place.
    ma = css.index("#top-menu {")
    mb = css.index("#menu-trigger:hover", ma)
    bar = css[ma:mb]
    bar = bar.replace("justify-content: center;", "justify-content: safe center;")
    bar = bar.replace("overflow: auto;", "overflow-x: auto;\n        overflow-y: hidden;")
    bar = bar.replace("scrollbar-width: none;", "scrollbar-width: thin;")
    bar = bar.replace(
        "#top-menu::-webkit-scrollbar {\n        display: none;\n      }",
        "#top-menu::-webkit-scrollbar {\n        height: 6px;\n      }\n"
        "      #top-menu::-webkit-scrollbar-thumb {\n"
        "        background: var(--line);\n        border-radius: 3px;\n      }",
    )
    css = css[:ma] + bar + css[mb:]

    # Merge the four rules that only exist in the CaiXiHui stylesheet.
    extra_rules = """
/* ---- rules carried over from the CaiXiHui stylesheet (shared shell needs them) ---- */
#property-import-input {
  display: none;
}
.data-meta {
  display: flex;
  gap: 11px;
  color: var(--dim);
  font-size: 9px;
  letter-spacing: 1px;
  white-space: nowrap;
  flex-shrink: 0;
}
.data-meta b {
  color: var(--ink);
  font-weight: 500;
}
.legend-grid {
  display: grid;
  align-items: center;
  justify-items: start;
}
"""
    write(ROOT / "core/zenviz.css", css.rstrip() + "\n" + extra_rules)

    # ----------------------------------------------------------------- JS ----
    js = max(re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S), key=len)

    # 1) legend family -> unified implementation
    legend_a = js.index("        // 图例项较多时的自动换行/换列：")
    legend_b = js.index("        function renderOverlay() {", legend_a)
    js = js[:legend_a] + convert_py_legend_block(py_js) + "\n" + js[legend_b:]

    # 2) inline call site: balanceLegendLayout(legend, items, isVertical)
    #    -> fitLegendLayout(legend, host)
    old_call = """              balanceLegendLayout(
                legend,
                Array.from(legend.querySelectorAll('.layout-legend-item')),
                state.legendOrientation === 'vertical',
              )"""
    new_call = """              fitLegendLayout(legend, host)"""
    if old_call not in js:
        raise SystemExit("[js] renderOverlay legend call site not found")
    js = js.replace(old_call, new_call, 1)

    # 3) parser -> single RFC-4180 implementation supplied by zen viz-parse.js
    pa, pb = find_block(
        js, "        function parseTextData(raw) {", "\n        $('#import-btn')", "parseTextData"
    )
    new_parse = """        function parseTextData(raw) {
          if (!window.ZenvizParse || typeof window.ZenvizParse.textData !== 'function') {
            throw new Error('zenviz-parse.js 未加载：无法解析粘贴的数据')
          }
          return window.ZenvizParse.textData(raw)
        }
"""
    js = js[:pa] + new_parse + js[pb:]

    # 4) strip the OMM-only VizBridge receiver into the product overlay
    end_marker = "        if (document.readyState === 'loading')"
    vb_end = js.index(end_marker)
    comment_start = js.rfind("\n        /* ", 0, vb_end)
    if comment_start < 0 or vb_end - comment_start > 2000:
        raise SystemExit("[js] VizBridge receiver block not found")
    vb_start = comment_start + 1
    tail = js[vb_start:vb_end]
    js = js[:vb_start] + js[vb_end:]

    write(ROOT / "core/zenviz.js", js.strip("\n") + "\n")
    write(ROOT / "profiles/omm/tail.js", tail.strip("\n") + "\n")
    write(ROOT / "core/zenviz-parse.js", parse_js)

    # --------------------------------------------------------------- shell ----
    # head product scripts
    head_a = html.index('    <script src="omm-embed.js"></script>')
    head_b = html.index('    <meta name="viewport"', head_a)
    shell = html[:head_a] + "{{HEAD_SCRIPTS}}\n" + html[head_b:]

    # vendor bundles differ per product (different folders / pinned versions)
    vendor_a = shell.index('    <link rel="stylesheet" href="vendor/fonts/literata-full.css" />')
    vendor_b = shell.index("    <style>", vendor_a)
    vendor = shell[vendor_a:vendor_b]
    shell = shell[:vendor_a] + "    {{VENDOR_SCRIPTS}}\n" + shell[vendor_b:]

    shell = shell.replace(
        '<link rel="icon" href="/icon.ico" type="image/x-icon" />',
        '<link rel="icon" href="{{FAVICON}}" type="image/x-icon" />',
    )

    style_a = shell.index("    <style>")
    style_b = shell.index("    </style>", style_a) + len("    </style>")
    shell = shell[:style_a] + "    {{STYLES}}" + shell[style_b:]

    script_a = shell.index("    <script>\n      ;(function () {")
    script_b = shell.index("    </script>", script_a) + len("    </script>")
    shell = (
        shell[:script_a]
        + "    {{PARSE_SCRIPT}}\n    {{SCRIPT}}\n{{BRIDGE_SCRIPT}}"
        + shell[script_b:]
    )
    write(ROOT / "core/shell.html", shell)

    # ------------------------------------------------------------ profiles ----
    head = """    <script src="omm-embed.js"></script>
    <script src="omm-desktop.js"></script>
    <script src="omm-share.js"></script>
    <script type="module" src="zen-link.js"></script>
    <script type="module" src="viz-bridge.js"></script>
"""
    write(ROOT / "profiles/omm/head.html", head)
    write(ROOT / "profiles/omm/config.json", '{\n  "favicon": "/icon.ico",\n  "layout": "single"\n}\n')
    write(ROOT / "profiles/omm/bridge.html", "")
    write(ROOT / "profiles/omm/vendor.html", vendor)

    cjh_vendor = """    <link href="vendor/fonts/literata.css" rel="stylesheet" />
    <script src="vendor/zv/chart.umd.min.js"></script>
    <script src="vendor/zv/apexcharts.min.js"></script>
    <script src="vendor/echarts.min.js"></script>
    <script src="vendor/zv/xlsx.full.min.js"></script>
    <script src="vendor/zv/html2canvas.min.js"></script>
    <script src="vendor/zv/jspdf.umd.min.js"></script>
"""
    write(ROOT / "profiles/caixihui/vendor.html", cjh_vendor)
    write(ROOT / "profiles/caixihui/head.html", "")
    write(ROOT / "profiles/caixihui/tail.js", "")
    write(
        ROOT / "profiles/caixihui/bridge.html",
        '    <script src="js/zenviz-bridge.js"></script>\n',
    )
    write(
        ROOT / "profiles/caixihui/config.json",
        '{\n  "favicon": "icon.ico",\n  "layout": "split"\n}\n',
    )

    print("\nBootstrap complete. Next: python build.py --product omm|caixihui --root <repo>")


if __name__ == "__main__":
    sys.exit(main())
