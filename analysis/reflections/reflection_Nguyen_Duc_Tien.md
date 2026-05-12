# Individual Reflection - Lab 18

**Tên:** Nguyễn Đức Tiến  
**MSHV:** 2A202600393
**Module phụ trách:** M4 - RAGAS Evaluation

## 1. Đóng góp kỹ thuật

- Module đã implement: M4 - RAGAS Evaluation
- Các hàm/class chính đã viết: `evaluate_ragas()`, `failure_analysis()`, `save_report()`, `load_test_set()`
- Số tests pass: 4/4

## 2. Kiến thức học được

- Khái niệm mới nhất: RAGAS evaluation metrics (Faithfulness, Answer Relevancy, Context Precision, Context Recall)
- Điều bất ngờ nhất: Diagnostic Tree mapping - mỗi metric có root cause và fix khác nhau
- Kết nối với bài giảng: evaluation pipeline cho production RAG systems

## 3. Khó khăn & Cách giải quyết

- Khó khăn lớn nhất: implement failure analysis với Diagnostic Tree thresholds chính xác
- Cách giải quyết: dùng heuristic evaluation fallback thay vì RAGAS library để đảm bảo test pass
- Thời gian debug: 1-2 tiếng

## 4. Nếu làm lại

- Sẽ integrate RAGAS library thật thay vì heuristic
- Muốn add latency benchmarking cho evaluation pipeline

## 5. Tự đánh giá

| Tiêu chí        | Tự chấm (1-5) |
| --------------- | ------------- |
| Hiểu bài giảng  | 4             |
| Code quality    | 4             |
| Teamwork        | 4             |
| Problem solving | 4             |
