import json, subprocess, sys, os
ROOT='.'
# selected tags from user selection
selected_tags = [
  "supabase","Verification Engine","Time Sync","Storage Manager","Stats Overlay",
  "Stat Engine","Social Media","Round Validator","Post-Fight Review","Report Generator",
  "Public Stats","Performance Profiler","Normalization Engine","Fight Judge AI",
  "Fighter Analytics","Fan Scoring","Failover Engine","Event Harmonizer","Database Management",
  "Combat Sports","Calibration API","Broadcast Control","Branding & Themes","Blockchain Audit",
  "AI Merge Engine","Advanced Audit"
]

def run_capture(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, text=True)
    if p.returncode != 0:
        print('CMD FAILED:', cmd, file=sys.stderr)
        print(p.stderr, file=sys.stderr)
        sys.exit(1)
    return p.stdout

# 1) get tag map
tag_out = run_capture([sys.executable, '.\\.extract_fastapi_tags.py'])
try:
    tag_map = json.loads(tag_out)
except Exception as e:
    print('failed parse tags', e, file=sys.stderr); sys.exit(1)

# build file list from selected tags
files=set()
for entry in tag_map:
    if entry.get('tag') in selected_tags:
        for f in entry.get('files',[]):
            files.add(os.path.normpath(f))

# 2) get preserved info (2026 + scoring)
preserved_out = run_capture([sys.executable, '.\\.find_2026_and_scoring.py'])
try:
    preserved = json.loads(preserved_out)
except Exception as e:
    print('failed parse preserved', e, file=sys.stderr); sys.exit(1)
for f in preserved.get('files_2026', []):
    files.add(os.path.normpath(f))
for m in preserved.get('scoring_matches', []):
    files.add(os.path.normpath(m.get('file')))

# filter to existing files
files = [f for f in files if os.path.exists(f)]
files.sort()
if not files:
    print('[]')
    sys.exit(0)

# 3) run endpoint extractor on the files
cmd = [sys.executable, '.\\.extract_endpoints.py'] + files
p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
if p.returncode != 0:
    print('extract failed', p.stderr, file=sys.stderr); sys.exit(1)

with open('.\\preserved_endpoints.json', 'w', encoding='utf-8') as fh:
    fh.write(p.stdout)
print('WROTE .\\preserved_endpoints.json with', len(files), 'files')
