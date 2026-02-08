import os, re, json,sys
root='.'
tag_map = {}
# regexes to find tags in APIRouter(...) or decorators with tags=
router_re = re.compile(r"APIRouter\s*\(.*?tags\s*=\s*\[([^\]]+)\]", re.S)
decorator_re = re.compile(r"@\w+\..*?\(.*?tags\s*=\s*\[([^\]]+)\]", re.S)
str_re = re.compile(r"['\"](.*?)['\"]")
for dirpath, dirnames, filenames in os.walk(root):
    # skip virtual env and __pycache__
    if '.venv' in dirpath.split(os.sep) or '__pycache__' in dirpath.split(os.sep):
        continue
    for fn in filenames:
        if not fn.endswith('.py'):
            continue
        path = os.path.join(dirpath, fn)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                txt = f.read()
        except Exception:
            continue
        tags = set()
        for m in router_re.finditer(txt):
            inner = m.group(1)
            for s in str_re.findall(inner):
                tags.add(s.strip())
        for m in decorator_re.finditer(txt):
            inner = m.group(1)
            for s in str_re.findall(inner):
                tags.add(s.strip())
        if tags:
            mtime = os.path.getmtime(path)
            for t in tags:
                entry = tag_map.setdefault(t, {'files':[], 'latest_mtime':0})
                entry['files'].append(path.replace('\\','/'))
                if mtime > entry['latest_mtime']:
                    entry['latest_mtime'] = mtime
# prepare output list sorted by latest_mtime desc
out = [{'tag':k, 'files':v['files'], 'latest_mtime':v['latest_mtime']} for k,v in tag_map.items()]
out.sort(key=lambda x: x['latest_mtime'], reverse=True)
print(json.dumps(out, indent=2))
