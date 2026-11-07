# Lời giải — đọc sau khi tự làm

Các truy vấn ngắn dưới đây mặc định toàn DB; để báo cáo lịch sử phải dùng scope/UNIT_SQL và cắt sự kiện theo mốc như buổi 6.

## 1. Xem 10 đơn vị

```sql
SELECT * FROM units ORDER BY unit_id LIMIT 10;
```

## 2. Lọc lô tháng 2

```sql
SELECT batch_code,produced_at FROM batches WHERE produced_at>='2026-02-01' AND produced_at<'2026-03-01' ORDER BY produced_at,batch_id LIMIT 10;
```

## 3. Xem kiểm tra lại

```sql
SELECT * FROM inspections WHERE inspection_no=2 ORDER BY inspected_at,inspection_id LIMIT 10;
```

## 4. JOIN tên sản phẩm và lỗi

```sql
SELECT u.unit_code,p.name AS product,i.inspection_no,t.name AS defect FROM inspection_defects d JOIN inspections i USING(inspection_id) JOIN units u USING(unit_id) JOIN batches b USING(batch_id) JOIN products p USING(product_id) JOIN defect_types t USING(defect_type_id) LIMIT 20;
```

## 5. Dòng lỗi khác đơn vị lỗi

```sql
SELECT i.inspection_no,COUNT(*) AS defect_records,COUNT(DISTINCT i.unit_id) AS defective_units FROM inspections i JOIN inspection_defects d USING(inspection_id) GROUP BY i.inspection_no;
```

## 6. Mẫu số tất cả kiểm tra đầu

```sql
SELECT inspection_no,COUNT(*) AS all_inspected FROM inspections GROUP BY inspection_no;
```

## 7. Tìm đơn vị chưa kiểm tra

```sql
SELECT u.unit_code FROM units u WHERE NOT EXISTS(SELECT 1 FROM inspections i WHERE i.unit_id=u.unit_id AND i.inspection_no=1) LIMIT 20;
```

## 8. Giữ đơn vị chưa kiểm tra bằng LEFT JOIN

```sql
SELECT u.unit_code,i.inspected_at FROM units u LEFT JOIN inspections i ON i.unit_id=u.unit_id AND i.inspection_no=1 ORDER BY u.unit_id LIMIT 20;
```

## 9. Lô có ít nhất 100 đã kiểm tra

```sql
SELECT u.batch_id,COUNT(*) AS n FROM units u JOIN inspections i USING(unit_id) WHERE i.inspection_no=1 GROUP BY u.batch_id HAVING COUNT(*)>=100;
```

## 10. Lỗi phổ biến lần đầu

```sql
SELECT t.name,COUNT(*) AS n FROM inspection_defects d JOIN inspections i USING(inspection_id) JOIN defect_types t USING(defect_type_id) WHERE i.inspection_no=1 GROUP BY t.defect_type_id ORDER BY n DESC;
```

## 11. Một dòng mỗi đơn vị tại mốc

```sql
-- Chạy UNIT_SQL với scope từ quality_lab.analysis; kiểm tra unit_id duy nhất.
```

## 12. Tỷ lệ lỗi với mẫu số đúng

```sql
WITH failed AS (SELECT DISTINCT i.unit_id FROM inspections i JOIN inspection_defects d USING(inspection_id) WHERE inspection_no=1) SELECT (SELECT COUNT(*) FROM failed)*100.0/NULLIF(COUNT(*),0) AS failure_pct FROM inspections WHERE inspection_no=1;
```

## 13. Chưa sửa

```sql
SELECT DISTINCT i.unit_id FROM inspections i JOIN inspection_defects d USING(inspection_id) WHERE inspection_no=1 AND NOT EXISTS(SELECT 1 FROM reworks r WHERE r.unit_id=i.unit_id);
```

## 14. Sửa xong chờ kiểm tra lại

```sql
SELECT r.unit_id FROM reworks r WHERE NOT EXISTS(SELECT 1 FROM inspections i WHERE i.unit_id=r.unit_id AND i.inspection_no=2);
```

## 15. Kết quả lần 2

```sql
SELECT i.inspection_id,i.unit_id,CASE WHEN COUNT(d.defect_type_id)=0 THEN 'passed' ELSE 'failed' END AS result FROM inspections i LEFT JOIN inspection_defects d USING(inspection_id) WHERE i.inspection_no=2 GROUP BY i.inspection_id;
```

## 16. Ngày trước/kiểm tra trước

```sql
SELECT unit_id,inspection_no,inspected_at,LAG(inspected_at) OVER(PARTITION BY unit_id ORDER BY inspection_no) AS previous_inspection FROM inspections ORDER BY unit_id,inspection_no LIMIT 20;
```

## 17. 100 sản phẩm, 8 lỗi, 12 dòng

```sql
-- Chạy fixture SQLite tạm trong notebook buổi 4: COUNT(*)=12, COUNT(DISTINCT unit_id)=8, tỷ lệ=8/100.
```

## 18. Thử rollback

```sql
-- Notebook buổi 7: gây trùng loại lỗi, kiểm tra cả inspections và defects đều về 0.
```

## 19. Đối chiếu pandas

```sql
-- compare(db,start=...,end=...,as_of=...) đọc bảng nguồn và tự tổng hợp; không đọc bảng SQL làm dữ liệu pandas.
```

## 20. Ba nhận xét

```sql
-- Ghi nhóm lô, mốc, tử số/mẫu số và giới hạn; chưa kiểm tra không phải đạt, chưa kiểm tra lại không phải sửa thất bại.
```