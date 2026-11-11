"""Shared helpers for per-exam printed-content patches. Every change is logged (old value kept)."""
import json, os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
class Audit:
    def __init__(s, ex, short, date='2026-11-05'):
        s.ex, s.short, s.date = ex, short, date; s.f = os.path.join(root, 'data/questions', ex + '.json'); s.d = json.load(open(s.f, encoding='utf-8')); s.rows = []; s.Q = {}; s.G = {}
        for p in s.d['parts']:
            for sec in p['sections']:
                for g in sec.get('groups', []):
                    for q in g['questions']: k = '%s-%s' % (sec['section_no'], q['number']); s.Q[k] = q; s.G[k] = g
                for q in sec.get('questions', []): s.Q['%s-%s' % (sec['section_no'], q['number'])] = q
    def log(s, q, field, old, new, why, ev): s.rows.append((s.date, s.ex, q, field, old, new, why, ev))
    def sub(s, k, field, a, b, why, ev):
        q = s.Q[k]; old = q[field]; assert a in old, (k, field, a, old); q[field] = old.replace(a, b, 1); s.log(k, field, old, q[field], why, ev)
    def gsub(s, k, field, a, b, why, ev):
        g = s.G[k]; old = g['stimulus']['passage'] if field == 'passage' else g[field]; assert a in old, (k, field, a)
        new = old.replace(a, b, 1)
        if field == 'passage': g['stimulus']['passage'] = new
        else: g[field] = new
        s.log(k + ' (group)', field, old, new, why, ev)
    def opt(s, k, lab): return next(o for o in s.Q[k]['options'] if o['label'] == lab)
    def osub(s, k, lab, a, b, why, ev):
        o = s.opt(k, lab); old = o['text']; assert a in old, (k, lab, old); o['text'] = old.replace(a, b, 1); s.log(k, 'option ' + lab, old, o['text'], why, ev)
    def oadd(s, k, lab, text, after, why, ev):
        q = s.Q[k]; i = [o['label'] for o in q['options']].index(after) + 1; q['options'].insert(i, {'label': lab, 'text': text}); s.log(k, 'option ' + lab, '(absent)', text, why, ev)
    def defect(s, k, text, ev):
        s.Q[k]['source_defect'] = text; s.log(k, 'source_defect', '(absent)', text, 'New flag', ev)
    def finish(s, unresolved, status):
        old = s.d['unresolved']; s.d['unresolved'] = unresolved
        s.log('(exam)', 'unresolved', ' ¶ '.join(old), '(replaced by printed-content notes)', 'Stale answer notes are out of scope', '-')
        json.dump(s.d, open(s.f, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        h = '## Modifications\n\n| Date | Exam | Question | Field | Old value | New value | Reason | Evidence |\n|---|---|---|---|---|---|---|---|\n'
        with open(os.path.join(root, 'docs/verification/%s.md' % s.short), 'w') as o, open(os.path.join(root, 'docs/verification/CHANGELOG.md'), 'a') as c:
            o.write(h)
            for r in s.rows:
                line = '| ' + ' | '.join(str(x).replace('\n', '<br>').replace('|', '\\|') for x in r) + ' |\n'; o.write(line); c.write(line)
        sp = os.path.join(root, 'docs/verification/STATUS.md'); t = open(sp).read().split('\n')
        t = [('| %s | %s | 2026-11-05 | %d changes; see %s.md |' % (s.ex, status, len(s.rows) - 1, s.short)) if l.startswith('| %s |' % s.ex) else l for l in t]
        open(sp, 'w').write('\n'.join(t)); print(len(s.rows), 'logged')
