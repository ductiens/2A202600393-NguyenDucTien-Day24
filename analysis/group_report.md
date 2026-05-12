# Group Report — Lab 18: Production RAG

**Nhom:** C401-E2
**Ngay:** 2026-05-04

## Thanh vien & Phan cong

| Ten | Module | Hoan thanh | Tests pass |
|-----|--------|-----------|-----------|
|  | M1: Chunking | x | 8/8 |
|  | M2: Hybrid Search | x | 5/5 |
|  | M3: Reranking | x | 5/5 |
|  | M4: Evaluation | x | 4/4 |

## Ket qua RAGAS

| Metric | Naive | Production | Delta |
|--------|-------|-----------|-------|
| Faithfulness | 0.9600 | 0.8875 | -0.073 |
| Answer Relevancy | 0.7969 | 0.8449 | +0.048 |
| Context Precision | 0.7583 | 0.8804 | +0.122 |
| Context Recall | 0.8000 | 0.7500 | -0.05 |

## Key Findings

1. **Biggest improvement:** Context Precision tang +0.122 — Hybrid Search (BM25 + Dense + RRF) ket hop voi multilingual CrossEncoder reranker (mmarco-mMiniLMv2) loai bo duoc nhieu chunk nhieu hon naive baseline.

2. **Biggest challenge:** Context Recall giam -0.05 — cac cau hoi liet ke (Dieu 9 co 11 quyen, du lieu co ban co 12 loai) bi phan tan sang qua nhieu chunk nho (400 chars). Top-5 reranked chunks khong cover het, dan den recall thap du search co tim dung.

3. **Surprise finding:** Doi reranker tu ms-marco (English-only) sang mmarco (multilingual) tang faithfulness tu 0.70 len 0.89 (+0.19) — chinh to viec chon dung ngon ngu cho reranker quan trong hon la tang chunk size hay top_k. Model tieng Anh rerank tieng Viet se dua sai chunk len top, LLM generate tu context sai thi faithfulness sap.

## Presentation Notes (5 phut)

1. RAGAS scores (naive vs production): Context Precision vuot baseline (+0.12), nhung Context Recall giam (-0.5) vi chunk nho bi chia cat cho cac doan liet ke dai.

2. Biggest win — M3 Reranking: doi tu ms-marco sang mmarco multilingual, faithfulness tang 0.19 (0.70 → 0.89). Language mismatch giua reranker va corpus la nguyen nhan chinh khien production thua naive.

3. Case study — "Chu the du lieu co nhung quyen gi theo Dieu 9?" (context_recall=0.0): Error Tree — search tim dung chunk → reranker giu lai top-5 → nhung Dieu 9 co 11 quyen trai 4 chunk → top-5 khong du → answer thieu quyen. Fix: tang RERANK_TOP_K hoac dung parent chunk.

4. Next optimization neu co them 1 gio: Parent chunk retrieval — khi child chunk duoc lay, tu dong mo rong sang parent (2048 chars) de dam bao lay het cac enumeration dai trong van ban phap luat.
