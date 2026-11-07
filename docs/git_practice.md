# Tự phát triển từ Issues
Chưa làm sẵn ba phần: lọc lô theo số kiểm tra tối thiểu; xuất lịch sử một đơn vị; hình so kiểm tra đầu/kiểm tra lại. Viết tiêu chí và test trước. Không thay mẫu số mặc định âm thầm.
```powershell
git switch -c feature/min-inspected
git diff
python -m unittest discover -s tests -v
git add ten_file_da_sua
git commit -m "Add minimum inspected units filter"
git push -u origin feature/min-inspected
```
Tạo PR ghi Closes #số_issue. Không commit CSV sinh, DB, outputs hoặc môi trường. Chỉ thao tác Git cần cài Git; chạy chương trình không cần.
