"""Entire dataset is SIMULATED for SQL learning, with a fixed seed."""
import random
from datetime import datetime,timedelta
START=datetime(2026,1,1);END=datetime(2026,3,31,23,59,59)
TABLES=['product_groups','products','shifts','batches','units','defect_types','inspections','inspection_defects','reworks']
def generate(seed=42):
    rng=random.Random(seed);data={t:[] for t in TABLES}
    groups=['Bút','Vở','Thước','Hộp bút','Kẹp giấy','Bìa hồ sơ']
    data['product_groups']=[(i,name+' — giả lập') for i,name in enumerate(groups,1)]
    data['products']=[(i,(i-1)//3+1,f'{groups[(i-1)//3]} mẫu {i:02d}') for i in range(1,19)]
    data['shifts']=[(i,f'Ca {i} — nhãn giả lập') for i in range(1,4)]
    data['defect_types']=[(i,n) for i,n in enumerate(['Trầy xước','Sai kích thước','Lệch màu','Thiếu chi tiết','Biến dạng','Lỗi đóng gói'],1)]
    fmt=lambda d:d.strftime('%Y-%m-%d %H:%M:%S')
    for batch in range(1,121):
        day=(batch-1)*89//119;produced=START+timedelta(days=day,hours=8)
        product=(batch-1)%18+1;shift=rng.randint(1,3)
        data['batches'].append((batch,f'LOT-{batch:03d}',product,shift,fmt(produced)))
        for pos in range(1,101):
            uid=len(data['units'])+1;data['units'].append((uid,f'UNIT-{uid:05d}',batch))
            if rng.random()<.11:continue
            first=produced+timedelta(hours=rng.randint(1,48),seconds=pos)
            if first>END:continue
            iid=len(data['inspections'])+1;data['inspections'].append((iid,uid,1,fmt(first)))
            failed=rng.random()<(.08+.025*shift+.01*((product-1)//3))
            if not failed:continue
            for defect in rng.sample(range(1,7),rng.randint(1,3)):data['inspection_defects'].append((iid,defect))
            if rng.random()<.2:continue
            repaired=first+timedelta(hours=rng.randint(1,96))
            if repaired>END:continue
            data['reworks'].append((len(data['reworks'])+1,uid,fmt(repaired)))
            if rng.random()<.18:continue
            second=repaired+timedelta(hours=rng.randint(1,72))
            if second>END:continue
            iid=len(data['inspections'])+1;data['inspections'].append((iid,uid,2,fmt(second)))
            if rng.random()<.18:
                for defect in rng.sample(range(1,7),rng.randint(1,2)):data['inspection_defects'].append((iid,defect))
    return data
