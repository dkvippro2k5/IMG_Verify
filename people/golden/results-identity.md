# Kết quả đo rule danh tính trên golden (2026-10-07)

- Golden: 602 ảnh còn trong file mới của mentor (237 rejected), nhãn [golden-labels-v2.csv](golden-labels-v2.csv).
- Đặc trưng: SCRFD-10g + ArcFace R50 (buffalo_l), CPU. Detect 0,66 s/ảnh, embedding 0,48 s/mặt (~1,6 s/ảnh tổng).
- Script: [tools/extract_faces.py](../tools/extract_faces.py), [tools/eval_identity.py](../tools/eval_identity.py).

## Rule đạt 100% trên golden (ứng viên tự loại)

| Rule | Loại | Đúng | Precision | Bắt được (% rejected) |
|------|------|------|-----------|----------------------|
| R1 tiêu đề có tên **khác dấu** với `canonical_name` | 37 | 37 | 100% | 15,6% |
| A2 tiêu đề **không có tên** VÀ mặt giống mốc < 0,25 | 23 | 23 | 100% | 9,7% |
| **R1 ∪ A2** | **60** | **60** | **100%** | **25,3%** |

Mốc (anchor) = mặt lớn nhất của các ảnh có tên khớp đúng trong tiêu đề; giữ cụm mốc lớn nhất (≥ 2 ảnh). A2 ổn định với ngưỡng 0,15–0,30 (luôn 100%).

**Giới hạn:** 60 ảnh đến từ một số ít entity. Không lỗi trên 60 ảnh chỉ cho cận trên sai số khoảng 5%, chưa chứng minh được 99%. Cần mẫu kiểm tra ~5% ảnh auto-reject khi chạy thật.

## Rule chưa đạt 99% (chỉ dùng làm gợi ý cho người duyệt)

| Rule | Loại | Precision | Bắt được |
|------|------|-----------|----------|
| R4 không có tên VÀ mặt giống cụm chính < 0,30 | 102 | 97,1% | 41,8% |
| R3 mặt giống cụm chính < 0,10 | 78 | 94,9% | 31,2% |
| E1 cụm chính không có ảnh nào có tên khớp → loại cả entity | 159 | 92,5% | 62,0% |
| W3 mentor đánh `cluster = ambiguous` | 19 | 89,5% | 7,2% |
| W1 tiêu đề không nhắc tên | 212 | 80,2% | 71,7% |

Lỗi chính của các rule dựa trên "cụm chính": chọn nhầm cụm khi entity có nhiều người (vd Nhạc sĩ Thái Cơ), tên đầy đủ khác tên gốc (Trần **Lê** Quốc Toàn), ảnh có nhiều mặt.

## Hệ quả

- Với ràng buộc ≥ 99%, pipeline hiện tự loại được ~10% số ảnh (≈ 25% số ảnh xấu). ~90% ảnh vẫn qua người duyệt.
- Giá trị lớn hơn nằm ở **gợi ý**: R4 đánh dấu sẵn ~42% số ảnh xấu với độ đúng ~97%, giúp người duyệt xác nhận nhanh.
- Tiêu chí chất lượng / nhạy cảm gần như không có mẫu trong golden (15 ảnh), nên chưa đo được.
