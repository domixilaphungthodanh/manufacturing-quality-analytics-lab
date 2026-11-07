import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from .db import ROOT,DEFAULT_DB
from .analysis import scope,compare
def export(db=DEFAULT_DB,start='2026-01-01',end=None,as_of='2026-03-31',out=None):
    p=scope(start,end,as_of);tables=compare(db,start,end,as_of)
    out=Path(out or ROOT/'outputs');out.mkdir(parents=True,exist_ok=True)
    for name,frame in tables.items():frame.to_csv(out/(name+'.csv'),index=False,encoding='utf-8-sig')
    sns.set_theme(style='whitegrid');foot=f'SIMULATED seed 42 | Batch production: {p["start"]} to {p["end"]} | As of {as_of}, Asia/Ho_Chi_Minh'
    def save(name,draw,empty=False,size=(11,6)):
        fig,ax=plt.subplots(figsize=size)
        if empty:ax.text(.5,.5,'No eligible observations',ha='center',transform=ax.transAxes);ax.set_axis_off()
        else:draw(ax)
        fig.text(.02,.015,foot,fontsize=8);fig.tight_layout(rect=(0,.055,1,1));fig.savefig(out/name,dpi=140);plt.close(fig)
    daily=tables['daily'];defects=tables['defects'];shifts=tables['shifts'];units=tables['units']
    def line(ax):
        # Matplotlib keeps NaN gaps; Seaborn aggregation would drop and connect them.
        ax.plot(pd.to_datetime(daily.date),daily.initial_failure_pct,color=sns.color_palette()[0]);ax.set(xlabel='Initial inspection date',ylabel='Initially defective units (%)');ax.tick_params(axis='x',rotation=30)
    save('01_daily_failure.png',line,daily.initial_inspected.sum()==0)
    first=defects[defects.inspection_no==1];counts=first.groupby('defect_name',as_index=False).defect_count.sum().sort_values('defect_count',ascending=False)
    def bars(ax):
        sns.barplot(data=counts,x='defect_count',y='defect_name',color='#268c8f',ax=ax)
        for container in ax.containers:ax.bar_label(container,padding=3)
        ax.set(xlabel='Initial defect-type records (not defective units)',ylabel='SIMULATED defect type')
    save('02_defect_types.png',bars,counts.defect_count.sum()==0)
    eligible=shifts[shifts.chart_eligible]
    def shift_chart(ax):
        sns.barplot(data=eligible,x='shift_name',y='initial_failure_pct',color='#507bb1',ax=ax);ax.set(xlabel='Production shift label (SIMULATED)',ylabel='Initially defective units (%)',ylim=(0,100))
        for i,row in enumerate(eligible.itertuples()):ax.text(i,row.initial_failure_pct+2,f'{row.initial_failed}/{row.initial_inspected}',ha='center',fontsize=9)
        ax.set_title('At least 100 initially inspected units; denominator shown')
    save('03_shift_failure.png',shift_chart,eligible.empty)
    def heat(ax):
        grid=first.pivot(index='group_name',columns='defect_name',values='defect_count')
        sns.heatmap(grid,annot=True,fmt='d',cmap='YlOrRd',ax=ax,cbar_kws={'label':'Initial defect-type records'});ax.set(xlabel='Defect type',ylabel='Product group');ax.tick_params(axis='x',rotation=25)
    save('04_defect_heatmap.png',heat,first.defect_count.sum()==0,size=(12,7))
    n=len(units);inspected=int(units.initial_inspected.sum());failed=int(units.initial_failed.sum());defect_n=int(units.initial_defect_count.sum());reworked=int(units.reworked.sum());again=int(units.reinspected.sum());passed=int(units.reinspection_passed.sum());waiting_rework=int(units.waiting_rework.sum());waiting_reinspection=int(units.waiting_reinspection.sum())
    insights=[f'Nhóm có {n:,} đơn vị; {inspected:,} đã kiểm tra đầu. Độ bao phủ '+(f'{inspected/n*100:.2f}%.' if n else 'chưa xác định do mẫu số 0.'),f'Có {failed:,}/{inspected:,} đơn vị lỗi lần đầu'+(f' ({failed/inspected*100:.2f}%)' if inspected else ' (tỷ lệ chưa xác định)')+f', nhưng có {defect_n:,} dòng loại lỗi. Một đơn vị có thể nhiều lỗi.',f'Trong {failed:,} đơn vị lỗi ban đầu: {reworked:,} đã sửa, {again:,} đã kiểm tra lại; {passed:,} đạt'+(f'/{again:,} = {passed/again*100:.2f}%.' if again else '; tỷ lệ đạt kiểm tra lại chưa xác định.')+f' Còn {waiting_rework:,} chờ sửa và {waiting_reinspection:,} chờ kiểm tra lại.']
    text='# Manufacturing Quality Analytics — GIẢ LẬP\n\n'+foot+'\n\n'+'\n\n'.join(f'{i}. {s}' for i,s in enumerate(insights,1))
    text+='\n\n## Cách đọc và giới hạn\n\nNhóm chọn theo ngày sản xuất lô, giữ mọi kiểm tra và sửa của nhóm đến mốc. Không nhìn sự kiện sau mốc. Tỷ lệ lỗi = đơn vị lỗi / đơn vị đã kiểm tra lần đầu; không chia dòng lỗi cho số sản phẩm. Không có mẫu số giữ trống, không gán 0. Chưa kiểm tra không coi là đạt; chưa kiểm tra lại không coi là sửa thất bại.\n\nKết quả kiểm tra lại chỉ mô tả đơn vị đã được kiểm tra lại, luôn kèm số lỗi ban đầu, đã sửa, đang chờ; không chứng minh tác động nhân quả của sửa chữa. Không suy ca sản xuất gây lỗi từ thống kê mô tả; ba ca chỉ là nhãn giả lập. Một tháng/nhóm giả lập không đại diện nhà máy thật hoặc năng lực nhân viên. Chưa có phế phẩm, sửa lần hai, chi phí hoặc lợi nhuận.\n\nSQL/pandas đã đối chiếu độc lập. quality.csv kiểm tra toàn database; năm bảng còn lại theo nhóm/mốc. Bốn hình gồm tỷ lệ lỗi ngày, dòng lỗi theo loại, tỷ lệ theo ca đủ mẫu và heatmap dòng lỗi lần đầu. Ngày không kiểm tra giữ khoảng trống; ngưỡng 100 là quy tắc thực hành.\n'
    (out/'report.md').write_text(text,encoding='utf-8');print('GIẢ LẬP: SQL/pandas khớp; đã xuất 4 PNG, 6 CSV, report.md:',out);return tables
def main():
    p=argparse.ArgumentParser();p.add_argument('--db',default=str(DEFAULT_DB));p.add_argument('--start',default='2026-01-01');p.add_argument('--end');p.add_argument('--as-of',default='2026-03-31');p.add_argument('--out');a=p.parse_args();export(a.db,a.start,a.end,a.as_of,a.out)
if __name__=='__main__':main()
