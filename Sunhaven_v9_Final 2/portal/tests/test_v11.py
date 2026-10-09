"""Version 11 regression cases: isolation, atomic bulk actions, query budgets."""
import json,sqlite3
from unittest.mock import patch
from test_web import WebTests
import database,release_v11 as v11,experience
from assets import cached_asset
from pathlib import Path

class Version11Tests(WebTests):
    def test_saved_views_round_trip_escape_and_ownership(self):
        self.login();vid=v11.save_view('SC1005','<my view>','employees',{'q':'Sarah & Co','next':'https://invalid.test'})
        with database.connect() as c:r=c.execute('SELECT * FROM saved_views WHERE id=?',(vid,)).fetchone()
        self.assertEqual(v11.view_url(r),'/employees?q=Sarah+%26+Co')
        page=self.call('/saved-views');self.assertEqual(page['status'],200);self.assertIn('&lt;my view&gt;',page['body'])
        self.login('SC1002');self.assertNotIn('&lt;my view&gt;',self.call('/saved-views')['body'])
        self.assertEqual(self.call('/saved-views/delete','POST',{'id':vid})['status'],403)
        v11.remove_view('SC1005',vid)
        with database.connect() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM saved_views').fetchone()[0],0)
    def test_worker_cannot_create_or_list_views(self):
        self.login('SC1003')
        self.assertEqual(self.call('/saved-views')['status'],403)
        self.assertEqual(self.call('/saved-views/save','POST',{'name':'Test','module':'employees'})['status'],403)
    def test_view_validation_and_duplicate(self):
        for module,data in [('https://evil.test',{}),('employees',{'facility':'unknown'}),('employees',{'status':'unknown'}),('workbench',{'kind':'unknown'}),('notes',{'q':'x'*101})]:
            with self.assertRaises(ValueError):v11.save_view('SC1005','Test',module,data)
        v11.save_view('SC1005','Test','notes',{})
        with self.assertRaises(sqlite3.IntegrityError):v11.save_view('SC1005','Test','notes',{})
    def test_saved_view_limit(self):
        for i in range(20):v11.save_view('SC1005',f'View {i}','employees',{})
        with self.assertRaises(ValueError):v11.save_view('SC1005','Overflow','employees',{})
    def test_view_post_csrf(self):
        self.login();self.assertEqual(self.call('/saved-views/save','POST',{'name':'Denied','module':'notes'},csrf=False)['status'],403)
    def test_inbox_filter_and_personal_read(self):
        with database.connect() as c:stats,rows=v11.inbox(c,'SC1005',category='Reviews',size=1)
        self.assertEqual(len(rows),1);v11.mark_read('SC1005',[rows[0]['key']])
        with database.connect() as c:
            read,items=v11.inbox(c,'SC1005',category='Reviews',state='read')
            self.assertEqual(read['total'],1);self.assertEqual(read['unread'],0)
            self.assertTrue(any(x['key']==rows[0]['key'] and not x['read'] for x in v11.inbox(c,'SC1002',category='Reviews')[1]))
    def test_bulk_is_atomic_when_one_key_outside_scope(self):
        with database.connect() as c:_,rows=v11.inbox(c,'SC1005')
        with self.assertRaises(LookupError):v11.mark_read('SC1005',[rows[0]['key'],'outbox:999999'])
        with database.connect() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM notification_reads').fetchone()[0],0)
    def test_bulk_size_and_worker_scope(self):
        with self.assertRaises(ValueError):v11.mark_read('SC1005',[str(i) for i in range(26)])
        with database.connect() as c:_,rows=v11.inbox(c,'SC1005',category='Reviews')
        with self.assertRaises(LookupError):v11.mark_read('SC1003',[rows[0]['key']])
    def test_bulk_http_and_inbox_validation(self):
        self.login()
        with database.connect() as c:_,rows=v11.inbox(c,'SC1005')
        self.assertEqual(self.call('/notifications/bulk-read','POST',{'keys':'|'.join(r['key'] for r in rows)})['status'],303)
        for path in ['/notifications?page=0','/notifications?state=invalid','/notifications?category=invalid']:
            self.assertEqual(self.call(path)['status'],400)
    def test_inbox_constant_query_budget(self):
        with database.connect() as c:
            sql=[];c.set_trace_callback(sql.append);v11.inbox(c,'SC1005')
        self.assertLessEqual(len(sql),5)
    def test_qualification_query_budget(self):
        self.login();original=database.connect;sql=[]
        def traced(*args,**kwargs):
            c=original(*args,**kwargs);c.set_trace_callback(sql.append);return c
        with patch.object(database,'connect',side_effect=traced):self.assertEqual(self.call('/qualifications')['status'],200)
        self.assertLessEqual(sum(x.lstrip().upper().startswith('SELECT') for x in sql),15)
    def test_static_etag_and_cache_invalidation(self):
        result=self.call('/static/app.bundle.css');headers=dict(result['headers'])
        self.assertEqual(result['status'],200);self.assertIn('ETag',headers)
        f=Path(self.tmp.name)/'asset';f.write_text('old');a=cached_asset(str(f),f.stat().st_mtime_ns,3)
        f.write_text('changed');b=cached_asset(str(f),f.stat().st_mtime_ns,7)
        self.assertNotEqual(a[1],b[1]);self.assertEqual(b[0],b'changed')
    def test_all_saved_filter_controls_render(self):
        self.login()
        for path in ['/employees','/notes','/workbench']:
            self.assertIn('action="/saved-views/save"',self.call(path)['body'])
    def test_notifications_beyond_old_100_item_limit_remain_searchable(self):
        with database.connect() as c:
            c.executemany("INSERT INTO notification_outbox(dedupe_key,recipient_id,title,message,href,created_at) VALUES (?,'SC1005','System test',?,'/notifications','2026-01-01')",[(f'qa:{i}',f'Unique event {i:03}') for i in range(110)])
            stats,rows=v11.inbox(c,'SC1005',q='Unique event 000',category='System')
        self.assertEqual(stats['total'],1);v11.mark_read('SC1005',[rows[0]['key']])
        with database.connect() as c:self.assertEqual(v11.inbox(c,'SC1003',category='System')[0]['total'],0)
    def test_qualification_register_filters_and_rejects_bad_pages(self):
        self.login()
        result=self.call('/qualifications?q=Professional');self.assertEqual(result['status'],200)
        self.assertIn('Search qualification register',result['body'])
        self.assertEqual(self.call('/qualifications?page=-1')['status'],400)

    def test_migration_idempotent_and_foreign_keys(self):
        database.init_db()
        with database.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM schema_versions WHERE version=11').fetchone()[0],1)
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])

for name in dir(WebTests):
    if name.startswith('test_') and name not in Version11Tests.__dict__:setattr(Version11Tests,name,None)
del WebTests
