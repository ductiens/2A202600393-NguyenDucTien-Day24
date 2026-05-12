# Failure Analysis — Lab 18: Production RAG

**Nhom:** C401-E2  
**Thanh vien:** 

---

## RAGAS Scores

| Metric | Naive Baseline | Production | Delta |
|--------|---------------|------------|-------|
| Faithfulness | 0.9600 | 0.8875 | -0.073 |
| Answer Relevancy | 0.7969 | 0.8449 | +0.048 |
| Context Precision | 0.7583 | 0.8804 | +0.122 |
| Context Recall | 0.8000 | 0.7500 | -0.05 |

---

## Bottom-5 Failures

### #1
- **Question:** Cac hanh vi bi nghiem cam theo Dieu 8 Nghi dinh 13 la gi?
- **Expected:** Cac hanh vi bi nghiem cam gom: xu ly du lieu ca nhan trai phap luat; xu ly du lieu de chong lai Nha nuoc; xu ly du lieu gay anh huong an ninh quoc gia; can tro hoat dong bao ve du lieu ca nhan cua co quan co tham quyen; va loi dung hoat dong bao ve du lieu de vi pham phap luat.
- **Got:** LLM them thong tin ngoai context (hallucination)
- **Worst metric:** faithfulness = 0.0
- **Error Tree:** Output sai → Context dung? → Kiem tra → Reranker dua len dung chunk nhung LLM them thong tin ngoai → LLM hallucinating
- **Root cause:** Model ms-marco (English) da duoc thay bang mmarco nhung Dieu 8 liet ke nhieu muc ngan → LLM "doan" them cac hanh vi tuong tu ma khong co trong context
- **Suggested fix:** Tighten prompt — yeu cau LLM chi trich dan nguyen van, khong suy luan them

### #2
- **Question:** Du lieu ca nhan co ban bao gom nhung thong tin gi?
- **Expected:** Du lieu ca nhan co ban bao gom ho ten, ngay thang nam sinh, gioi tinh, noi sinh, quoc tich, hinh anh, so dien thoai, so CMND/CCCD, so ho chieu, tinh trang hon nhan, thong tin tai khoan so va cac thong tin khac gan lien voi mot con nguoi cu the.
- **Got:** Chi lay duoc mot phan danh sach, thieu nhieu loai
- **Worst metric:** context_recall = 0.0
- **Error Tree:** Output thieu thong tin → Context day du? → Khong — chunk 400 chars khong chua het danh sach ~12 loai → Missing relevant chunks
- **Root cause:** Du lieu co ban duoc liet ke trong mot doan dai (~600 chars), bi cat ra nhieu chunk nho → top-5 reranked chunks khong bao phu het
- **Suggested fix:** Tang HIERARCHICAL_CHILD_SIZE len 600 hoac dung parent chunk (2048 chars) cho cau hoi liet ke

### #3
- **Question:** Chu the du lieu co nhung quyen gi theo Dieu 9 Nghi dinh 13?
- **Expected:** Chu the du lieu co 11 quyen: quyen duoc biet, quyen dong y, quyen truy cap, quyen rut lai su dong y, quyen xoa du lieu, quyen han che xu ly du lieu, quyen cung cap du lieu, quyen phan doi xu ly du lieu, quyen khieu nai to cao khoi kien, quyen yeu cau boi thuong thiet hai va quyen tu bao ve.
- **Got:** Chi liet ke duoc mot so quyen, khong du 11 quyen
- **Worst metric:** context_recall = 0.0
- **Error Tree:** Output thieu quyen → Context co day du? → Khong — Dieu 9 trai dai qua 3-4 chunk → top-5 khong lay het → Missing relevant chunks
- **Root cause:** 11 quyen trai tren nhieu doan, chunk_size 400 bi chia nho. Reranker lay dung 1-2 chunk dau nhung bo qua phan con lai
- **Suggested fix:** Tang RERANK_TOP_K len 8, hoac dung parent chunk

### #4
- **Question:** Du lieu ca nhan nhay cam la gi va bao gom nhung loai nao?
- **Expected:** Du lieu ca nhan nhay cam la du lieu gan lien voi quyen rieng tu cua ca nhan, khi bi xam pham se gay anh huong truc tiep toi quyen loi hop phap cua ca nhan, bao gom: quan diem chinh tri, ton giao, tinh trang suc khoe, nguon goc chung toc, dac diem sinh trac hoc, doi song tinh duc, du lieu ve toi pham va thong tin tai chinh ngan hang.
- **Got:** Mo ta chung chung, bo sot mot so loai cu the
- **Worst metric:** context_recall = 0.5
- **Error Tree:** Output thieu loai du lieu → Context co du? → Mot phan — chunk co dinh nghia nhung thieu phan cuoi danh sach → Missing tail of enumeration
- **Root cause:** Danh sach cac loai du lieu nhay cam bi cat giua doan → chunk cuoi cung khong duoc rerank len top
- **Suggested fix:** Dung overlap giua cac chunk hoac tang child_size

### #5
- **Question:** Ten cong ty nop to khai thue GTGT quy 4 nam 2024 la gi?
- **Expected:** Cong ty nop to khai la CONG TY CO PHAN DHA SURFACES voi ma so thue 0106769437.
- **Got:** Cau tra loi co nhung kem chinh xac, co them thong tin cua cong ty khac
- **Worst metric:** context_precision = 0.5
- **Error Tree:** Output co thong tin sai → Qua nhieu context khong lien quan → Reranker dua len nhieu chunk tu file Nghi dinh xen vao → Too many irrelevant chunks
- **Root cause:** Hybrid search lay ca chunks tu Nghi dinh 13 lan BCTC → reranker khong phan biet duoc document source → context bi "nhiem" boi chunks tu file khac
- **Suggested fix:** Them metadata filter theo document source, hoac dung source-aware reranking

---

## Case Study (cho presentation)

**Question chon phan tich:** "Chu the du lieu co nhung quyen gi theo Dieu 9 Nghi dinh 13?"

**Error Tree walkthrough:**
1. Output dung? → Khong — chi liet ke 4-5 quyen, thieu 6-7 quyen con lai
2. Context day du? → Khong — context_recall = 0.0, top-5 chunks khong cover het Dieu 9
3. Search co tim duoc chunk? → Co — Qdrant tim duoc nhieu chunk lien quan
4. Reranker giu lai du chunk? → Khong — RERANK_TOP_K=5 qua thap, cac chunk cuoi Dieu 9 bi loai
5. Fix o buoc: Tang RERANK_TOP_K + tang chunk_size de it bi chia cat hon

**Neu co them 1 gio, se optimize:**
- Dung parent chunk retrieval: khi tim duoc child chunk lien quan, tu dong lay ca parent (2048 chars) de dam bao cover het cac enumeration dai
- Them metadata filter theo file source de tranh cross-document noise
