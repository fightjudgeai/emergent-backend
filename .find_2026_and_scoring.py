import os, re, json, sys
from datetime import datetime
root='.'
scoring_matches = []
files_2026 = []
scoring_regex = re.compile(r"scoring[_-]?engine[_-]?v(\d+)", re.I)
for dirpath, dirnames, filenames in os.walk(root):
    # skip virtual env and __pycache__
    parts = dirpath.split(os.sep)
    if '.venv' in parts or '__pycache__' in parts:
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
        # mtime year
        try:
            mtime = os.path.getmtime(path)
            year = datetime.fromtimestamp(mtime).year
            if year == 2026:
                files_2026.append(path.replace('\\','/'))
        except Exception:
            pass
        # search for scoring_engine vN
        for m in scoring_regex.finditer(txt):
            ver = int(m.group(1))
            if ver >= 3:
                scoring_matches.append({
                    'file': path.replace('\\','/'),
                    'version': ver,
                    'match': m.group(0)
                })
# Also scan top-level dirs for folder named scoring_engine_v3 or similar
for name in os.listdir('.'):
    if os.path.isdir(name) and re.search(r"scoring[_-]?engine[_-]?v(\d+)", name, re.I):
        m = re.search(r"scoring[_-]?engine[_-]?v(\d+)", name, re.I)
        ver = int(m.group(1))
        if ver >= 3:
            scoring_matches.append({'file': name.replace('\\','/'), 'version': ver, 'match': name})
out = {'scoring_matches': scoring_matches, 'files_2026': sorted(list(set(files_2026)))}
print(json.dumps(out, indent=2))
