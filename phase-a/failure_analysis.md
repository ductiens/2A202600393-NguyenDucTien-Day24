# Failure Cluster Analysis

## Bottom 10 Questions

| # | Question (truncated) | Type | F | AR | CP | CR | Avg | Cluster |
|---|---|---|---|---|---|---|---|---|
| 1 | Don xin nghi phep can ai phe duyet? Neu ket hop voi quy dinh 'Nghi om ca... | reasoning | 0.40 | 0.05 | 0.15 | 0.41 | 0.25 | C1 |
| 2 | Nhan vien chinh thuc duoc nghi phep nam bao nhieu ngay moi nam? Neu ket ... | reasoning | 0.44 | 0.10 | 0.36 | 0.41 | 0.33 | C1 |
| 3 | Nhan vien chinh thuc duoc nghi phep nam bao nhieu ngay moi nam? Neu ket ... | reasoning | 0.44 | 0.08 | 0.40 | 0.46 | 0.34 | C1 |
| 4 | Mat khau he thong phai doi bao lau mot lan? | simple | 0.66 | 0.27 | 0.17 | 1.00 | 0.52 | C2 |
| 5 | Mat khau he thong phai doi bao lau mot lan? | simple | 0.66 | 0.27 | 0.17 | 1.00 | 0.52 | C2 |
| 6 | Mat khau he thong phai doi bao lau mot lan? | simple | 0.66 | 0.27 | 0.17 | 1.00 | 0.52 | C2 |
| 7 | Mat khau he thong phai doi bao lau mot lan? Neu ket hop voi quy dinh 'Du... | reasoning | 0.69 | 0.29 | 0.15 | 1.00 | 0.53 | C1 |
| 8 | Mat khau he thong phai doi bao lau mot lan? Neu ket hop voi quy dinh 'Du... | reasoning | 0.69 | 0.29 | 0.15 | 1.00 | 0.53 | C1 |
| 9 | So sanh va tong hop: 'Nhan vien chinh thuc duoc nghi phep nam bao nhieu ... | multi_context | 0.57 | 0.42 | 0.18 | 1.00 | 0.54 | C2 |
| 10 | So sanh va tong hop: 'Nhan vien chinh thuc duoc nghi phep nam bao nhieu ... | multi_context | 0.57 | 0.42 | 0.18 | 1.00 | 0.54 | C2 |

## Clusters Identified

### Cluster C1: Multi-hop reasoning failures
**Pattern:** Cau hoi reasoning can ket hop >=2 facts nhung answer bi thieu suy luan.
**Examples:**
- R03: Ket hop quy dinh nghi phep va tham nien.
- R07: Ket hop nghi phep va nghi khong luong.
- R11: Ket hop chinh sach IT va retention.
**Root cause:** Retriever tra ve context qua ngan (chi 1 chunk) cho cau hoi can nhieu buoc.
**Proposed fix:**
- Tang `top_k` retriever tu 3 -> 6 cho nhom reasoning.
- Them hybrid retrieval (BM25 + dense) de giam bo sot facts.
- Add cross-encoder reranker de giu lai chunks complementary.

### Cluster C2: Off-topic retrieval contamination
**Pattern:** Context lay dung 1 chunk chinh nhung bi chen chunk khong lien quan.
**Examples:**
- M02: HR question bi chen chunk IT.
- M05: Multi-context policy co 1 chunk lac de.
- M09: Context precision giam manh do noise.
**Root cause:** Fusion stage uu tien score cao nhung khong co topical diversity constraint.
**Proposed fix:**
- Bo sung metadata filter theo domain (`hr`, `it`, `privacy`).
- Cai dat MMR diversity reranking sau RRF de loai chunk noise.
- Dat nguong minimum similarity cho chunk thu cap truoc khi vao prompt.
