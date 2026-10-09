"""Personal saved views and scoped notification queries. No external services."""
from datetime import timedelta
from urllib.parse import urlencode
import json
import auth, config, database, enterprise, governance
from clock import utc_today

SCHEMA='''
CREATE TABLE IF NOT EXISTS saved_views (
 id INTEGER PRIMARY KEY, employee_id TEXT NOT NULL REFERENCES employees(employee_id),
 name TEXT NOT NULL, module TEXT NOT NULL, filters TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(employee_id,name)
);
CREATE INDEX IF NOT EXISTS ix_review_latest ON access_reviews(employee_id,review_date DESC);
CREATE INDEX IF NOT EXISTS ix_outbox_recipient ON notification_outbox(recipient_id,id DESC);
'''
MODULES={'employees':('q','status','facility'),'notes':('q','employee'),'workbench':('q','kind','overdue')}

def migrate(c):
    c.executescript(SCHEMA)
    c.execute('INSERT OR IGNORE INTO schema_versions VALUES (11,?)',(enterprise.now(),))

def filters(module,data):
    if module not in MODULES:raise ValueError('Unsupported saved-view module.')
    out={k:str(data.get(k,'')).strip() for k in MODULES[module] if str(data.get(k,'')).strip()}
    if any(len(v)>100 for v in out.values()):raise ValueError('A filter is too long.')
    if out.get('status') and out['status'] not in config.STATUSES:raise ValueError('Unknown status.')
    if out.get('facility') and out['facility'] not in config.FACILITIES:raise ValueError('Unknown site.')
    if out.get('overdue') and out['overdue']!='1':raise ValueError('Invalid overdue filter.')
    if out.get('kind'):
        from v10_ui import KINDS
        if out['kind'] not in KINDS:raise ValueError('Unknown work category.')
    return out

def save_view(actor,name,module,data):
    name=str(name or '').strip()
    if not 2<=len(name)<=60:raise ValueError('Use a view name of 2 to 60 characters.')
    query=filters(module,data)
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'IAMOperator','Manager','Auditor'})
        if c.execute('SELECT COUNT(*) FROM saved_views WHERE employee_id=?',(actor,)).fetchone()[0]>=20:raise ValueError('Keep at most 20 saved views; remove an old view first.')
        vid=c.execute('INSERT INTO saved_views(employee_id,name,module,filters,created_at) VALUES (?,?,?,?,?)',(actor,name,module,json.dumps(query,sort_keys=True),enterprise.now())).lastrowid
        governance.event(c,actor,actor,'SAVED_VIEW_CREATED',{'id':vid,'module':module,'name':name})
    return vid

def remove_view(actor,vid):
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.active(c,actor)
        if not c.execute('SELECT 1 FROM saved_views WHERE id=? AND employee_id=?',(vid,actor)).fetchone():raise PermissionError('Saved view not found in your workspace.')
        c.execute('DELETE FROM saved_views WHERE id=? AND employee_id=?',(vid,actor))
        governance.event(c,actor,actor,'SAVED_VIEW_REMOVED',{'id':vid})

def view_url(row):
    module=row['module'];q=filters(module,json.loads(row['filters']))
    return '/'+module+('?' + urlencode(q) if q else '')

# Scope is inside every UNION branch. There is no global notification cache.
INBOX='''
WITH latest AS (SELECT employee_id,MAX(review_date) reviewed FROM access_reviews GROUP BY employee_id),
items AS (
 SELECT 'request:'||request_id key,'Approval pending' title,
 printf('REQ-%04d',request_id)||' · '||requested_role text,'/requests/'||request_id href,'orange' tone,'Requests' category
 FROM access_requests WHERE status='Pending' AND (:elevated=1 OR employee_id=:actor)
 UNION ALL
 SELECT 'contract:'||employee_id||':'||end_date,'Contract deadline',name||' · '||end_date,'/employees/'||employee_id,
 CASE WHEN end_date<:today THEN 'red' ELSE 'orange' END,'Contracts'
 FROM employees WHERE :elevated=1 AND worker_type='Agency' AND status='Active' AND end_date<=:deadline
 UNION ALL
 SELECT 'review:'||e.employee_id||':'||substr(COALESCE(l.reviewed,e.start_date),1,10),'Review overdue',
 e.name||' · last review/start '||substr(COALESCE(l.reviewed,e.start_date),1,10),'/access-reviews','orange','Reviews'
 FROM employees e LEFT JOIN latest l USING(employee_id)
 WHERE :elevated=1 AND e.status='Active' AND substr(COALESCE(l.reviewed,e.start_date),1,10)<:review_before
 UNION ALL
 SELECT 'outbox:'||id,title,message,href,'orange','System' FROM notification_outbox WHERE recipient_id=:actor
)
SELECT i.*,CASE WHEN r.notification_key IS NULL THEN 0 ELSE 1 END read
FROM items i LEFT JOIN notification_reads r ON r.employee_id=:actor AND r.notification_key=i.key
'''

def inbox_context(c,actor):
    enterprise.active(c,actor)
    roles={r[0] for r in c.execute('SELECT role FROM employee_roles WHERE employee_id=?',(actor,))}
    return {'actor':actor,'elevated':int(bool(roles&{'Manager','IAMOperator','Auditor'})),
            'today':str(utc_today()),'deadline':str(utc_today()+timedelta(days=14)),
            'review_before':str(utc_today()-timedelta(days=90))}

def inbox(c,actor,q='',category='',state='all',page=1,size=25):
    if not 1<=page<=1000000 or not 1<=size<=100:raise ValueError('Invalid inbox page.')
    if category not in ('','Requests','Contracts','Reviews','System') or state not in ('all','unread','read'):raise ValueError('Unknown inbox filter.')
    args=inbox_context(c,actor);args.update(q='%'+q[:100]+'%',category=category,state=state,size=size,offset=(page-1)*size)
    where=" WHERE (title LIKE :q OR text LIKE :q) AND (:category='' OR category=:category) AND (:state='all' OR (:state='unread' AND read=0) OR (:state='read' AND read=1))"
    base=' FROM ('+INBOX+')'+where
    stats=c.execute('SELECT COUNT(*) total,COALESCE(SUM(1-read),0) unread'+base,args).fetchone()
    rows=[dict(r) for r in c.execute('SELECT *'+base+' ORDER BY read,CASE tone WHEN \'red\' THEN 0 ELSE 1 END,category,key LIMIT :size OFFSET :offset',args)]
    return dict(stats),rows

def mark_read(actor,keys):
    keys=list(dict.fromkeys(keys))
    if not 1<=len(keys)<=25 or any(not isinstance(k,str) or len(k)>150 for k in keys):raise ValueError('Select 1 to 25 current reminders.')
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');args=inbox_context(c,actor)
        for i,key in enumerate(keys):args['k'+str(i)]=key
        marks=','.join(':k'+str(i) for i in range(len(keys)))
        actual={r['key'] for r in c.execute('SELECT * FROM ('+INBOX+') WHERE key IN ('+marks+')',args)}
        if actual!=set(keys):raise LookupError('A reminder is outside your scope or no longer current. Reload the inbox.')
        c.executemany('INSERT INTO notification_reads VALUES (?,?,?) ON CONFLICT(employee_id,notification_key) DO UPDATE SET read_at=excluded.read_at',[(actor,k,enterprise.now()) for k in keys])
        governance.event(c,actor,actor,'NOTIFICATIONS_MARKED_READ',{'count':len(keys)})
