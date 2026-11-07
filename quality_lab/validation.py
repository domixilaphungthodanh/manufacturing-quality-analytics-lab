import re
from datetime import datetime
import pandas as pd
from .db import connect
from .sample import START,END
def timestamp(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',value):raise ValueError('Ngày giờ cần YYYY-MM-DD HH:MM:SS: '+str(value))
    parsed=datetime.strptime(value,'%Y-%m-%d %H:%M:%S')
    if not START<=parsed<=END:raise ValueError('Sự kiện ngoài kỳ mẫu: '+value)
    return parsed
def validate(db):
    with connect(db) as c:
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or c.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Cấu trúc/khóa ngoại không hợp lệ')
        m=dict(c.execute('SELECT * FROM metadata'))
        if m.get('data_kind')!='simulated':raise ValueError('Thiếu nhãn GIẢ LẬP')
        b=pd.read_sql_query('SELECT * FROM batches',c)
        units=pd.read_sql_query('SELECT u.*,b.produced_at FROM units u JOIN batches b USING(batch_id)',c)
        inspections=pd.read_sql_query('SELECT * FROM inspections ORDER BY unit_id,inspection_no',c)
        defects=pd.read_sql_query('SELECT * FROM inspection_defects',c)
        repairs=pd.read_sql_query('SELECT * FROM reworks',c)
        counts={t:c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ['product_groups','products','shifts','batches','units','defect_types','inspections','inspection_defects','reworks']}
    for v in b.produced_at:timestamp(v)
    produced=dict(zip(units.unit_id,units.produced_at));has_defects=set(defects.inspection_id)
    firsts={};seconds={}
    for row in inspections.itertuples(index=False):
        time=timestamp(row.inspected_at)
        if time<=timestamp(produced[row.unit_id]):raise ValueError(f'Kiểm tra {row.inspection_id} phải sau sản xuất ít nhất một giây')
        if row.inspection_no==1:firsts[row.unit_id]=(row.inspected_at,row.inspection_id in has_defects)
        elif row.inspection_no==2:seconds[row.unit_id]=row.inspected_at
        else:raise ValueError('Chỉ có kiểm tra lần 1/2')
    reworked={}
    for row in repairs.itertuples(index=False):
        timestamp(row.completed_at)
        if row.unit_id not in firsts or not firsts[row.unit_id][1]:raise ValueError(f'Chỉ sửa đơn vị lỗi lần đầu: {row.unit_id}')
        if row.completed_at<=firsts[row.unit_id][0]:raise ValueError(f'Sửa phải sau kiểm tra đầu: {row.unit_id}')
        reworked[row.unit_id]=row.completed_at
    for unit,time in seconds.items():
        if unit not in reworked or time<=reworked[unit]:raise ValueError(f'Kiểm tra lại phải sau sửa: {unit}')
    counts.update(initial_inspections=len(firsts),initial_failed_units=sum(failed for _,failed in firsts.values()),reinspected_units=len(seconds),structural_errors=0,timeline_errors=0)
    return pd.DataFrame([{'metric':k,'value':v,'scope':'full simulated database'} for k,v in counts.items()])
