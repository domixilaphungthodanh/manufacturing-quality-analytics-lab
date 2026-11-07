-- Các truy vấn học cơ bản toàn DB; báo cáo lịch sử dùng quality_lab.analysis.UNIT_SQL có tham số mốc.

-- Bảng, dòng và khóa
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;

-- Lọc lô và kiểm tra
SELECT batch_code,produced_at FROM batches WHERE produced_at>='2026-02-01' AND produced_at<'2026-03-01' ORDER BY produced_at,batch_id LIMIT 10;

-- JOIN một–nhiều
SELECT u.unit_code,p.name AS product,i.inspection_no,t.name AS defect FROM inspection_defects d JOIN inspections i USING(inspection_id) JOIN units u USING(unit_id) JOIN batches b USING(batch_id) JOIN products p USING(product_id) JOIN defect_types t USING(defect_type_id) LIMIT 20;

-- Đếm sản phẩm lỗi
SELECT i.inspection_no,COUNT(*) AS defect_records,COUNT(DISTINCT i.unit_id) AS defective_units FROM inspections i JOIN inspection_defects d USING(inspection_id) GROUP BY i.inspection_no;

-- LEFT JOIN, NOT EXISTS và NULL
SELECT u.unit_code FROM units u WHERE NOT EXISTS(SELECT 1 FROM inspections i WHERE i.unit_id=u.unit_id AND i.inspection_no=1) LIMIT 20;

-- Cửa sổ và transaction
SELECT unit_id,inspection_no,inspected_at,LAG(inspected_at) OVER(PARTITION BY unit_id ORDER BY inspection_no) AS previous_inspection FROM inspections ORDER BY unit_id,inspection_no LIMIT 20;

-- pandas, biểu đồ và Git
SELECT COUNT(DISTINCT unit_id) AS initially_inspected FROM inspections WHERE inspection_no=1;