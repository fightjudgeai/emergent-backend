import re,sys,os,json
files = sys.argv[1:]
if not files:
    print('[]')
    sys.exit(0)

def find_router_vars(txt):
    # find variable names assigned APIRouter
    rv = {}
    for m in re.finditer(r"^(\s*)(\w+)\s*=\s*APIRouter\s*\((.*?)\)", txt, re.M|re.S):
        name = m.group(2)
        args = m.group(3)
        tags = re.findall(r"tags\s*=\s*\[([^\]]+)\]", args)
        tag_list = []
        if tags:
            tag_list = re.findall(r"['\"](.*?)['\"]", tags[0])
        rv[name] = {'tags': tag_list}
    return rv

# decorator pattern: @<router>.<method>("/path", ...)
dec_re = re.compile(r"^\s*@(\w+)\.(get|post|put|delete|patch|options|head)\s*\(\s*([\'\"][^\'\"]+[\'\"])", re.M)

out=[]
for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as fh:
            txt = fh.read()
    except Exception as e:
        out.append({'file':f, 'error':str(e)})
        continue
    routers = find_router_vars(txt)
    endpoints = []
    for m in dec_re.finditer(txt):
        var,method,pathlit = m.groups()
        path = pathlit.strip('"\'')
        endpoints.append({'decorator_var':var, 'method':method.upper(), 'path':path})
    # try to determine tag for file by looking for APIRouter tags or for module-level comment
    tag_set = set()
    for rname,meta in routers.items():
        for t in meta.get('tags',[]):
            tag_set.add(t)
    # also try to find a line like "router = APIRouter(prefix=..., tags=["Name"] )" earlier
    out.append({'file':f, 'tags':sorted(list(tag_set)), 'routers':routers, 'endpoints':endpoints})
print(json.dumps(out, indent=2))
