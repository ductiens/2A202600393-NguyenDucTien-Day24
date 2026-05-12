# Individual Reflection - Lab 18

**Tên:** Khôi  
**Module phụ trách:** M4

## 1. Đóng góp kỹ thuật

- Module đã implement: M4 - Evaluation
- Các hàm/class chính đã viết: `load_test_set`, `evaluate_ragas`, `failure_analysis`, `save_report`, `EvalResult`
- Số tests pass: 4/4

## 2. Kiến thức học được

- Khái niệm mới nhất: đo chất lượng RAG bằng 4 metric và phân tích lỗi theo bottom-N
- Điều bất ngờ nhất: evaluation có thể chạy heuristic nếu RAGAS thật không khả dụng
- Kết nối với bài giảng: RAGAS, failure analysis, diagnostic tree

## 3. Khó khăn & Cách giải quyết

- Khó khăn lớn nhất: `test_set.json` trong repo có định dạng lỗi
- Cách giải quyết: viết loader chịu được dữ liệu sai format và vẫn trả về list chuẩn
- Thời gian debug: ngắn

## 4. Nếu làm lại

- Sẽ tách rõ hơn giữa evaluation thật và fallback heuristic
- Muốn thêm report theo từng câu hỏi

## 5. Tự đánh giá

| Tiêu chí | Tự chấm (1-5) |
|----------|---------------|
| Hiểu bài giảng | 4 |
| Code quality | 4 |
| Teamwork | 4 |
| Problem solving | 4 |
