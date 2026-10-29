"""En desarrollo: registro de muestras en SQLite local. La PWA aun no lo usa."""
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
import json,sqlite3,threading
from app.schemas.samples import SampleIn,UfcInput
from app.services.ufc import calcular_ufc

class SampleNotFound(Exception):pass

class SampleRepository:
    def __init__(self,path):
        self.path=Path(path);self._lock=threading.Lock()

    @contextmanager
    def _connect(self):
        # One connection per call, serialized: a local demo has few concurrent writers.
        with self._lock:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            con=sqlite3.connect(self.path)
            try:
                con.execute('create table if not exists samples(id integer primary key,code text unique not null,data text not null,'
                            'created_at text not null,updated_at text not null)')
                yield con
                con.commit()
            finally:con.close()

    @staticmethod
    def _record(row):
        ident,code,data,created,updated=row
        body=json.loads(data)
        return {'id':ident,'code':code,**body,'result':calcular_ufc(UfcInput(**body)),'created_at':created,'updated_at':updated}

    @staticmethod
    def _fetch(con,ident):
        row=con.execute('select id,code,data,created_at,updated_at from samples where id=?',(ident,)).fetchone()
        if row is None:raise SampleNotFound
        return row

    def list(self):
        with self._connect() as con:
            rows=con.execute('select id,code,data,created_at,updated_at from samples order by id desc').fetchall()
        out=[]
        for row in rows:
            r=self._record(row)
            out.append({k:r[k] for k in ('id','code','analyzed_at','sample_type','responsible','origin','updated_at')}|
                       {'result':r['result'] and {k:r['result'][k] for k in ('value','unit','in_range')}})
        return out

    def create(self,data:SampleIn):
        now=datetime.now().isoformat(timespec='seconds')
        with self._connect() as con:
            last=con.execute('select max(id) from samples').fetchone()[0] or 0
            cur=con.execute('insert into samples(code,data,created_at,updated_at) values(?,?,?,?)',
                            (f'M-{last+1:05d}',data.model_dump_json(),now,now))
            return self._record(self._fetch(con,cur.lastrowid))

    def get(self,ident):
        with self._connect() as con:return self._record(self._fetch(con,ident))

    def update(self,ident,data:SampleIn):
        now=datetime.now().isoformat(timespec='seconds')
        with self._connect() as con:
            self._fetch(con,ident)
            con.execute('update samples set data=?,updated_at=? where id=?',(data.model_dump_json(),now,ident))
            return self._record(self._fetch(con,ident))

    def delete(self,ident):
        with self._connect() as con:
            self._fetch(con,ident)
            con.execute('delete from samples where id=?',(ident,))
