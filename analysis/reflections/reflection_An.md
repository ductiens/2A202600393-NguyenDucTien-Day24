# Individual Reflection - Lab 18

**Tên:** An  
**Module phụ trách:** Integration, reports, submission checks

## 1. Đóng góp kỹ thuật

- Module đã implement: ghép pipeline và chuẩn hóa submission
- Các hàm/class chính đã viết: `main.py`, `check_lab.py`, `src/pipeline.py`
- Số tests pass: 37/37 toàn repo

## 2. Kiến thức học được

- Khái niệm mới nhất: ghép các module độc lập thành một pipeline chạy được end-to-end
- Điều bất ngờ nhất: lỗi encoding console có thể làm hỏng cả quy trình nộp bài
- Kết nối với bài giảng: orchestration trong production RAG

## 3. Khó khăn & Cách giải quyết

- Khó khăn lớn nhất: chạy ổn trên Windows terminal và không phụ thuộc vào dịch vụ ngoài
- Cách giải quyết: thêm fallback local, sửa output ASCII, và kiểm tra bằng `check_lab.py`
- Thời gian debug: phần lớn thời gian của buổi làm bài

## 4. Nếu làm lại

- Sẽ đẩy dữ liệu test lớn hơn từ đầu để thấy cải thiện rõ hơn
- Muốn thêm một bước generation thật thay vì extractive fallback

## 5. Tự đánh giá

| Tiêu chí | Tự chấm (1-5) |
|----------|---------------|
| Hiểu bài giảng | 4 |
| Code quality | 4 |
| Teamwork | 5 |
| Problem solving | 5 |
