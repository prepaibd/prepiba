#!/usr/bin/env python3
"""Compare derived answers (data/sol) with stored answers (data/questions); print differences + coverage."""
import json, glob, os
tot = cov = diff = 0
rows = []
for f in sorted(glob.glob('data/questions/*.json')):
    ex = os.path.basename(f)[:-5]
    d = json.load(open(f, encoding='utf-8'))
    sp = f'data/sol/{ex}.sol.json'
    sol = json.load(open(sp, encoding='utf-8'))['items'] if os.path.exists(sp) else {}
    for p in d['parts']:
        for s in p['sections']:
            for g in s['groups']:
                for q in g['questions']:
                    k = f"{s['section_no']}-{q['number']}"; tot += 1
                    if k in sol:
                        cov += 1
                        if 'answer' in sol[k] and str(sol[k]['answer']).strip() != str(q.get('answer')).strip():
                            diff += 1; rows.append((ex, k, q.get('answer'), sol[k]['answer']))
print(f"coverage {cov}/{tot}; answer differences {diff}")
for r in rows: print(r)
