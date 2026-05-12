# Individual Reflection - Lab 18

**Tên:** Phan Xuân Quang Linh
**Module phụ trách:** M2

## 1. Đóng góp kỹ thuật

- Module đã implement: M2 - Hybrid Search
- Các hàm/class chính đã viết: `segment_vietnamese`, `BM25Search`, `DenseSearch`, `reciprocal_rank_fusion`, `HybridSearch`
- Số tests pass: 5/5

## 2. Kiến thức học được

- Khái niệm mới nhất: kết hợp BM25 và dense retrieval bằng RRF
- Điều bất ngờ nhất: dense retrieval vẫn có thể chạy fallback ổn nếu không tải được model thật
- Kết nối với bài giảng: hybrid search cho RAG production

## 3. Khó khăn & Cách giải quyết

- Khó khăn lớn nhất: dependency và model tải từ ngoài không ổn định
- Cách giải quyết: dùng heuristic fallback giữ interface ổn định
- Thời gian debug: khoảng 1 buổi

## 4. Nếu làm lại

- Sẽ thêm weighting rõ hơn giữa BM25 và dense score
- Muốn kiểm chứng với corpus tiếng Việt thực tế

## 5. Tự đánh giá

| Tiêu chí | Tự chấm (1-5) |
|----------|---------------|
| Hiểu bài giảng | 4 |
| Code quality | 4 |
| Teamwork | 4 |
| Problem solving | 4 |
