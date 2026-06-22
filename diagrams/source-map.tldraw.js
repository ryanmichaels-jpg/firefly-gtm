// Firefly TAM pipeline — source-map diagram for tldraw MCP exec.
// Paste/run via mcp__tldraw__exec once a tldraw canvas is open and connected.
// Style mirror: ALL-CAPS labels above outlined containers, field-row rectangles
// inside, violet arrows between actions. Mirrors the two reference screenshots.

const C = {
  arrow:        'violet',
  srcOutline:   'light-violet',
  pipeOutline:  'orange',
  martOutline:  'light-green',
  downOutline:  'light-red',
  guardOutline: 'red',
  rowFill:      'tint',
  rowColor:     'orange',
  txt:          'black',
};
const X = { src: 0, pipe: 420, mart: 920, down: 1380 };
const COL_W = 280, ROW_H = 26, ROW_PAD = 12;

[['src','SOURCES',X.src],
 ['pipe','PIPELINE  (CMS-first · 8 steps)',X.pipe],
 ['mart','MART',X.mart],
 ['down','DOWNSTREAM',X.down]
].forEach(([k,t,x]) => editor.createShape({
  _type:'text', shapeId:'h-'+k, x, y:0, text:t,
  color:C.txt, fontSize:26, maxWidth:380, anchor:'top-left'
}));

function container(key, x, y, label, rows, outline){
  editor.createShape({_type:'text', shapeId:'lbl-'+key, x, y:y-30,
    text:label, color:C.txt, fontSize:14, maxWidth:COL_W, anchor:'top-left'});
  const h = ROW_PAD + rows.length*(ROW_H+4) + ROW_PAD - 4;
  editor.createShape({_type:'rectangle', shapeId:'box-'+key,
    x, y, w:COL_W, h, text:'', color:outline, fill:'none'});
  rows.forEach((r,j) => editor.createShape({
    _type:'rectangle', shapeId:'row-'+key+'-'+j,
    x:x+12, y:y+ROW_PAD+j*(ROW_H+4), w:COL_W-24, h:ROW_H, text:r,
    color:C.rowColor, fill:C.rowFill, textAlign:'start'
  }));
  return 'box-'+key;
}

// SOURCES
const sources = [
  ['cms-hgi',  'CMS HGI',          ['Hospital list (15 states)','ccn, hospital_type, ownership','has_ED, mailing address']],
  ['ahrq',     'AHRQ COMPENDIUM',  ['parent_system + health_sys_id','facilities_in_system','98% CCN match']],
  ['pos',      'CMS POS  Q1 2026', ['CRTFD_BED_CNT (certified)','PSYCH_UNIT_BED_CNT','→ has_behavioral_unit']],
  ['nppes',    'NPPES',            ['DBA (other_names → name)','physical address + zip','edm_seed (auth_official)']],
  ['census',   'CENSUS GEOCODER',  ['lat, lng (TIGER, free)','batch ≤ 10k, no key','retry on 502; strip PO BOX']],
  ['mandates', 'MANDATES.CSV',     ['Status: Upcoming / In force','effective_date (parsed)','source_url']],
];
const SRC_TOP_Y = 60, SRC_GAP = 140;
const srcIds = {};
sources.forEach((s,i) => { srcIds[s[0]] = container('src-'+s[0], X.src, SRC_TOP_Y+i*SRC_GAP, s[1], s[2], C.srcOutline); });

// PIPELINE
const steps = [
  ['st1','STEP 1 · PULL CMS HGI',     ['→ clean hospital list','primary seed (NOT NPPES)']],
  ['st2','STEP 2 · DEDUP',            ['key: CCN + name+addr','do NOT key on NPI']],
  ['st3','STEP 3 · JOIN AHRQ',        ['add parent_system','facilities_in_system']],
  ['st4','STEP 4 · JOIN POS',         ['add certified beds','add has_behavioral_unit']],
  ['st5','STEP 5 · ENRICH NPPES',     ['prefer DBA over legal','edm_seed from auth_official']],
  ['st6','STEP 6 · GEOCODE',          ['Census batch geocoder','retry / address-clean']],
  ['st7','STEP 7 · MANDATE-JOIN',     ['status logic (In force/Upcoming)','NOT raw countdown']],
  ['st8','STEP 8 · TIER',             ['by beds + hospital_type','Critical Access → Tier 3']],
];
const PIPE_TOP_Y = 60, PIPE_GAP = 100;
const stepIds = {};
steps.forEach((s,i) => { stepIds[s[0]] = container(s[0], X.pipe, PIPE_TOP_Y+i*PIPE_GAP, s[1], s[2], C.pipeOutline); });

// MART
const martId = container('mart-tam', X.mart, 200, 'DATA/MART/TAM.CSV  (one row = facility)', [
  'identity: account_id, ccn, facility_name',
  'footprint: lat,lng · beds · has_ED · has_BH',
  'parent: parent_system · facilities_in_system',
  'mandate: status · effective_date · src_url',
  'edm: edm_seed name · title · phone',
  'meta: facility_tier · confidence · needs_review',
], C.martOutline);

// DOWNSTREAM
const forgeId = container('down-forge', X.down, 80, 'FORGE SCORE  (pre-call proxies)', [
  'Fit (gate)  · pass/fail',
  'Acute Need  · 0–3',
  'Event       · 0–3 (mandate clock)',
  'Gravity     · 0–3 (sponsor/budget)',
  'TOTAL · TIER · rationale',
  'Resolve/Clarity → confirm on call',
], C.downOutline);
const qsoId = container('down-qso', X.down, 380, '5 QSOs  (TIER C · paid enrichment)', [
  'Apify  + Prospeo/Apollo',
  'Street View recon (entrances)',
  'is_qso_candidate = TRUE',
  'one-off draft (NOT a sequence)',
], C.downOutline);
const dashId = container('down-dash', X.down, 600, 'DASHBOARD  (static, reads tam.json)', [
  'US map view (mandate states)',
  'Clay-style list view',
  'sortable / filterable by FORGE',
], C.downOutline);
container('guard', X.down, 820, 'GUARDRAILS  (never break)', [
  'Never fabricate · unknown = null + needs_review',
  'Never seed NPPES first',
  'Paid (Apify / contacts) only on 5 QSOs',
  'No email sequences — one-offs only',
], C.guardOutline);

// ARROWS
[['cms-hgi','st1'],['ahrq','st3'],['pos','st4'],['nppes','st5'],['census','st6'],['mandates','st7']]
  .forEach(([s,t]) => createArrowBetweenShapes(srcIds[s], stepIds[t], { color: C.arrow }));
for (let i=1; i<=7; i++) createArrowBetweenShapes(stepIds['st'+i], stepIds['st'+(i+1)], { color: 'black' });
createArrowBetweenShapes(stepIds['st8'], martId, { color: C.arrow, text: 'write' });
createArrowBetweenShapes(martId, forgeId, { color: C.arrow, text: 'score' });
createArrowBetweenShapes(forgeId, qsoId, { color: C.arrow, text: 'top-5' });
createArrowBetweenShapes(martId, dashId, { color: C.arrow, text: 'render' });

editor.selectAll();
editor.zoomToSelection();
return { ok: true };
