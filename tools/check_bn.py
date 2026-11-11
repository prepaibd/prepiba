#!/usr/bin/env python3
"""Check Bangla vs English: numbers and $...$ LaTeX must match; no Bangla digits; coverage.
Usage: python3 tools/check_bn.py data/bn/<exam>.bn.json"""
import json, re, sys, collections
def strip(s): return re.sub(r'^\s*\d+\s*[.)]\s+', '', s or '')
def nums(s): return collections.Counter(re.findall(r'\d+(?:\.\d+)?', s))
def latex(s): return collections.Counter(re.findall(r'\$[^$]*\$', s.replace('\\$', 'DOLLAR')))
def main(path):
    bn = json.load(open(path, encoding='utf-8')); bad = 0
    en = json.load(open(f"data/questions/{bn['exam']}.json", encoding='utf-8'))
    qs, gs, want = {}, {}, set()
    for p in en['parts']:
        for s in p['sections']:
            for g in s['groups']:
                gs[f"{s['section_no']}-{g['questions'][0]['number']}"] = g
                for q in g['questions']:
                    k = f"{s['section_no']}-{q['number']}"; qs[k] = q
                    if s['subject'] in ('mathematics', 'analytical'): want.add(k)
    def cmp(k, a, b, what):
        nonlocal bad
        if nums(a) != nums(b): print(f"{k} {what}: numbers differ EN={dict(nums(a))} BN={dict(nums(b))}"); bad += 1
        if latex(a) != latex(b): print(f"{k} {what}: LaTeX differs"); bad += 1
        if re.search('[০-৯]', b): print(f"{k} {what}: Bangla digits"); bad += 1
    for k, it in bn['items'].items():
        q = qs.get(k)
        if not q: print(f"{k}: no such question"); bad += 1; continue
        cmp(k, strip(q['stem']), it['stem_bn'], 'stem')
        for lab, t in (it.get('options_bn') or {}).items():
            o = next((o for o in q['options'] if o['label'] == lab), None)
            if not o: print(f"{k}: option {lab} missing"); bad += 1
            else: cmp(k, o['text'], t, 'opt' + lab)
    for k, g in (bn.get('groups') or {}).items():
        G = gs.get(k)
        if not G: print(f"group {k}: not found"); bad += 1; continue
        if g.get('passage_bn'): cmp('G' + k, G['stimulus'].get('passage') or '', g['passage_bn'], 'passage')
        if g.get('instruction_bn'): cmp('G' + k, G.get('instruction') or '', g['instruction_bn'], 'instr')
    miss = sorted(want - set(bn['items']))
    if miss: print("missing:", miss); bad += len(miss)
    for k, G in gs.items():
        if k.split('-')[0] and any(f"{k.split('-')[0]}-{q['number']}" in want for q in G['questions']):
            st = G['stimulus']
            if (st.get('passage') and not (bn.get('groups', {}).get(k, {}).get('passage_bn'))): print(f"group {k}: passage not translated"); bad += 1
    print(f"{len(bn['items'])} items, {bad} problems"); return bad
if __name__ == '__main__': sys.exit(1 if main(sys.argv[1]) else 0)
