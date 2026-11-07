import pandas as pd
import numpy as np
from .db import connect,day
from .validation import validate
STATES=['not_inspected','initial_passed','waiting_rework','waiting_reinspection','reinspection_passed','reinspection_failed']
COUNTS=['initial_inspected','initial_failed','initial_passed','initial_defect_count','reworked','reinspected','reinspection_passed','reinspection_failed','reinspection_defect_count','not_inspected','waiting_rework','waiting_reinspection']
def scope(start='2026-01-01',end=None,as_of='2026-03-31'):
    end=end or as_of
    for value in [start,end,as_of]:day(value)
    if not '2026-01-01'<=start<=end<=as_of<='2026-03-31':raise ValueError('Cần 2026-01-01 <= start <= end <= as-of <= 2026-03-31')
    return {'start':start,'end':end,'as_of':as_of,'cutoff':as_of+' 23:59:59'}
BASE='''WITH selected_batches AS (
 SELECT * FROM batches WHERE date(produced_at) BETWEEN :start AND :end AND produced_at<=:cutoff
), defect_counts AS (
 SELECT inspection_id,COUNT(*) AS n FROM inspection_defects GROUP BY inspection_id
), visible_inspections AS (
 SELECT i.unit_id,MAX(CASE WHEN inspection_no=1 THEN inspected_at END) AS initial_at,
 MAX(CASE WHEN inspection_no=2 THEN inspected_at END) AS reinspection_at,
 MAX(CASE WHEN inspection_no=1 THEN COALESCE(d.n,0) ELSE 0 END) AS initial_defect_count,
 MAX(CASE WHEN inspection_no=2 THEN COALESCE(d.n,0) ELSE 0 END) AS reinspection_defect_count
 FROM inspections i LEFT JOIN defect_counts d USING(inspection_id) WHERE i.inspected_at<=:cutoff GROUP BY i.unit_id
), joined AS (
 SELECT u.unit_id,u.unit_code,b.batch_id,b.batch_code,b.produced_at,b.product_id,p.name AS product_name,
 p.group_id,g.name AS group_name,b.shift_id,s.name AS shift_name,
 v.initial_at,v.reinspection_at,COALESCE(v.initial_defect_count,0) AS initial_defect_count,
 COALESCE(v.reinspection_defect_count,0) AS reinspection_defect_count,r.completed_at AS rework_at
 FROM units u JOIN selected_batches b USING(batch_id) JOIN products p USING(product_id)
 JOIN product_groups g USING(group_id) JOIN shifts s USING(shift_id)
 LEFT JOIN visible_inspections v USING(unit_id)
 LEFT JOIN reworks r ON r.unit_id=u.unit_id AND r.completed_at<=:cutoff
), unit_rows AS MATERIALIZED (
 SELECT *,CASE WHEN initial_at IS NULL THEN 'not_inspected'
 WHEN initial_defect_count=0 THEN 'initial_passed'
 WHEN rework_at IS NULL THEN 'waiting_rework'
 WHEN reinspection_at IS NULL THEN 'waiting_reinspection'
 WHEN reinspection_defect_count=0 THEN 'reinspection_passed' ELSE 'reinspection_failed' END AS state,
 CAST(initial_at IS NOT NULL AS INTEGER) AS initial_inspected,
 CAST(initial_at IS NOT NULL AND initial_defect_count>0 AS INTEGER) AS initial_failed,
 CAST(initial_at IS NOT NULL AND initial_defect_count=0 AS INTEGER) AS initial_passed,
 CAST(rework_at IS NOT NULL AS INTEGER) AS reworked,
 CAST(reinspection_at IS NOT NULL AS INTEGER) AS reinspected,
 CAST(reinspection_at IS NOT NULL AND reinspection_defect_count=0 AS INTEGER) AS reinspection_passed,
 CAST(reinspection_at IS NOT NULL AND reinspection_defect_count>0 AS INTEGER) AS reinspection_failed,
 CAST(initial_at IS NULL AS INTEGER) AS not_inspected,
 CAST(initial_at IS NOT NULL AND initial_defect_count>0 AND rework_at IS NULL AS INTEGER) AS waiting_rework,
 CAST(rework_at IS NOT NULL AND reinspection_at IS NULL AS INTEGER) AS waiting_reinspection
 FROM joined
)'''
UNIT_SQL=BASE+' SELECT * FROM unit_rows ORDER BY unit_id'
def rates(frame):
    frame=frame.copy()
    frame['coverage_pct']=frame.initial_inspected/frame.unit_count.replace(0,np.nan)*100
    frame['initial_failure_pct']=frame.initial_failed/frame.initial_inspected.replace(0,np.nan)*100
    frame['reinspection_pass_pct']=frame.reinspection_passed/frame.reinspected.replace(0,np.nan)*100
    return frame
def summarize_units(units,keys):
    if units.empty:return pd.DataFrame(columns=keys+['unit_count',*COUNTS])
    return units.groupby(keys,as_index=False).agg(unit_count=('unit_id','size'),**{col:(col,'sum') for col in COUNTS})
def sql_tables(db,start='2026-01-01',end=None,as_of='2026-03-31'):
    p=scope(start,end,as_of)
    with connect(db) as c:
        units=pd.read_sql_query(UNIT_SQL,c,params=p)
        sums=','.join('COALESCE(SUM(u.'+col+'),0) AS '+col for col in COUNTS)
        batches=pd.read_sql_query(BASE+''' SELECT b.batch_id,b.batch_code,b.produced_at,p.name AS product_name,b.shift_id,
            COUNT(u.unit_id) AS unit_count,'''+sums+''' FROM selected_batches b JOIN products p USING(product_id)
            LEFT JOIN unit_rows u USING(batch_id) GROUP BY b.batch_id ORDER BY b.batch_id''',c,params=p)
        shifts=pd.read_sql_query(BASE+''' SELECT s.shift_id,s.name AS shift_name,COUNT(u.unit_id) AS unit_count,'''+sums+''' FROM shifts s
            LEFT JOIN unit_rows u USING(shift_id) GROUP BY s.shift_id ORDER BY s.shift_id''',c,params=p)
        daily=pd.read_sql_query(BASE+''', calendar(date) AS (SELECT :start UNION ALL SELECT date(date,'+1 day') FROM calendar WHERE date<:as_of),
            totals AS (SELECT date(initial_at) AS date,COUNT(*) AS initial_inspected,SUM(initial_failed) AS initial_failed,SUM(initial_defect_count) AS initial_defect_count
            FROM unit_rows WHERE initial_at IS NOT NULL GROUP BY date(initial_at))
            SELECT c.date,COALESCE(t.initial_inspected,0) AS initial_inspected,COALESCE(t.initial_failed,0) AS initial_failed,COALESCE(t.initial_defect_count,0) AS initial_defect_count
            FROM calendar c LEFT JOIN totals t USING(date) ORDER BY c.date''',c,params=p)
        defects=pd.read_sql_query(BASE+''', rounds(inspection_no) AS (VALUES(1),(2)), grouped AS (
            SELECT p.group_id,i.inspection_no,d.defect_type_id,COUNT(*) AS defect_count,COUNT(DISTINCT i.unit_id) AS affected_units
            FROM inspection_defects d JOIN inspections i USING(inspection_id) JOIN units u USING(unit_id)
            JOIN selected_batches b USING(batch_id) JOIN products p USING(product_id)
            WHERE i.inspected_at<=:cutoff GROUP BY p.group_id,i.inspection_no,d.defect_type_id)
            SELECT g.group_id,g.name AS group_name,r.inspection_no,d.defect_type_id,d.name AS defect_name,
            COALESCE(x.defect_count,0) AS defect_count,COALESCE(x.affected_units,0) AS affected_units
            FROM product_groups g CROSS JOIN rounds r CROSS JOIN defect_types d LEFT JOIN grouped x
            ON x.group_id=g.group_id AND x.inspection_no=r.inspection_no AND x.defect_type_id=d.defect_type_id
            ORDER BY g.group_id,r.inspection_no,d.defect_type_id''',c,params=p)
    daily['initial_failure_pct']=daily.initial_failed/daily.initial_inspected.replace(0,np.nan)*100
    shifts=rates(shifts);shifts['chart_eligible']=shifts.initial_inspected>=100
    return {'units':units,'daily':daily,'batches':rates(batches),'shifts':shifts,'defects':defects}
def pandas_tables(db,start='2026-01-01',end=None,as_of='2026-03-31'):
    p=scope(start,end,as_of)
    with connect(db) as c:
        raw={t:pd.read_sql_query('SELECT * FROM '+t,c) for t in ['units','batches','products','product_groups','shifts','inspections','inspection_defects','reworks','defect_types']}
    selected=raw['batches'][raw['batches'].produced_at.str[:10].between(p['start'],p['end'])&(raw['batches'].produced_at<=p['cutoff'])]
    base=raw['units'].merge(selected,on='batch_id',validate='many_to_one').merge(raw['products'].rename(columns={'name':'product_name'}),on='product_id',validate='many_to_one').merge(raw['product_groups'].rename(columns={'name':'group_name'}),on='group_id',validate='many_to_one').merge(raw['shifts'].rename(columns={'name':'shift_name'}),on='shift_id',validate='many_to_one')
    count=raw['inspection_defects'].groupby('inspection_id').size().to_dict()
    visible=raw['inspections'][raw['inspections'].inspected_at<=p['cutoff']]
    first=visible[visible.inspection_no==1].set_index('unit_id');second=visible[visible.inspection_no==2].set_index('unit_id')
    repairs=raw['reworks'][raw['reworks'].completed_at<=p['cutoff']].set_index('unit_id')
    base['initial_at']=base.unit_id.map(first.inspected_at);base['reinspection_at']=base.unit_id.map(second.inspected_at)
    base['initial_defect_count']=base.unit_id.map(first.inspection_id).map(count).fillna(0).astype('int64')
    base['reinspection_defect_count']=base.unit_id.map(second.inspection_id).map(count).fillna(0).astype('int64');base['rework_at']=base.unit_id.map(repairs.completed_at)
    base['initial_inspected']=base.initial_at.notna().astype(int);base['initial_failed']=((base.initial_inspected==1)&(base.initial_defect_count>0)).astype(int);base['initial_passed']=((base.initial_inspected==1)&(base.initial_defect_count==0)).astype(int)
    base['reworked']=base.rework_at.notna().astype(int);base['reinspected']=base.reinspection_at.notna().astype(int)
    base['reinspection_passed']=((base.reinspected==1)&(base.reinspection_defect_count==0)).astype(int);base['reinspection_failed']=((base.reinspected==1)&(base.reinspection_defect_count>0)).astype(int)
    base['not_inspected']=(base.initial_inspected==0).astype(int);base['waiting_rework']=((base.initial_failed==1)&(base.reworked==0)).astype(int);base['waiting_reinspection']=((base.reworked==1)&(base.reinspected==0)).astype(int)
    base['state']=np.select([base.not_inspected==1,base.initial_passed==1,base.waiting_rework==1,base.waiting_reinspection==1,base.reinspection_passed==1],STATES[:-1],default='reinspection_failed')
    cols=['unit_id','unit_code','batch_id','batch_code','produced_at','product_id','product_name','group_id','group_name','shift_id','shift_name','initial_at','reinspection_at','initial_defect_count','reinspection_defect_count','rework_at','state','initial_inspected','initial_failed','initial_passed','reworked','reinspected','reinspection_passed','reinspection_failed','not_inspected','waiting_rework','waiting_reinspection']
    base=base[cols].sort_values('unit_id').reset_index(drop=True)
    batch_keys=['batch_id','batch_code','produced_at','product_name','shift_id']
    batch_grid=selected.merge(raw['products'][['product_id','name']].rename(columns={'name':'product_name'}),on='product_id')[batch_keys]
    batches=batch_grid.merge(summarize_units(base,['batch_id']),on='batch_id',how='left')
    shifts=raw['shifts'].rename(columns={'name':'shift_name'}).merge(summarize_units(base,['shift_id']),on='shift_id',how='left')
    for f in [batches,shifts]:
        for col in ['unit_count',*COUNTS]:f[col]=pd.to_numeric(f[col]).fillna(0).astype('int64')
    batches=rates(batches);shifts=rates(shifts);shifts['chart_eligible']=shifts.initial_inspected>=100
    observed=base[base.initial_at.notna()].copy();observed['date']=observed.initial_at.astype('string').str[:10]
    summary=observed.groupby('date',as_index=False).agg(initial_inspected=('unit_id','size'),initial_failed=('initial_failed','sum'),initial_defect_count=('initial_defect_count','sum'))
    daily=pd.DataFrame({'date':pd.date_range(p['start'],p['as_of']).strftime('%Y-%m-%d')}).merge(summary,on='date',how='left')
    for col in ['initial_inspected','initial_failed','initial_defect_count']:daily[col]=pd.to_numeric(daily[col]).fillna(0).astype('int64')
    daily['initial_failure_pct']=daily.initial_failed/daily.initial_inspected.replace(0,np.nan)*100
    d=raw['inspection_defects'].merge(visible,on='inspection_id',validate='many_to_one').merge(base[['unit_id','group_id']],on='unit_id',validate='many_to_one')
    dg=d.groupby(['group_id','inspection_no','defect_type_id'],as_index=False).agg(defect_count=('inspection_id','size'),affected_units=('unit_id','nunique'))
    grid=raw['product_groups'].rename(columns={'name':'group_name'}).merge(pd.DataFrame({'inspection_no':[1,2]}),how='cross').merge(raw['defect_types'].rename(columns={'name':'defect_name'}),how='cross')
    defects=grid.merge(dg,on=['group_id','inspection_no','defect_type_id'],how='left')
    for col in ['defect_count','affected_units']:defects[col]=pd.to_numeric(defects[col]).fillna(0).astype('int64')
    return {'units':base,'daily':daily,'batches':batches,'shifts':shifts,'defects':defects}
def compare(db,start='2026-01-01',end=None,as_of='2026-03-31'):
    q=validate(db);sql=sql_tables(db,start,end,as_of);pan=pandas_tables(db,start,end,as_of)
    keys={'units':['unit_id'],'daily':['date'],'batches':['batch_id'],'shifts':['shift_id'],'defects':['group_id','inspection_no','defect_type_id']}
    for name,sort in keys.items():
        a=sql[name].sort_values(sort).reset_index(drop=True);b=pan[name].reindex(columns=a.columns).sort_values(sort).reset_index(drop=True)
        if a.shape!=b.shape:raise ValueError('SQL/pandas khác số dòng: '+name)
        for col in a:
            if col.endswith('_pct'):
                if not np.allclose(pd.to_numeric(a[col]).astype(float),pd.to_numeric(b[col]).astype(float),atol=1e-8,rtol=0,equal_nan=True):raise ValueError('SQL/pandas khác '+name+'.'+col)
            elif not ((a[col]==b[col])|(a[col].isna()&b[col].isna())).all():raise ValueError('SQL/pandas khác '+name+'.'+col)
    if len(sql['units']) and not (sql['units'][STATES].sum(axis=1)==1).all():raise ValueError('Trạng thái đơn vị không phân hoạch đúng')
    sql['quality']=q;return sql
