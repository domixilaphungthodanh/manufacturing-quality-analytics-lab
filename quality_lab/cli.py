import argparse
import pandas as pd
from .db import connect,DEFAULT_DB
from .analysis import scope,sql_tables
from .validation import validate
from .analyze import export
def pages(frame):
    if frame.empty:print('Không có kết quả.');return
    for start in range(0,len(frame),20):
        print(frame.iloc[start:start+20].to_string(index=False))
        if start+20<len(frame) and input('Enter trang tiếp; q quay lại: ').strip().lower()=='q':break
def choose(frame,label,idcol):
    if frame.empty:print('Không có kết quả.');return None
    frame=frame.reset_index(drop=True);page=0
    while True:
        for index,row in frame.iloc[page:page+20].iterrows():print(f'{index+1}. {row[label]}')
        v=input('Chọn số thứ tự; n/p đổi trang; q quay lại: ').strip().lower()
        if v=='q':return None
        if v=='n':page=min(page+20,((len(frame)-1)//20)*20);continue
        if v=='p':page=max(0,page-20);continue
        if not v and len(frame)==1:return int(frame.iloc[0][idcol])
        if v.isdigit() and 1<=int(v)<=len(frame):return int(frame.iloc[int(v)-1][idcol])
        print('Chưa hợp lệ; nhập số thứ tự danh sách, không cần nhớ mã nguồn.')
def ask_scope():
    start=input('Ngày sản xuất từ [2026-01-01], q quay lại: ').strip()
    if start.lower()=='q':return None
    end=input('Ngày sản xuất đến [bằng ngày quan sát]: ').strip();as_of=input('Ngày quan sát [2026-03-31]: ').strip()
    p=scope(start or '2026-01-01',end or None,as_of or '2026-03-31');return p['start'],p['end'],p['as_of']
def main():
    p=argparse.ArgumentParser();p.add_argument('--db',default=str(DEFAULT_DB));a=p.parse_args();validate(a.db)
    while True:
        print('\nKIỂM TRA CHẤT LƯỢNG — GIẢ LẬP\n1. Bộ mẫu và chất lượng\n2. Tìm sản phẩm/lô\n3. Lịch sử một đơn vị\n4. Kiểm tra đầu\n5. Loại lỗi phổ biến\n6. Sửa và kiểm tra lại\n7. Xuất báo cáo\n8. Giải thích chỉ số\n0. Thoát')
        try:
            choice=input('Chọn số menu: ').strip()
            if choice=='0':return
            if choice=='1':
                with connect(a.db) as c:pages(pd.read_sql_query('SELECT * FROM metadata',c))
                pages(validate(a.db))
            elif choice=='2':
                word=input('Tên sản phẩm hoặc mã lô (Enter xem tất cả): ').strip()
                with connect(a.db) as c:frame=pd.read_sql_query('SELECT b.batch_id,b.batch_code,p.name AS product,b.produced_at FROM batches b JOIN products p USING(product_id) WHERE p.name LIKE ? OR b.batch_code LIKE ? ORDER BY b.batch_id',c,params=('%'+word+'%','%'+word+'%'))
                selected=choose(frame,'batch_code','batch_id')
                if selected is not None:
                    with connect(a.db) as c:pages(pd.read_sql_query('SELECT * FROM units WHERE batch_id=? ORDER BY unit_id',c,params=(selected,)))
            elif choice=='3':
                word=input('Mã đơn vị hoặc một phần mã (ví dụ 00001): ').strip()
                with connect(a.db) as c:frame=pd.read_sql_query('SELECT * FROM units WHERE unit_code LIKE ? ORDER BY unit_id',c,params=('%'+word+'%',))
                selected=choose(frame,'unit_code','unit_id')
                if selected is not None:
                    with connect(a.db) as c:
                        pages(pd.read_sql_query("SELECT i.inspection_no,i.inspected_at,COUNT(d.defect_type_id) AS defects,CASE WHEN COUNT(d.defect_type_id)=0 THEN 'Đạt' ELSE 'Chưa đạt' END AS result FROM inspections i LEFT JOIN inspection_defects d USING(inspection_id) WHERE unit_id=? GROUP BY i.inspection_id ORDER BY inspection_no",c,params=(selected,)))
                        pages(pd.read_sql_query('SELECT i.inspection_no,t.name FROM inspections i JOIN inspection_defects d USING(inspection_id) JOIN defect_types t USING(defect_type_id) WHERE i.unit_id=? ORDER BY inspection_no,t.defect_type_id',c,params=(selected,)))
                        pages(pd.read_sql_query('SELECT * FROM reworks WHERE unit_id=?',c,params=(selected,)))
            elif choice in ('4','5','6','7'):
                selected=ask_scope()
                if selected is None:continue
                if choice=='7':export(a.db,*selected)
                else:
                    tables=sql_tables(a.db,*selected)
                    if choice=='4':pages(tables['daily']);pages(tables['batches'])
                    elif choice=='5':pages(tables['defects'].sort_values(['inspection_no','defect_count'],ascending=[True,False]))
                    else:pages(tables['shifts']);pages(tables['units'].query("state in ['waiting_rework','waiting_reinspection','reinspection_passed','reinspection_failed']"))
            elif choice=='8':print('GIẢ LẬP. Một đơn vị có nhiều loại lỗi. Tỷ lệ lỗi lần đầu = số đơn vị lỗi / số đã kiểm tra đầu. Chưa kiểm tra không phải đạt. Chưa kiểm tra lại không phải sửa thất bại. 12 dòng lỗi trên 8 đơn vị khác 12 đơn vị lỗi. Xem docs/metrics.md.')
            else:print('Nhập số 0–8.')
        except (ValueError,OSError) as e:print('Không thực hiện được:',e)
        except (KeyboardInterrupt,EOFError):return
if __name__=='__main__':main()
