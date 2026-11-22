# zen viz-core

The single source of truth for the ZENVIZ chart studio, shared by two products:

- **OMM-ZEN** — `D:/blog/web/public/omm-visualization.html` (one self-contained HTML)
- **CaiXiHui / 采析绘** — `F:/python_project/crawls/crawler_workflow/backend/static/`
  (`zenviz.html` + `css/zenviz.css` + `js/zenviz-page.js` + `js/zenviz-parse.js`)

Both products vendor this repository as a git submodule at `third_party/zenviz-core`.

## Layout

```
core/
  shell.html         HTML skeleton with {{HEAD_SCRIPTS}} {{VENDOR_SCRIPTS}}
                     {{FAVICON}} {{STYLES}} {{PARSE_SCRIPT}} {{SCRIPT}}
                     {{BRIDGE_SCRIPT}} placeholders
  zenviz.css         shared styles (OMM baseline + the CaiXiHui-only rules)
  zenviz.js          shared page app (one IIFE; TeX export, shortcuts and the
                     unified legend layout all live here)
  zenviz-parse.js    the RFC-4180 paste parser (single implementation)
profiles/
  omm/               head scripts, vendor bundles, favicon, VizBridge receiver,
                     transforms.json (OMM-only shared-UI migration overlay)
  caixihui/          head scripts, vendor bundles, favicon, iframe bridge tag
build.py             generator (deterministic, byte-stable output)
tools/bootstrap.py   ONE-TIME extraction from the original product files
tests/               determinism check
```

## Editing

Edit files under `core/` (or a `profiles/` overlay when the change is genuinely
product-specific). Never edit a generated artifact in a product repository.

```bash
python build.py --product omm       --root D:/blog/web
python build.py --product caixihui  --root F:/python_project/crawls/crawler_workflow
python tests/test_build.py          # determinism self-check
```

The generated artifacts are committed in the product repositories so each
product stays independently deployable. Both repositories have a guard test
that regenerates the artifacts and compares them byte-for-byte.

## Product-specific overlays

`build.py` keeps `core/` genuinely shared. Changes that apply to only one
product must live in that product's profile, not be hand-edited into a generated
artifact:

- `profiles/omm/transforms.json` — an ordered list of anchored `{old,new}`
  string replacements applied (in reverse order) to the final OMM HTML. It
  carries the OMM shared-UI migration: swapping in `zen/components/*.js` +
  `zen/zen.css`, routing dialogs/toasts through `ZenUI`, and removing the
  legacy private modal shells. `build.py` applies these only to the `single`
  layout, so the CaiXiHui (`split`) output is byte-for-byte unaffected.
- To change OMM's migrated page, edit this overlay (or `head.html`) and rebuild;
  never patch `public/omm-visualization.html` directly — the guard will reject it.

## Repository

Hosted at https://github.com/Xingye-Dujing/zenviz-core (public), and referenced
as a submodule at `third_party/zenviz-core` by both product repositories.
Pushing a commit here and advancing the submodule pointer in a product is the
way shared chart-studio changes reach both products.
