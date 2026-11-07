# Manufacturing Quality Analytics Lab

Học SQL qua kiểm tra chất lượng đồ dùng học tập **GIẢ LẬP**, seed 42. Repo Public; mã MIT. Menu chỉ tra cứu, không thu thập dữ liệu nhà máy hoặc nhân viên thật.

## Chạy trên Windows PowerShell

Tải ZIP ở [Releases](https://github.com/domixilaphungthodanh/manufacturing-quality-analytics-lab/releases), giải nén toàn bộ. Mở thư mục dự án bằng File Explorer, gõ `powershell` trên thanh địa chỉ rồi Enter. Cần **Python 3.12** và mạng lần cài thư viện đầu; không cần Git. Đây chưa phải EXE độc lập.

```powershell
Get-Location
Get-ChildItem
python src/prepare_data.py
python src/analyze.py
python run_quality.py --notebook
```

Phải thấy `run_quality.py` và `src`. Nếu đang ở `system32` hoặc thư mục người dùng, dùng `cd "đường dẫn thư mục dự án"` trước. Không dùng `cd /d` trong PowerShell, không sao chép phần `PS ...>`.

Mở **notebooks/02_analysis.ipynb**, Shift+Enter từng ô từ trên xuống. Nếu thấy tab Running trống, chọn Files → notebooks → 02_analysis.ipynb. Giữ PowerShell mở; Ctrl+C để dừng server. Notebook mở trực tiếp bằng `python -m notebook`, với thư mục gốc cố định.

Menu:
```powershell
python run_quality.py
```
Nhập số 0–8 ở menu; chọn kết quả bằng số thứ tự, `n/p` đổi trang, `q` quay lại. Có hai file nhấp đúp START_WINDOWS.cmd và START_NOTEBOOK.cmd. Môi trường Windows nằm ở đường dẫn ngắn trong LOCALAPPDATA; hỗ trợ thư mục có dấu/khoảng trắng, không cần Administrator hoặc tắt bảo mật. Sau cài đầu có thể chạy offline. Dữ liệu giữa các máy không tự đồng bộ.

## Bắt đầu đọc
1. [Từ điển và quan hệ](docs/data_dictionary.md): phân biệt đơn vị, kiểm tra, dòng lỗi và sửa.
2. [Chỉ số và mẫu số](docs/metrics.md): chưa kiểm tra khác đạt; dòng lỗi khác đơn vị lỗi.
3. Notebook tổng hợp: dữ liệu → SQL → pandas → bốn biểu đồ → ba nhận xét.
4. Tám bài trong notebooks/lessons, [20 bài tập](docs/exercises.md), [lời giải riêng](docs/solutions.md).
5. [Bảng tra lệnh](docs/commands.md) và [tự luyện Git](docs/git_practice.md).

## Bộ mẫu đã kiểm tra
Tháng 1–3/2026, giờ **Asia/Ho_Chi_Minh**, cuối mẫu **31/03/2026 23:59:59**. Có 6 nhóm, 18 sản phẩm, 6 loại lỗi, 3 nhãn ca, 120 lô × 100 đơn vị = **12.000 đơn vị**. Kết quả sinh: **11.664 kiểm tra**, gồm **10.608 kiểm tra đầu**, **1.056 kiểm tra lại**, **3.550 dòng lỗi**, **1.308 lượt sửa**. **1.670 đơn vị lỗi lần đầu**. Không có sự kiện sau mốc; giá trị đều giả lập, không đại diện doanh nghiệp thật.

Một đơn vị tối đa hai lần kiểm tra và một lần sửa. Kiểm tra đầu phải sau sản xuất ít nhất một giây; sửa sau kiểm tra đầu lỗi; kiểm tra lại sau sửa ít nhất một giây. Không có dòng lỗi = đạt; có ít nhất một dòng = chưa đạt. Bản đầu chưa sửa lần hai/phế phẩm/chi phí. Ca là nhãn phân loại, chưa mô phỏng lịch ca qua đêm.

## Chọn nhóm và mốc
```powershell
python src/analyze.py --start 2026-01-01 --end 2026-01-31 --as-of 2026-03-31
python src/prepare_data.py --db database/practice.db
python run_quality.py --notebook --db database/practice.db
python src/analyze.py --db database/practice.db --as-of 2026-02-28 --out outputs/february
```
`--start/--end` chọn **ngày sản xuất lô**; giữ sửa/kiểm tra của nhóm đến `--as-of`, không cắt sự kiện tại end. Mốc quan sát là cuối ngày. Mặc định start=01/01, as-of=31/03; end bằng as-of nếu bỏ trống. Chỉ nhận 01/01 ≤ start ≤ end ≤ as-of ≤ 31/03/2026. `--db` chọn SQLite, `--out` chọn kết quả, prepare có `--raw-out` chọn nơi CSV nguồn.

Prepare chỉ tạo khi chưa có DB. Chạy lại kiểm tra và xuất CSV nguồn, giữ DB. Khởi tạo vào DB tạm và kiểm tra trước khi công bố. Database mặc định database/quality.db. Phạm vi rỗng vẫn xuất đủ, không có mẫu số thì tỷ lệ trống.

## Kết quả
4 PNG: tỷ lệ lỗi ngày, số dòng lỗi theo loại, tỷ lệ theo ca đủ >=100 mẫu, heatmap dòng lỗi theo nhóm. Ngày không kiểm tra giữ khoảng trống; không nối đường qua ngày thiếu mẫu số. Heatmap đếm dòng lỗi, không phải tỷ lệ sản phẩm lỗi.

6 CSV: units, daily, batches, shifts, defects, quality. `units` đúng một dòng mỗi đơn vị tại mốc; `defects` tách inspection_no 1/2. Bảng lô/ca có mẫu số, bao phủ, lỗi đầu, đã sửa, chờ sửa, chờ kiểm tra lại và kết quả kiểm tra lại. quality kiểm tra **toàn DB**; năm bảng khác theo nhóm/mốc. report.md có ba nhận xét, mẫu số và giới hạn. SQL/pandas tính độc lập, số đếm khớp chính xác; tỷ lệ sai số tối đa 1e-8.

```text
src/             Chuẩn bị và phân tích
quality_lab/     Mẫu, kiểm tra, SQL/pandas, menu, báo cáo
sql/             Schema và SQL mẫu
notebooks/       02_analysis.ipynb + 8 bài SQL
docs/            Sơ đồ, từ điển, bài tập, lời giải
tests/           Fixture nhỏ, ghi rõ giả lập
data/raw/        CSV sinh ra; không Git/ZIP
database/        SQLite; không Git/ZIP
outputs/         Báo cáo; không Git/ZIP
```

## Cài thủ công và kiểm thử
```powershell
python -m pip install -r requirements.txt
python -m quality_lab.prepare_data
python -m quality_lab.cli
python -m quality_lab.analyze
python -m notebook
python -m unittest discover -s tests -v
python -m quality_lab.execute_notebooks
```
Notebook phân tích mở DB chỉ đọc; bài INSERT/rollback dùng SQLite tạm. Actions kiểm thử Windows/Linux, workflow thủ công tạo mẫu/phân tích/9 notebook, artifact 14 ngày. ZIP không chứa DB, CSV sinh ra, môi trường hoặc notebook đã chạy.

Không gọi chưa kiểm tra là đạt; không gọi chưa kiểm tra lại là sửa thất bại. Không suy ca gây lỗi hoặc kết quả mô tả chứng minh tác động sửa chữa. Không dùng mẫu giả lập để đánh giá nhà máy/nhân viên thật.
