"""All fixtures are SIMULATED; no claims about a real manufacturer."""
import contextlib,copy,io,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from quality_lab.sample import generate
from quality_lab.db import connect
from quality_lab.prepare_data import create,prepare
from quality_lab.validation import validate
from quality_lab.analysis import compare,scope,STATES
from quality_lab.analyze import export

def fixture():
    return {'product_groups':[(1,'Nhóm mẫu 1'),(2,'Nhóm mẫu 2')],
        'products':[(1,1,'Sản phẩm mẫu 1'),(2,2,'Sản phẩm mẫu 2')],
        'shifts':[(1,'Ca mẫu 1'),(2,'Ca mẫu 2'),(3,'Ca mẫu 3')],
        'batches':[(1,'LOT-001',1,1,'2026-01-01 08:00:00'),(2,'LOT-002',2,2,'2026-01-02 08:00:00')],
        'units':[(i,f'UNIT-{i:05d}',1 if i<=100 else 2) for i in range(1,102)],
        'defect_types':[(1,'Trầy mẫu'),(2,'Màu mẫu'),(3,'Kích thước mẫu')],
        'inspections':[(i,i,1,'2026-01-01 10:00:00') for i in range(1,101)]+[(101,1,2,'2026-01-03 10:00:00'),(102,2,2,'2026-01-03 10:00:00'),(103,4,2,'2026-03-31 23:59:59')],
        'inspection_defects':[(i,1) for i in range(1,9)]+[(i,2) for i in range(1,5)]+[(102,1)],
        'reworks':[(i,i,'2026-01-02 10:00:00') for i in range(1,5)]}

class Lab(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.db=self.root/'quality.db';create(self.db,data=fixture())
    def tearDown(self):self.temp.cleanup()
    def t(self,**kwargs):return compare(self.db,**kwargs)
    def invalid(self,change):
        data=fixture();change(data);target=self.root/'invalid.db'
        with self.assertRaises((sqlite3.IntegrityError,ValueError)):create(target,data=data)
        self.assertFalse(target.exists())
    def test_all_tables_reconcile(self):self.assertEqual(set(self.t()),{'units','daily','batches','shifts','defects','quality'})
    def test_8_units_12_defects(self):
        t=self.t();self.assertEqual(t['units'].initial_failed.sum(),8);self.assertEqual(t['units'].initial_defect_count.sum(),12);self.assertEqual(t['daily'].initial_inspected.sum(),100);self.assertEqual(t['shifts'].set_index('shift_id').loc[1,'initial_failure_pct'],8)
    def test_one_row_per_unit(self):self.assertEqual(len(self.t()['units']),101);self.assertFalse(self.t()['units'].unit_id.duplicated().any())
    def test_pass_no_defect(self):self.assertEqual(self.t()['units'].query('unit_id==9').state.iloc[0],'initial_passed')
    def test_uninspected_not_pass(self):
        u=self.t()['units'].query('unit_id==101').iloc[0];self.assertEqual(u.state,'not_inspected');self.assertEqual(u.initial_passed,0)
    def test_waiting_rework(self):self.assertEqual(self.t()['units'].query('unit_id==8').state.iloc[0],'waiting_rework')
    def test_waiting_reinspection(self):self.assertEqual(self.t()['units'].query('unit_id==3').state.iloc[0],'waiting_reinspection')
    def test_reinspection_pass(self):self.assertEqual(self.t()['units'].query('unit_id==1').state.iloc[0],'reinspection_passed')
    def test_reinspection_fail(self):self.assertEqual(self.t()['units'].query('unit_id==2').state.iloc[0],'reinspection_failed')
    def test_reinspection_denominator(self):
        s=self.t()['shifts'].set_index('shift_id').loc[1];self.assertEqual(s.reinspected,3);self.assertEqual(s.reworked,4);self.assertEqual(s.initial_failed,8);self.assertAlmostEqual(s.reinspection_pass_pct,2/3*100)
    def test_counts_partition(self):
        t=self.t();self.assertTrue((t['units'][STATES].sum(axis=1)==1).all());self.assertEqual(t['shifts'][STATES].sum().sum(),101);self.assertEqual(t['batches'][STATES].sum().sum(),101)
    def test_coverage(self):self.assertEqual(self.t()['batches'].set_index('batch_id').loc[2,'coverage_pct'],0)
    def test_no_inspection_denominator(self):self.assertTrue(pd.isna(self.t()['batches'].set_index('batch_id').loc[2,'initial_failure_pct']))
    def test_no_reinspection_denominator(self):self.assertTrue(pd.isna(self.t(as_of='2026-01-02')['shifts'].set_index('shift_id').loc[1,'reinspection_pass_pct']))
    def test_history_before_repair(self):
        u=self.t(as_of='2026-01-01')['units'].query('unit_id==1').iloc[0];self.assertEqual(u.state,'waiting_rework');self.assertTrue(pd.isna(u.rework_at));self.assertTrue(pd.isna(u.reinspection_at))
    def test_history_after_repair(self):self.assertEqual(self.t(as_of='2026-01-02')['units'].query('unit_id==1').state.iloc[0],'waiting_reinspection')
    def test_history_after_first_reinspection(self):self.assertEqual(self.t(as_of='2026-01-03')['units'].query('unit_id==1').state.iloc[0],'reinspection_passed')
    def test_end_does_not_cut_events(self):self.assertEqual(self.t(end='2026-01-01')['units'].query('unit_id==4').state.iloc[0],'reinspection_passed')
    def test_cutoff_exact_end(self):self.assertEqual(self.t(as_of='2026-03-30')['units'].query('unit_id==4').state.iloc[0],'waiting_reinspection');self.assertEqual(self.t()['units'].query('unit_id==4').state.iloc[0],'reinspection_passed')
    def test_future_batch_excluded(self):self.assertEqual(len(self.t(as_of='2026-01-01')['units']),100)
    def test_zero_day_is_missing_rate(self):
        r=self.t()['daily'].set_index('date').loc['2026-01-02'];self.assertEqual(r.initial_inspected,0);self.assertTrue(pd.isna(r.initial_failure_pct))
    def test_defects_rounds_separate(self):
        d=self.t()['defects'];self.assertEqual(d.query('inspection_no==1').defect_count.sum(),12);self.assertEqual(d.query('inspection_no==2').defect_count.sum(),1)
    def test_keep_empty_groups(self):self.assertEqual(len(self.t()['defects']),2*2*3);self.assertEqual(len(self.t()['shifts']),3)
    def test_threshold100(self):self.assertTrue(self.t()['shifts'].set_index('shift_id').loc[1,'chart_eligible'])
    def test_threshold99(self):
        data=fixture();data['inspections']=[r for r in data['inspections'] if r[0]!=100];target=self.root/'small.db';create(target,data=data);s=compare(target)['shifts'].set_index('shift_id');self.assertEqual(s.loc[1,'initial_inspected'],99);self.assertFalse(s.loc[1,'chart_eligible'])
    def test_readonly(self):
        with connect(self.db) as c,self.assertRaises(sqlite3.OperationalError):c.execute('DELETE FROM inspections')
    def test_foreign_key(self):
        with connect(self.db,False) as c,self.assertRaises(sqlite3.IntegrityError):c.execute("INSERT INTO inspections VALUES(999,999,1,'2026-01-01 10:00:00')")
    def test_duplicate_defect(self):self.invalid(lambda d:d['inspection_defects'].append((1,1)))
    def test_third_inspection(self):self.invalid(lambda d:d['inspections'].append((999,1,3,'2026-01-04 10:00:00')))
    def test_second_repair(self):self.invalid(lambda d:d['reworks'].append((999,1,'2026-01-04 10:00:00')))
    def test_duplicate_initial(self):self.invalid(lambda d:d['inspections'].append((999,1,1,'2026-01-04 10:00:00')))
    def test_initial_before_production(self):self.invalid(lambda d:d['inspections'].__setitem__(0,(1,1,1,'2026-01-01 07:59:59')))
    def test_initial_equal_production(self):self.invalid(lambda d:d['inspections'].__setitem__(0,(1,1,1,'2026-01-01 08:00:00')))
    def test_initial_one_second_after(self):
        data=fixture();data['inspections'][0]=(1,1,1,'2026-01-01 08:00:01');create(self.root/'one-second.db',data=data)
    def test_repair_before_initial(self):self.invalid(lambda d:d['reworks'].__setitem__(0,(1,1,'2026-01-01 09:59:59')))
    def test_repair_equal_initial(self):self.invalid(lambda d:d['reworks'].__setitem__(0,(1,1,'2026-01-01 10:00:00')))
    def test_repair_passed_unit(self):self.invalid(lambda d:d['reworks'].append((999,9,'2026-01-02 10:00:00')))
    def test_repair_uninspected_unit(self):self.invalid(lambda d:d['reworks'].append((999,101,'2026-01-02 10:00:00')))
    def test_reinspection_without_repair(self):self.invalid(lambda d:d['inspections'].append((999,8,2,'2026-01-03 10:00:00')))
    def test_reinspection_equal_repair(self):self.invalid(lambda d:d['inspections'].__setitem__(100,(101,1,2,'2026-01-02 10:00:00')))
    def test_bad_date(self):self.invalid(lambda d:d['inspections'].__setitem__(0,(1,1,1,'2026-02-30 10:00:00')))
    def test_bad_date_format(self):self.invalid(lambda d:d['inspections'].__setitem__(0,(1,1,1,'2026-1-01 10:00:00')))
    def test_future_event(self):self.invalid(lambda d:d['inspections'].__setitem__(100,(101,1,2,'2026-04-01 10:00:00')))
    def test_missing_defect_type(self):self.invalid(lambda d:d['inspection_defects'].append((1,999)))
    def test_missing_inspection(self):self.invalid(lambda d:d['inspection_defects'].append((999,1)))
    def test_no_overwrite(self):
        before=self.db.read_bytes()
        with self.assertRaises(FileExistsError):create(self.db)
        self.assertEqual(before,self.db.read_bytes())
    def test_prepare_preserves_exports(self):
        before=self.db.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):prepare(self.db,self.root/'raw')
        self.assertEqual(before,self.db.read_bytes());self.assertEqual(len(list((self.root/'raw').glob('*.csv'))),10)
    def test_atomic_publish_failure(self):
        target=self.root/'failed.db'
        with patch('quality_lab.prepare_data.os.link',side_effect=OSError('simulated failure')),self.assertRaises(OSError):create(target,data=fixture())
        self.assertFalse(target.exists());self.assertEqual(list(self.root.glob('tmp*.db')),[])
    def test_transaction_inspection_defects_rollback(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with connect(self.db,False) as c:
                c.execute("INSERT INTO inspections VALUES(999,101,1,'2026-01-02 10:00:00')")
                c.execute('INSERT INTO inspection_defects VALUES(999,1)')
                c.execute('INSERT INTO inspection_defects VALUES(999,1)')
        with connect(self.db) as c:
            self.assertIsNone(c.execute('SELECT * FROM inspections WHERE inspection_id=999').fetchone());self.assertIsNone(c.execute('SELECT * FROM inspection_defects WHERE inspection_id=999').fetchone())
    def test_wrong_metadata_stops_before_output(self):
        with connect(self.db,False) as c:c.execute("UPDATE metadata SET value='real' WHERE key='data_kind'")
        with self.assertRaises(ValueError):export(self.db,out=self.root/'bad')
        self.assertFalse((self.root/'bad').exists())
    def test_empty_scope_exports(self):
        t=export(self.db,start='2026-02-01',end='2026-02-02',out=self.root/'out');self.assertEqual(len(t['units']),0);self.assertEqual(len(list((self.root/'out').glob('*.png'))),4);self.assertEqual(len(list((self.root/'out').glob('*.csv'))),6)
    def test_no_inspections_exports(self):
        data=fixture();data['inspections']=[];data['inspection_defects']=[];data['reworks']=[];target=self.root/'none.db';create(target,data=data);t=export(target,out=self.root/'none-out');self.assertEqual(t['units'].not_inspected.sum(),101);self.assertTrue(t['shifts'].initial_failure_pct.isna().all())
    def test_empty_db(self):
        data=fixture()
        for k in ['batches','units','inspections','inspection_defects','reworks']:data[k]=[]
        target=self.root/'empty.db';create(target,data=data);t=compare(target);self.assertEqual(len(t['units']),0)
    def test_ranges(self):
        for a,b,c in [('2026-01-02','2026-01-01','2026-03-31'),('2026-01-01','2026-03-31','2026-02-01'),('2025-12-31','2026-01-01','2026-03-31'),('2026-01-01','2026-01-01','2026-04-01')]:
            with self.subTest(a=a,b=b,c=c),self.assertRaises(ValueError):scope(a,b,c)
    def test_menu_retry(self):
        from quality_lab.cli import choose
        frame=pd.DataFrame({'unit_id':[1],'unit_code':['UNIT-00001']})
        with patch('builtins.input',side_effect=['bad','999','1']),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(choose(frame,'unit_code','unit_id'),1)
    def test_menu_quit(self):
        from quality_lab.cli import choose
        with patch('builtins.input',return_value='q'),contextlib.redirect_stdout(io.StringIO()):self.assertIsNone(choose(pd.DataFrame({'unit_id':[1],'unit_code':['A']}),'unit_code','unit_id'))

class Sample(unittest.TestCase):
    def test_seed_reproducible(self):self.assertEqual(generate(),generate())
    def test_seed_changes(self):self.assertNotEqual(generate(42),generate(43))
    def test_exact_dimensions(self):
        d=generate();self.assertEqual([len(d[k]) for k in ['product_groups','products','shifts','batches','units','defect_types']],[6,18,3,120,12000,6]);self.assertTrue(all(sum(u[2]==b[0] for u in d['units'])==100 for b in d['batches']))
    def test_realized_counts(self):
        d=generate();self.assertEqual(len(d['inspections']),11664);self.assertEqual(len(d['inspection_defects']),3550);self.assertEqual(len(d['reworks']),1308)

if __name__=='__main__':unittest.main()
