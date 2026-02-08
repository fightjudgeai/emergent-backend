import json, re, sys
p='preserved_endpoints.json'
with open(p,'r',encoding='utf-8') as fh:
    data=json.load(fh)

# scoring weights
method_weight={'POST':5,'PUT':4,'PATCH':4,'DELETE':4,'GET':1,'HEAD':1,'OPTIONS':1}
keywords=[('fight',5),('judg',5),('score',5),('scoring',5),('validate',4),('approve',4),('aggregate',4),('initialize',4),('broadcast',3),('video',3),('upload',3),('generate',3),('admin',3),('health',2),('stats',2),('leaderboard',3),('auth',2)]

items=[]
for entry in data:
    file=entry.get('file')
    tag_list=entry.get('tags',[])
    for ep in entry.get('endpoints',[]):
        path=ep.get('path','')
        method=ep.get('method','GET')
        score=method_weight.get(method.upper(),1)
        path_l=path.lower()
        for k,w in keywords:
            if k in path_l:
                score+=w
        # also tag boosts
        for t in tag_list:
            tl=t.lower()
            if 'scoring' in tl or 'judge' in tl or 'fight' in tl or 'database' in tl or 'broadcast' in tl:
                score+=2
        items.append({'file':file,'tag':tag_list,'method':method,'path':path,'score':score})

items.sort(key=lambda x: x['score'], reverse=True)
# print top 40
out=items[:40]
print(json.dumps(out, indent=2))
