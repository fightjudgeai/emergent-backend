import json, os, time
p = '.\\preserved_endpoints.json'
with open(p,'r',encoding='utf-8') as fh:
    data = json.load(fh)
tag_map = {}
for entry in data:
    f = entry.get('file')
    tags = entry.get('tags', [])
    try:
        mtime = os.path.getmtime(f)
    except Exception:
        mtime = 0
    for t in tags:
        cur = tag_map.get(t, {'files':set(), 'latest':0})
        cur['files'].add(f)
        if mtime > cur['latest']:
            cur['latest'] = mtime
        tag_map[t] = cur
out = []
for t,meta in tag_map.items():
    out.append({'tag':t,'count':len(meta['files']),'latest':meta['latest']})
out.sort(key=lambda x: x['latest'], reverse=True)
for i,e in enumerate(out, start=1):
    ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(e['latest'])) if e['latest'] else 'unknown'
    print(f"{i}. {e['tag']} — {e['count']} file(s) — latest: {ts}")
