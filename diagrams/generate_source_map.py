#!/usr/bin/env python3
"""Emit diagrams/source-map.svg — the Firefly TAM pipeline source map.

Style: hand-drawn aesthetic via SVG turbulence filter, all-caps labels above
outlined containers, peach-tinted field rows, violet arrows. Mirrors the
reference screenshots (color-coded containers, ALL-CAPS section labels).

Regenerate after edits:  python3 diagrams/generate_source_map.py
"""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass

# ---- layout constants ----
COL_W = 320
ROW_H = 28
ROW_GAP = 4
PAD = 14
LABEL_GAP = 8     # text-label above container
COL_GAP = 100     # gap between source/pipe/mart/down columns
COL_X = {'src': 40, 'pipe': 460, 'mart': 900, 'down': 1320}
CANVAS_W = COL_X['down'] + COL_W + 60
CANVAS_H = 1080

# ---- colors (Excalidraw-ish) ----
COLOR = {
    'src':   '#9B7BC9',   # lavender
    'pipe':  '#E08E45',   # orange
    'mart':  '#69A55C',   # green
    'down':  '#D96B7E',   # pink/coral
    'guard': '#C0392B',   # red
    'row_fill': '#FBEFE0',
    'row_stroke': '#5A3A1A',
    'arrow': '#A23DA8',   # magenta-violet
    'chain_arrow': '#1F1F1F',
    'text': '#1F1F1F',
}

@dataclass
class Container:
    key: str
    x: int
    y: int
    label: str
    rows: list[str]
    outline: str
    @property
    def h(self):
        return PAD + len(self.rows) * (ROW_H + ROW_GAP) - ROW_GAP + PAD
    @property
    def cx(self): return self.x + COL_W // 2
    @property
    def cy(self): return self.y + self.h // 2

# ---- data ----
SOURCES = [
    ('cms-hgi',  'CMS HGI',          ['Hospital list (15 states)', 'ccn · hospital_type · ownership', 'has_ED · mailing address']),
    ('ahrq',     'AHRQ COMPENDIUM',  ['parent_system · health_sys_id', 'facilities_in_system', '98% CCN match']),
    ('pos',      'CMS POS — Q1 2026',['CRTFD_BED_CNT (certified)', 'PSYCH_UNIT_BED_CNT', '→ has_behavioral_unit']),
    ('nppes',    'NPPES',            ['DBA (other_names → name)', 'physical address + zip', 'edm_seed (auth_official)']),
    ('census',   'CENSUS GEOCODER',  ['lat · lng (TIGER, free)', 'batch ≤ 10k · no key', 'retry on 502 · strip PO BOX']),
    ('mandates', 'MANDATES.CSV',     ['Status: Upcoming / In force', 'effective_date (parsed)', 'source_url']),
]
STEPS = [
    ('st1', 'STEP 1 · PULL CMS HGI',    ['→ clean hospital list', 'primary seed (NOT NPPES)']),
    ('st2', 'STEP 2 · DEDUP',           ['key: CCN + name+addr', 'do NOT key on NPI']),
    ('st3', 'STEP 3 · JOIN AHRQ',       ['add parent_system', 'add facilities_in_system']),
    ('st4', 'STEP 4 · JOIN POS',        ['add certified beds', 'add has_behavioral_unit']),
    ('st5', 'STEP 5 · ENRICH NPPES',    ['prefer DBA over legal', 'edm_seed from auth_official']),
    ('st6', 'STEP 6 · GEOCODE',         ['Census batch geocoder', 'retry · address-clean']),
    ('st7', 'STEP 7 · MANDATE-JOIN',    ['status logic (In force / Upcoming)', 'NOT raw countdown']),
    ('st8', 'STEP 8 · TIER',            ['by beds + hospital_type', 'Critical Access → Tier 3']),
]
SRC_TOP_Y, SRC_GAP = 90, 150
PIPE_TOP_Y, PIPE_GAP = 90, 115

src_boxes = {k: Container('src-' + k, COL_X['src'], SRC_TOP_Y + i * SRC_GAP, lbl, rows, COLOR['src'])
             for i, (k, lbl, rows) in enumerate(SOURCES)}
step_boxes = {k: Container(k, COL_X['pipe'], PIPE_TOP_Y + i * PIPE_GAP, lbl, rows, COLOR['pipe'])
              for i, (k, lbl, rows) in enumerate(STEPS)}

mart_box = Container('mart-tam', COL_X['mart'], 260, 'DATA/MART/TAM.CSV  (1 row = facility)', [
    'identity: account_id · ccn · facility_name',
    'footprint: lat,lng · beds · has_ED · has_BH',
    'parent: parent_system · facilities_in_system',
    'mandate: status · effective_date · src_url',
    'edm: edm_seed name · title · phone',
    'meta: facility_tier · confidence · needs_review',
], COLOR['mart'])

forge_box = Container('down-forge', COL_X['down'], 90, 'FORGE SCORE  (pre-call proxies)', [
    'Fit (gate)  · pass / fail',
    'Acute Need  · 0–3',
    'Event       · 0–3 (mandate clock)',
    'Gravity     · 0–3 (sponsor / budget)',
    'TOTAL · TIER · rationale',
    'Resolve / Clarity → confirm on call',
], COLOR['down'])

qso_box = Container('down-qso', COL_X['down'], 380, '5 QSOs  (TIER C · paid enrichment)', [
    'Apify + Prospeo / Apollo',
    'Street View recon (entrances)',
    'is_qso_candidate = TRUE',
    'one-off draft (NOT a sequence)',
], COLOR['down'])

dash_box = Container('down-dash', COL_X['down'], 600, 'DASHBOARD  (static, reads tam.json)', [
    'US map view (mandate states)',
    'Clay-style list view',
    'sortable / filterable by FORGE',
], COLOR['down'])

guard_box = Container('guard', COL_X['down'], 800, 'GUARDRAILS  (never break)', [
    'Never fabricate · unknown = null + needs_review',
    'Never seed NPPES first',
    'Paid (Apify / contacts) only on 5 QSOs',
    'No email sequences — one-offs only',
], COLOR['guard'])

ALL = [*src_boxes.values(), *step_boxes.values(), mart_box, forge_box, qso_box, dash_box, guard_box]

ARROWS_SRC_TO_STEP = [
    ('cms-hgi', 'st1'), ('ahrq', 'st3'), ('pos', 'st4'),
    ('nppes', 'st5'),   ('census', 'st6'), ('mandates', 'st7'),
]
PIPE_CHAIN = [f'st{i}' for i in range(1, 9)]

# ---- SVG emit ----
def esc(s: str) -> str:
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def container_svg(c: Container) -> str:
    out = []
    out.append(
        f'<text class="lbl" x="{c.x}" y="{c.y - LABEL_GAP}">{esc(c.label)}</text>'
    )
    out.append(
        f'<rect class="container" x="{c.x}" y="{c.y}" width="{COL_W}" height="{c.h}" '
        f'rx="6" ry="6" fill="none" stroke="{c.outline}" stroke-width="2.5"/>'
    )
    for j, r in enumerate(c.rows):
        rx = c.x + 12
        ry = c.y + PAD + j * (ROW_H + ROW_GAP)
        rw = COL_W - 24
        out.append(
            f'<rect class="row" x="{rx}" y="{ry}" width="{rw}" height="{ROW_H}" '
            f'rx="3" ry="3" fill="{COLOR["row_fill"]}" stroke="{COLOR["row_stroke"]}" stroke-width="1"/>'
        )
        out.append(
            f'<text class="row-text" x="{rx + 10}" y="{ry + ROW_H/2 + 5}">{esc(r)}</text>'
        )
    return '\n'.join(out)

def arrow_svg(x1, y1, x2, y2, color, label=None, dashed=False, bend=0.0):
    # cubic bezier curve from (x1,y1) to (x2,y2), bend controls vertical sag
    dx = x2 - x1
    dy = y2 - y1
    c1x = x1 + dx * 0.4
    c1y = y1 + dy * 0.05 + bend
    c2x = x1 + dx * 0.6
    c2y = y2 - dy * 0.05 + bend
    dash = ' stroke-dasharray="6 3"' if dashed else ''
    path = (f'<path d="M {x1} {y1} C {c1x} {c1y}, {c2x} {c2y}, {x2} {y2}" '
            f'fill="none" stroke="{color}" stroke-width="2" marker-end="url(#arrow-{color.lstrip("#")})"{dash}/>')
    out = [path]
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2 + bend - 6
        out.append(f'<text class="edge-label" x="{mx}" y="{my}" fill="{color}">{esc(label)}</text>')
    return '\n'.join(out)

# ---- compose ----
header_y = 38
HEADERS = [
    (COL_X['src'],  'SOURCES'),
    (COL_X['pipe'], 'PIPELINE  (CMS-first · 8 steps)'),
    (COL_X['mart'], 'MART'),
    (COL_X['down'], 'DOWNSTREAM'),
]

# arrow markers (one per color)
arrow_colors = {COLOR['arrow'], COLOR['chain_arrow']}
marker_defs = '\n'.join(
    f'<marker id="arrow-{c.lstrip("#")}" viewBox="0 0 10 10" refX="9" refY="5" '
    f'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
    f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{c}"/>'
    f'</marker>'
    for c in arrow_colors
)

# build the arrow set
arrow_pieces = []

# sources → pipeline steps (right edge of source → left edge of step)
for s_key, t_key in ARROWS_SRC_TO_STEP:
    s = src_boxes[s_key]
    t = step_boxes[t_key]
    arrow_pieces.append(arrow_svg(
        s.x + COL_W, s.cy, t.x, t.cy,
        COLOR['arrow'], bend=(t.cy - s.cy) * 0.25
    ))

# pipeline chain (bottom of step N → top of step N+1)
for a, b in zip(PIPE_CHAIN[:-1], PIPE_CHAIN[1:]):
    sa = step_boxes[a]
    sb = step_boxes[b]
    arrow_pieces.append(arrow_svg(
        sa.cx, sa.y + sa.h, sb.cx, sb.y,
        COLOR['chain_arrow']
    ))

# step8 → mart
s8 = step_boxes['st8']
arrow_pieces.append(arrow_svg(
    s8.x + COL_W, s8.cy, mart_box.x, mart_box.cy + 60,
    COLOR['arrow'], label='write'
))
# mart → forge
arrow_pieces.append(arrow_svg(
    mart_box.x + COL_W, mart_box.y + 30, forge_box.x, forge_box.cy,
    COLOR['arrow'], label='score'
))
# forge → qso
arrow_pieces.append(arrow_svg(
    forge_box.cx, forge_box.y + forge_box.h, qso_box.cx, qso_box.y,
    COLOR['arrow'], label='top-5'
))
# mart → dashboard
arrow_pieces.append(arrow_svg(
    mart_box.x + COL_W, mart_box.y + mart_box.h - 30, dash_box.x, dash_box.cy,
    COLOR['arrow'], label='render'
))

containers_svg = '\n'.join(container_svg(c) for c in ALL)
arrows_svg = '\n'.join(arrow_pieces)
headers_svg = '\n'.join(
    f'<text class="header" x="{x}" y="{header_y}">{esc(t)}</text>' for x, t in HEADERS
)

svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CANVAS_W} {CANVAS_H}"
     width="{CANVAS_W}" height="{CANVAS_H}" font-family="'Patrick Hand','Caveat','Comic Sans MS',cursive">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Patrick+Hand&amp;family=Caveat:wght@500&amp;display=swap');
      .header   {{ font-size: 22px; font-weight: 700; fill: {COLOR['text']}; letter-spacing: 1px; }}
      .lbl      {{ font-size: 13px; font-weight: 700; fill: {COLOR['text']}; letter-spacing: 0.5px; }}
      .row-text {{ font-size: 12px; fill: {COLOR['text']}; font-family: 'Patrick Hand','Comic Sans MS',cursive; }}
      .edge-label {{ font-size: 11px; font-weight: 700; }}
      .container {{ filter: url(#rough); }}
      .row       {{ filter: url(#rough); }}
    </style>
    <filter id="rough" x="-2%" y="-2%" width="104%" height="104%">
      <feTurbulence type="fractalNoise" baseFrequency="0.018" numOctaves="2" seed="3" result="noise"/>
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="1.8"/>
    </filter>
    {marker_defs}
  </defs>

  <rect width="100%" height="100%" fill="#FAF7F0"/>

  <!-- column headers -->
  {headers_svg}

  <!-- arrows underneath containers -->
  {arrows_svg}

  <!-- containers + rows on top -->
  {containers_svg}

  <!-- footer credit / generated tag -->
  <text x="40" y="{CANVAS_H - 18}" font-size="10" fill="#888"
        font-family="ui-monospace,Menlo,monospace">
    firefly-gtm · TAM pipeline source map · regenerate: python3 diagrams/generate_source_map.py
  </text>
</svg>
'''

out_path = Path(__file__).parent / 'source-map.svg'
out_path.write_text(svg, encoding='utf-8')
print(f'wrote {out_path}  ({out_path.stat().st_size} bytes)')
