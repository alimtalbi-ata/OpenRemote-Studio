"""Opt-in local SSH diagnostic history, anonymized; author Abdelhalim Talbi."""
import json
import sqlite3
import time
import math
from contextlib import closing
from ssh_diagnostic_compare import _read
from ssh_route_scope import validate_token

SCHEMA="""CREATE TABLE IF NOT EXISTS diagnostics (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 recorded_at INTEGER NOT NULL,
 report_json TEXT NOT NULL
)"""

def normalize(report):
    status,steps=_read(report)
    # Whitelist, never store arbitrary imported fields or server identity.
    order=['Bastion principal','Bastion 2','Bastion 3','Bastion 4','Serveur cible','Diagnostic']
    return {'schema':'openremote.ssh-diagnostic.v1','status':status,
            'steps':[{'step':name,**steps[name]} for name in order if name in steps]}

class DiagnosticHistory:
    def __init__(self,path):
        self.path=str(path)
        with closing(sqlite3.connect(self.path,timeout=5)) as db, db:
            db.execute(SCHEMA)
            db.execute("CREATE TABLE IF NOT EXISTS diagnostic_scopes (diagnostic_id INTEGER PRIMARY KEY, route_id TEXT NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_scopes_route ON diagnostic_scopes(route_id)")
            db.execute("CREATE TABLE IF NOT EXISTS import_audit (id INTEGER PRIMARY KEY AUTOINCREMENT, imported_at INTEGER NOT NULL, total INTEGER NOT NULL, inserted INTEGER NOT NULL, duplicates INTEGER NOT NULL, conflicts INTEGER NOT NULL)")
    def add(self,report, *, route_id=None):
        if route_id is not None: validate_token(route_id)
        clean=normalize(report)
        with closing(sqlite3.connect(self.path,timeout=5)) as db, db:
            cursor=db.execute('INSERT INTO diagnostics(recorded_at,report_json) VALUES (?,?)',
                              (int(time.time()),json.dumps(clean,ensure_ascii=False,sort_keys=True)))
            db.execute('DELETE FROM diagnostics WHERE id NOT IN (SELECT id FROM diagnostics ORDER BY id DESC LIMIT 200)')
            db.execute('DELETE FROM diagnostic_scopes WHERE diagnostic_id NOT IN (SELECT id FROM diagnostics)')
            row_id=cursor.lastrowid
            if route_id is not None:
                db.execute('INSERT INTO diagnostic_scopes(diagnostic_id,route_id) VALUES (?,?)',(row_id,route_id))
            return row_id
    def recent(self,limit=20):
        if type(limit) is not int or not 1<=limit<=200:raise ValueError('Limite invalide')
        with closing(sqlite3.connect(self.path,timeout=5)) as db, db:
            rows=db.execute('SELECT id,recorded_at,report_json FROM diagnostics ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
        return [{'id':id,'recorded_at':ts,'report':json.loads(data)} for id,ts,data in rows]
    def filtered(self, *, since=None, until=None, status=None, limit=200, route_id=None):
        """Bounded, parameterized time/status filter; no server identifiers stored."""
        if route_id is not None: validate_token(route_id)
        if type(limit) is not int or not 1<=limit<=200:raise ValueError('Limite invalide')
        for value in (since,until):
            if value is not None and (type(value) is not int or value<0):raise ValueError('Date invalide')
        if since is not None and until is not None and since>until:raise ValueError('Période invalide')
        if status is not None and status not in ('authenticated','failed','cancelled'):raise ValueError('État invalide')
        clauses=[];params=[]
        if since is not None:clauses.append('recorded_at >= ?');params.append(since)
        if until is not None:clauses.append('recorded_at <= ?');params.append(until)
        query='SELECT d.id,d.recorded_at,d.report_json FROM diagnostics d'
        if route_id is not None:
            query+=' JOIN diagnostic_scopes s ON s.diagnostic_id=d.id'
            clauses.append('s.route_id = ?');params.append(route_id)
        if clauses:query+=' WHERE '+' AND '.join(clauses)
        query+=' ORDER BY d.id DESC LIMIT ?';params.append(200)
        with closing(sqlite3.connect(self.path,timeout=5)) as db, db:
            rows=db.execute(query,params).fetchall()
        results=[{'id':id,'recorded_at':ts,'report':json.loads(data)} for id,ts,data in rows]
        if status is not None:results=[row for row in results if row['report']['status']==status]
        return results[:limit]

    def purge_before(self, cutoff):
        """Explicit retention purge, returns number of removed records."""
        if type(cutoff) is not int or cutoff<0:raise ValueError('Date invalide')
        with closing(sqlite3.connect(self.path,timeout=5)) as db, db:
            count=db.execute('DELETE FROM diagnostics WHERE recorded_at < ?', (cutoff,)).rowcount
            db.execute('DELETE FROM diagnostic_scopes WHERE diagnostic_id NOT IN (SELECT id FROM diagnostics)')
            return count

    def statistics(self, *, since=None, until=None, status=None, route_id=None):
        """Return bounded, anonymized aggregate and time series."""
        records=self.filtered(since=since,until=until,status=status,limit=200,route_id=route_id)
        return {'count':len(records),'steps':trends(records),
                'series':{step:duration_series(records,step,limit=200) for step in
                          ('Bastion principal','Bastion 2','Bastion 3','Bastion 4','Serveur cible')}}

    @staticmethod
    def _validated_import_rows(records):
        if not isinstance(records, list) or len(records) > 200:
            raise ValueError('Historique importé invalide')
        clean=[]
        for row in records:
            if not isinstance(row, dict) or set(row) != {'recorded_at','report'}:
                raise ValueError('Enregistrement importé invalide')
            if type(row['recorded_at']) is not int or row['recorded_at'] < 0:
                raise ValueError('Horodatage importé invalide')
            report=normalize(row['report'])
            if report != row['report']:
                raise ValueError('Rapport importé non canonique')
            clean.append((row['recorded_at'],json.dumps(report,ensure_ascii=False,sort_keys=True)))
        return clean

    def preview_import(self, records):
        """Return duplicate/new counts without changing the database.

        Duplicate identity is the exact pair (original timestamp, canonical report).
        Preview is advisory; import_verified repeats checks transactionally.
        """
        clean=self._validated_import_rows(records)
        incoming=set(clean)
        with closing(sqlite3.connect(self.path,timeout=5)) as db:
            existing=set(db.execute('SELECT recorded_at,report_json FROM diagnostics').fetchall())
        unique_new=set()
        duplicates=0
        conflicts=0
        by_timestamp={}
        for ts, body in existing: by_timestamp.setdefault(ts,set()).add(body)
        seen=set(existing)
        for item in clean:
            if item in seen:
                duplicates+=1
            else:
                if item[0] in by_timestamp and item[1] not in by_timestamp[item[0]]: conflicts+=1
                unique_new.add(item)
                seen.add(item)
                by_timestamp.setdefault(item[0],set()).add(item[1])
        return {'total':len(clean),'new':len(unique_new),'duplicates':duplicates}

    def preview_import_details(self, records):
        """Additional non-sensitive details, preserving preview_import's v11.1 contract."""
        clean=self._validated_import_rows(records)
        with closing(sqlite3.connect(self.path,timeout=5)) as db:
            existing=set(db.execute('SELECT recorded_at,report_json FROM diagnostics').fetchall())
        by_timestamp={}
        for ts,body in existing:by_timestamp.setdefault(ts,set()).add(body)
        seen=set(existing);conflicts=0;sample=[]
        for ts,body in clean:
            if (ts,body) in seen:continue
            if ts in by_timestamp and body not in by_timestamp[ts]:conflicts+=1
            seen.add((ts,body));by_timestamp.setdefault(ts,set()).add(body)
            if len(sample)<5:sample.append({'recorded_at':ts,'status':json.loads(body)['status']})
        return {'timestamp_conflicts':conflicts,'sample':sample}

    def import_verified(self, records):
        """Import already HMAC-verified normalized records, skipping exact duplicates.

        Caller MUST verify the envelope before calling this method. Records are
        revalidated and inserted atomically; duplicate checks are repeated inside
        the transaction to avoid a preview/import race.
        """
        clean=self._validated_import_rows(records)
        imported=0
        conflicts=0
        with closing(sqlite3.connect(self.path,timeout=5)) as db, db:
            existing=set(db.execute('SELECT recorded_at,report_json FROM diagnostics').fetchall())
            seen=set(existing)
            by_timestamp={}
            for ts,body in existing: by_timestamp.setdefault(ts,set()).add(body)
            for timestamp,report_json in clean:
                item=(timestamp,report_json)
                if item in seen:
                    continue
                if timestamp in by_timestamp and report_json not in by_timestamp[timestamp]: conflicts+=1
                db.execute('INSERT INTO diagnostics(recorded_at,report_json) VALUES (?,?)',item)
                seen.add(item)
                by_timestamp.setdefault(timestamp,set()).add(report_json)
                imported+=1
            db.execute('DELETE FROM diagnostics WHERE id NOT IN (SELECT id FROM diagnostics ORDER BY id DESC LIMIT 200)')
            db.execute('DELETE FROM diagnostic_scopes WHERE diagnostic_id NOT IN (SELECT id FROM diagnostics)')
            db.execute('INSERT INTO import_audit(imported_at,total,inserted,duplicates,conflicts) VALUES (?,?,?,?,?)',(int(time.time()),len(clean),imported,len(clean)-imported,conflicts))
        return imported

    def import_audit(self, limit=20):
        """Bounded, anonymous history of committed import operations."""
        if type(limit) is not int or not 1 <= limit <= 100: raise ValueError('Limite invalide')
        with closing(sqlite3.connect(self.path,timeout=5)) as db:
            rows=db.execute('SELECT imported_at,total,inserted,duplicates,conflicts FROM import_audit ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
        return [dict(zip(('imported_at','total','inserted','duplicates','conflicts'),row)) for row in rows]

    def clear(self):
        with closing(sqlite3.connect(self.path,timeout=5)) as db, db:
            db.execute('DELETE FROM diagnostics')
            db.execute('DELETE FROM diagnostic_scopes')

def percentile(values, percent):
    """Nearest-rank percentile of finite, nonnegative bounded durations."""
    if not isinstance(values, (tuple, list)) or not values:
        return None
    if type(percent) not in (int, float) or not 0 < percent <= 100:
        raise ValueError('Percentile invalide')
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('Durées invalides')
    ordered = sorted(values)
    return ordered[math.ceil(percent / 100 * len(ordered)) - 1]


def trends(records):
    if not isinstance(records,list) or len(records)>200:raise ValueError('Historique invalide')
    by_step={}
    for entry in records:
        report=normalize(entry['report'])
        for step in report['steps']:
            data=by_step.setdefault(step['step'],{'runs':0,'failures':0,'durations':[]})
            data['runs']+=1
            data['failures']+=step['state']=='failed'
            if step.get('duration_ms') is not None:data['durations'].append(step['duration_ms'])
    return [{'step':name,'runs':data['runs'],'failures':data['failures'],
             'failure_rate_pct':round(100*data['failures']/data['runs'],1),
             'average_ms':round(sum(data['durations'])/len(data['durations'])) if data['durations'] else None,
             'median_ms':percentile(data['durations'],50),
             'p95_ms':percentile(data['durations'],95),
             'last_ms':data['durations'][0] if data['durations'] else None}
            for name,data in sorted(by_step.items())]

def duration_series(records,step='Bastion principal',limit=30):
    """Chronological bounded series of measured step latency, without endpoint identity."""
    if step not in ('Bastion principal','Bastion 2','Bastion 3','Bastion 4','Serveur cible','Diagnostic'):
        raise ValueError('Étape invalide')
    if type(limit) is not int or not 1<=limit<=200:raise ValueError('Limite invalide')
    if not isinstance(records,list) or len(records)>200:raise ValueError('Historique invalide')
    series=[]
    for row in reversed(records):
        clean=normalize(row['report'])
        for item in clean['steps']:
            if item['step']==step and item['duration_ms'] is not None:
                series.append({'recorded_at':row['recorded_at'],'duration_ms':item['duration_ms'],'state':item['state']})
    return series[-limit:]
