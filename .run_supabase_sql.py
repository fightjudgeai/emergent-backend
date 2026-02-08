import os, httpx, sys, json

# Load .env-like vars from environment
SUPABASE_URL = os.getenv('SUPABASE_URL')
SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
SQL_FILE = 'supabase_tables.sql'

# If env vars missing, try to load from .env file in repo root
if (not SUPABASE_URL or not SERVICE_KEY) and os.path.exists('.env'):
    with open('.env', 'r', encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            k,v = line.split('=',1)
            k=k.strip(); v=v.strip()
            # remove surrounding quotes
            if v.startswith('"') and v.endswith('"'):
                v=v[1:-1]
            if v.startswith("'") and v.endswith("'"):
                v=v[1:-1]
            if not os.getenv(k):
                os.environ[k]=v
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not SUPABASE_URL or not SERVICE_KEY:
    print('Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in environment')
    sys.exit(2)

with open(SQL_FILE, 'r', encoding='utf-8') as fh:
    sql = fh.read()

endpoints = [
    f"{SUPABASE_URL.rstrip('/')}/sql",
    f"{SUPABASE_URL.rstrip('/')}/rest/v1/rpc/sql",
    f"{SUPABASE_URL.rstrip('/')}/rest/v1/rpc/execute_sql",
    f"{SUPABASE_URL.rstrip('/')}/rest/v1/rpc/pg_execute",
]

headers = {
    'Authorization': f'Bearer {SERVICE_KEY}',
    'apikey': SERVICE_KEY,
}

client = httpx.Client(timeout=30.0)
result = []
for url in endpoints:
    try:
        # Try raw SQL POST
        r = client.post(url, headers={**headers, 'Content-Type':'application/sql'}, content=sql)
        result.append({'url':url,'status':r.status_code,'text':r.text[:1000]})
        if r.status_code in (200,201,202):
            print('SUCCESS', url, r.status_code)
            print(r.text)
            sys.exit(0)
        # Try JSON wrapper
        r2 = client.post(url, headers={**headers, 'Content-Type':'application/json'}, json={'sql':sql})
        result.append({'url':url+' (json)','status':r2.status_code,'text':r2.text[:1000]})
        if r2.status_code in (200,201,202):
            print('SUCCESS', url+' (json)', r2.status_code)
            print(r2.text)
            sys.exit(0)
    except Exception as e:
        result.append({'url':url,'error':str(e)})

print('No endpoint accepted the SQL. Responses:')
print(json.dumps(result, indent=2))
print('\nIf this fails, open the Supabase Project SQL editor and paste the contents of supabase_tables.sql to run it manually.')
sys.exit(1)
