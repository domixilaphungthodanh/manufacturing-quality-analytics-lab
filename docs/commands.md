# Tra lệnh
| Lệnh | Ý nghĩa |
|---|---|
| Get-Location | PowerShell: xem thư mục hiện tại |
| Get-ChildItem | PowerShell: liệt kê file, phải thấy run_quality.py |
| cd "đường dẫn" | PowerShell: đổi thư mục, không dùng /d |
| python -m ... | Chạy một module Python |
| python src/prepare_data.py | Tạo mẫu nếu chưa có DB, kiểm tra và xuất CSV |
| python src/analyze.py | Đối chiếu và xuất báo cáo |
| python run_quality.py --notebook | Mở đúng bài tổng hợp |
| 0–8 | Chỉ nhập ở menu |
| SELECT ... | Đặt trong chuỗi Python của read_sql ở notebook |

SELECT chọn cột; FROM chọn bảng; JOIN/ON nối đúng khóa; WHERE lọc dòng; GROUP BY gom nhóm; HAVING lọc nhóm; COUNT DISTINCT đếm không trùng; CASE phân loại; CTE tách bước; ROW_NUMBER xếp thứ tự trong nhóm. NULL khác 0. COMMIT lưu toàn thao tác, ROLLBACK hủy khi lỗi.
