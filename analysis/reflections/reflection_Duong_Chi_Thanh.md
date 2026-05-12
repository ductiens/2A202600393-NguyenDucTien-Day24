# Individual Reflection - Lab 18

**Tên:** Dương Chí Thành  
**Module phụ trách:** M3

## 1. Đóng góp kỹ thuật

- Module đã implement: M3 - Reranking
- Các hàm/class chính đã viết: `CrossEncoderReranker`, `FlashrankReranker`, `benchmark_reranker`
- Số tests pass: 5/5

## 2. Kiến thức học được

- Khái niệm mới nhất: cross-encoder reranking và cách nó sắp xếp lại top-k sau retrieval
- Điều bất ngờ nhất: reranker tốt vẫn không cứu được pipeline nếu context đầu vào quá yếu
- Kết nối với bài giảng: retrieval và reranking trong production RAG

## 3. Khó khăn & Cách giải quyết

- Khó khăn lớn nhất: môi trường không đảm bảo tải được model thật
- Cách giải quyết: thêm fallback heuristic để giữ test và pipeline chạy được
- Thời gian debug: khoảng 1 buổi làm việc ngắn

## 4. Nếu làm lại

- Sẽ ưu tiên benchmark rõ hơn giữa model thật và fallback
- Muốn thử reranker trên dữ liệu tiếng Việt lớn hơn

## 5. Tự đánh giá

| Tiêu chí | Tự chấm (1-5) |
|----------|--------------|
| Hiểu bài giảng | 4            |
| Code quality | 4            |
| Teamwork | 5            |
| Problem solving | 4            |
