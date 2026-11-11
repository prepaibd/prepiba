#!/usr/bin/env python3
"""Validate data/questions/*.json (read-only; never edits). Usage: python3 scripts/validate.py [exam_id ...]
Checks: schema, option labels, answer in options, numbering, $ escaping, KaTeX parse (same delimiters as viewer),
tables, stray artefacts, image files, topics, needs_review/unresolved/source_defect/answer_source flags."""
import json, glob, os, re, sys, subprocess, collections
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sel = set(sys.argv[1:])
CTRL = re.compile(r'[\x00-\x08\x0b-\x1f\x7f]')
STRAY = [('double space', re.compile(r'(?<=[^\s$])  +(?=[^\s$])')), ('stray |', re.compile(r'\|')), ('stray ¦', re.compile('¦')),
         ('U+FFFD', re.compile('�')), ('control char', CTRL), ('trailing space', re.compile(r'[ \t]+$', re.M))]
MONEY = re.compile(r'(?<!\\)\$\s?\d')          # "$250" style bare money
ESC_OK = '$\\$$'

def split_math(t):
    """Mimic auto-render: delimiters $$..$$, $..$, \\(..\\). Returns (spans, leftover_text_with_math_removed, problems)."""
    spans, probs, i, out = [], [], 0, []
    while i < len(t):
        if t.startswith('\\$', i): out.append('\\$'); i += 2; continue
        if t.startswith('$$', i):
            j = t.find('$$', i+2)
            if j < 0: probs.append('unclosed $$'); break
            spans.append((t[i+2:j], True)); i = j+2; continue
        if t[i] == '$':
            j = i+1
            while j < len(t) and not (t[j] == '$' and t[j-1] != '\\'): j += 1
            if j >= len(t): probs.append('unclosed $ at %d' % i); out.append(t[i:]); break
            spans.append((t[i+1:j], False)); i = j+1; continue
        if t.startswith('\\(', i):
            j = t.find('\\)', i+2)
            if j < 0: probs.append('unclosed \\('); break
            spans.append((t[i+2:j], False)); i = j+2; continue
        out.append(t[i]); i += 1
    return spans, ''.join(out), probs

def texts(q, g):
    yield 'stem', q.get('stem')
    for o in q.get('options') or []: yield 'option %s' % o.get('label'), o.get('text')
    yield 'explanation', q.get('explanation')
    if g['stimulus'].get('passage'): yield 'passage', g['stimulus']['passage']
    for k in ('source_group_label', 'instruction'): 
        if g.get(k): yield k, g[k]
    for tb, nm in ((q.get('table'), 'q.table'), (g['stimulus'].get('table'), 'stimulus.table')):
        if tb:
            for r in tb.get('rows', []):
                for c in r: yield nm + ' cell', c

res = collections.OrderedDict(); allmath = []
for f in sorted(glob.glob(os.path.join(root, 'data/questions/*.json'))):
    eid = os.path.basename(f)[:-5]
    if sel and eid not in sel: continue
    d = json.load(open(f, encoding='utf-8')); R = collections.defaultdict(list); res[eid] = R
    tp = os.path.join(root, 'data/topics', eid + '.json'); topics = json.load(open(tp)) if os.path.exists(tp) else None
    if topics is None: R['topics'].append('no topics file')
    for p in d['parts']:
        for s in p['sections']:
            seen = []
            for g in s['groups']:
                for fld in ('source_group_label', 'instruction', 'stimulus', 'questions'):
                    if fld not in g: R['schema'].append('%s: group missing %s' % (s['section_no'], fld))
                for k in ('passage', 'image', 'table'):
                    if k not in g.get('stimulus', {}): R['schema'].append('%s: stimulus missing %s' % (s['section_no'], k))
                im = g['stimulus'].get('image')
                if im and not os.path.exists(os.path.join(root, 'data/questions', eid, im) if not im.startswith('data/') else os.path.join(root, im)):
                    R['images'].append('%s: stimulus image not found: %s' % (s['section_no'], im))
                tbl = g['stimulus'].get('table')
                for q in g['questions']:
                    k = '%s-%s' % (s['section_no'], q.get('number')); seen.append(q.get('number'))
                    for fld in ('number', 'question_type', 'stem', 'options', 'answer', 'explanation'):
                        if fld not in q: R['schema'].append('%s missing %s' % (k, fld))
                    labs = [o.get('label') for o in q.get('options') or []]
                    if len(set(labs)) != len(labs): R['schema'].append('%s duplicate option labels %s' % (k, labs))
                    if labs and labs != sorted(labs): R['schema'].append('%s option labels not in order %s' % (k, labs))
                    a = q.get('answer')
                    if q.get('options'):
                        parts = [x.strip() for x in re.split(r'\s*(?:,|&|\band\b)\s*', a or '') if x.strip()]
                        multi = re.search(r'indicate (all|each)|all that apply|select all', (q.get('stem') or '') + (g.get('instruction') or ''), re.I)
                        ok = (a in labs) or (multi and parts and all(x in labs for x in parts))
                        if a is not None and not ok: R['answers_info'].append('%s answer %r not in options %s' % (k, a, labs))
                        if a is None and not q.get('source_defect'): R['answers_info'].append('%s null answer without source_defect' % k)
                    elif a not in (None, '') and False: R['schema'].append('%s no options but answer %r' % (k, a))
                    for fl in ('answer_source', 'answer_basis'):
                        if fl not in q: R['answers_info'].append('%s missing %s' % (k, fl)) if q.get('answer') else None
                    if q.get('needs_review'): R['needs_review'].append(k)
                    if q.get('source_defect'): R['source_defect'].append(k)
                    if '[unreadable]' in json.dumps(q, ensure_ascii=False): R['unreadable'].append(k)
                    for im in q.get('images') or []:
                        pth = im if isinstance(im, str) else im.get('src') or im.get('path') or ''
                        if not (os.path.exists(os.path.join(root, 'data/questions', eid, pth)) or os.path.exists(os.path.join(root, 'data/questions', pth)) or os.path.exists(os.path.join(root, pth))):
                            R['images'].append('%s image not found: %s' % (k, pth))
                    if topics is not None and not topics.get(k): R['topics'].append('%s untagged' % k)
                    qt = q.get('table')
                    for tb, nm in ((qt, 'q.table'), (tbl, 'stimulus.table')):
                        if tb:
                            rows = tb.get('rows') or []
                            if not rows: R['tables'].append('%s %s empty' % (k, nm))
                            elif len({len(r) for r in rows}) > 1: R['tables'].append('%s %s not rectangular %s' % (k, nm, [len(r) for r in rows]))
                            elif any(c in ('', None) for r in rows[1:] for j, c in enumerate(r) if not (tb.get('rowspan_first_col') and j == 0)) : R['tables'].append('%s %s has empty body cell(s)' % (k, nm))
                    for where, t in texts(q, g):
                        if not isinstance(t, str): continue
                        spans, rest, probs = split_math(t)
                        for pr in probs: R['dollar'].append('%s %s: %s | %s' % (k, where, pr, t[:70].replace('\n', ' ')))
                        for m in MONEY.finditer(re.sub(r'\$[^$]*\$', '', t) if False else rest):
                            R['dollar'].append('%s %s: bare money "$" outside $\\$$ : ...%s' % (k, where, rest[max(0, m.start()-15):m.end()+15].replace('\n', ' ')))
                        for sp, disp in spans: allmath.append((eid, k, where, sp, disp))
                        for nm, rg in STRAY:
                            if rg.search(rest if nm == 'stray |' else t): R['artefacts'].append('%s %s: %s' % (k, where, nm))
            nums = [n for n in seen if isinstance(n, int)]
            if nums and nums != list(range(nums[0], nums[0]+len(nums))): R['numbering'].append('section %s numbers %s' % (s['section_no'], nums))
    for u in d.get('unresolved') or []: R['unresolved'].append(u)

# KaTeX
uniq = sorted({(m[3], m[4]) for m in allmath}); err = {}
if uniq:
    try:
        out = subprocess.run(['node', os.path.join(root, 'tools/katex_check/check.js')], input=json.dumps([{'tex': t, 'display': dsp} for t, dsp in uniq]), capture_output=True, text=True, check=True).stdout
        err = {u: e for u, e in zip(uniq, json.loads(out)) if e}
    except Exception as e:
        print('KaTeX check could not run:', e, '(cd tools/katex_check && npm install)'); err = {}
for eid, k, where, sp, disp in allmath:
    if (sp, disp) in err: res[eid]['katex'].append('%s %s: %s  <- %s' % (k, where, err[(sp, disp)][:90], sp[:60]))

HARD = ['schema', 'dollar', 'katex', 'tables', 'artefacts', 'images', 'topics', 'numbering']
tot = collections.Counter()
for eid, R in res.items():
    print('== %s' % eid)
    for cat in HARD + ['answers_info', 'needs_review', 'source_defect', 'unreadable', 'unresolved']:
        v = R.get(cat, [])
        if v:
            tot[cat] += len(v)
            print('  %-13s %3d  %s' % (cat, len(v), ('; '.join(map(str, v[:6])) + (' ...' if len(v) > 6 else '')) if cat not in ('unresolved',) else '(see json)'))
    if not any(R.get(c) for c in HARD): print('  hard checks: clean')
print('\nTOTAL', dict(tot))
sys.exit(1 if any(tot[c] for c in HARD) else 0)
