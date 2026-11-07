import argparse,os,tempfile
from pathlib import Path
import pandas as pd
from .db import ROOT,DEFAULT_DB,connect
from .sample import generate,TABLES
from .validation import validate
def create(db=DEFAULT_DB,seed=42,data=None):
    db=Path(db).resolve()
    if db.exists():raise FileExistsError('Không ghi đè database: '+str(db))
    db.parent.mkdir(parents=True,exist_ok=True);data=generate(seed) if data is None else data
    fd,tmp=tempfile.mkstemp(dir=db.parent,suffix='.db');os.close(fd)
    try:
        with connect(tmp,False) as c:
            c.executescript((ROOT/'sql/schema.sql').read_text(encoding='utf-8'))
            sizes=dict(product_groups=2,products=3,shifts=2,batches=5,units=3,defect_types=2,inspections=4,inspection_defects=2,reworks=3)
            for table in TABLES:c.executemany('INSERT INTO '+table+' VALUES('+','.join('?' for _ in range(sizes[table]))+')',data[table])
            c.executemany('INSERT INTO metadata VALUES(?,?)',{'data_kind':'simulated','seed':str(seed),'version':'1.0.0','start':'2026-01-01','end':'2026-03-31 23:59:59','timezone':'Asia/Ho_Chi_Minh','result_rule':'no defect row = pass; at least one defect type = fail','timeline_rule':'production < first inspection < rework < second inspection'}.items())
        validate(tmp);os.link(tmp,db)
    finally:Path(tmp).unlink(missing_ok=True)
    return validate(db)
def prepare(db=DEFAULT_DB,raw_out=None):
    if not Path(db).exists():create(db)
    q=validate(db);out=Path(raw_out or ROOT/'data/raw');out.mkdir(parents=True,exist_ok=True)
    with connect(db) as c:
        for table in TABLES+['metadata']:pd.read_sql_query('SELECT * FROM '+table,c).to_csv(out/(table+'.csv'),index=False,encoding='utf-8-sig')
    print('GIẢ LẬP — giữ nguyên DB nếu đã có. CSV nguồn:',out);print(q.to_string(index=False));return q
def main():
    p=argparse.ArgumentParser();p.add_argument('--db',default=str(DEFAULT_DB));p.add_argument('--raw-out');a=p.parse_args();prepare(a.db,a.raw_out)
if __name__=='__main__':main()
