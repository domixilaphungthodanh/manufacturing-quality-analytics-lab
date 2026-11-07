# Chỉ số và mẫu số
Nhóm lô theo ngày produced_at, chỉ sự kiện <= cuối ngày as_of. Ngày đầu/đến chọn lô, không cắt sự kiện sau end thuộc nhóm đã chọn. Ba ca là nhãn **sản xuất**, không phải ca kiểm tra. Không suy nhân quả theo ca.

- Bao phủ = initial_inspected / unit_count.
- Lỗi đầu = initial_failed / initial_inspected; mỗi đơn vị tính một lần.
- Dòng lỗi đầu = tổng loại lỗi xuất hiện ở lần 1, có thể nhiều hơn số đơn vị lỗi.
- Đạt kiểm tra lại = reinspection_passed / reinspected. Luôn kèm initial_failed, reworked, waiting_rework và waiting_reinspection.
- Không mẫu số giữ NULL; đủ mẫu không lỗi là 0%, khác chưa kiểm tra.

Ví dụ **100 đã kiểm tra, 8 đơn vị lỗi, 12 dòng lỗi** => lỗi đầu 8%. Không cộng lỗi lần 2 vào tử số lần 1. Tỷ lệ kiểm tra lại chỉ mô tả nhóm đã kiểm tra lại, không chứng minh tác động sửa chữa.

Phân loại tại mốc: không kiểm tra đầu→not_inspected; đầu không lỗi→initial_passed; đầu lỗi chưa sửa→waiting_rework; đã sửa chưa kiểm tra lại→waiting_reinspection; đã kiểm tra lại thì kết quả theo lỗi lần 2. Lỗi lần 2 không xóa lịch sử lần 1.

Các mốc cùng đơn vị tăng tối thiểu một giây: sản xuất < kiểm tra đầu < sửa < kiểm tra lại. Chỉ đầu lỗi mới sửa; tối đa một sửa, hai kiểm tra. Quy tắc kiểm tra đầu **sau** sản xuất được chọn để thống nhất tăng nghiêm ngặt. Đây là mô hình học tập, không phải tiêu chuẩn vận hành nhà máy.

Biểu đồ ngày theo ngày kiểm tra đầu, lịch start→as_of. Không kiểm tra thì rate trống và đường bị ngắt. Ca xếp hình khi >=100 đã kiểm tra đầu, không phải >=100 đơn vị sản xuất. Các CSV giữ nhóm nhỏ. Heatmap là dòng lỗi theo nhóm, không gọi là tỷ lệ. quality kiểm tra toàn DB, báo cáo khác theo nhóm/mốc.
