# Báo cáo entity có vấn đề về dữ liệu ảnh

> Ngày 2026-10-08 · Người duyệt: Dương Văn Kiên · Nguồn nhãn: `scope-labels-DuongVanKien-2026-10-07 (1).csv`

## Phạm vi và cách đọc

- Phần việc: 1/3 cuối file `approved-results (1).csv` (dòng 13325–19988). Báo cáo này dựa trên **304 entity đã duyệt xong toàn bộ ảnh** trong batch 1–12 (3.432 ảnh, 2.369 approved). 134 entity khác chưa duyệt xong và batch 13–17 chưa có trong báo cáo.
- Tiêu chí: theo hướng dẫn duyệt (đúng người theo `canonical_name` khớp đúng dấu và đúng vai trò; rõ; không quá bé; không nhạy cảm; không quá nhiều chi tiết).
- Lý do loại: `wrong_person` = không phải người của entity; `name_mismatch` = tiêu đề nói về người khác hoặc tên khác dấu; `unresolved` = không xác định được entity là ai.

## Tóm tắt

**106/304 entity (35%) có vấn đề**, chia 4 nhóm (một entity có thể thuộc nhiều nhóm):

| Nhóm | Số entity | Ý nghĩa | Đề xuất |
|---|---|---|---|
| 1. Không còn ảnh nào dùng được | 66 | 6 entity không xác định được là ai; 60 entity mọi ảnh đều là người khác | Kiểm tra lại entity/query, crawl lại |
| 2. Lẫn nhiều người | 33 | ≥ 50% ảnh bị loại vì sai người | Crawl lại với query rõ hơn |
| 3. Còn quá ít ảnh (1–2 ảnh) | 5 | Dữ liệu ban đầu ít hoặc gần hết bị loại | Bổ sung ảnh |
| 4. Nhiều ảnh không tải được | 8 | ≥ 30% link ảnh lỗi | Kiểm tra link CDN |

**Phân bố nhóm 1 theo category** (tỉ lệ entity không còn ảnh nào):

| Category | Entity đã duyệt | Không còn ảnh | Tỉ lệ |
|---|---|---|---|
| historic | 43 | 27 | **63%** |
| athletes | 42 | 14 | 33% |
| scientist | 24 | 6 | 25% |
| politicer | 32 | 7 | 22% |
| writer | 15 | 2 | 13% |
| celeb | 38 | 3 | 8% |
| businessman | 24 | 2 | 8% |
| singer | 86 | 5 | 6% |

Nhận xét:
- **Nhân vật lịch sử** (nhiều entity dạng "tiến sĩ khoa …") gần như không có ảnh thật trên web, kết quả tìm kiếm trả về người cùng tên hiện đại.
- **Vận động viên ít nổi tiếng** và **tên phổ biến** (Phạm Văn …, Phan Thị …) hay bị lẫn với người cùng tên.
- Một số query dùng sai vai trò hoặc tên khác dấu (vd "Phương Loan" ra NSND Phượng Loan).

## Danh sách rút gọn

Mỗi entity chỉ nằm ở một nhóm (trừ nhóm ảnh lỗi). "Sai lĩnh vực" là ước đoán: phần lớn ảnh bị loại có tiêu đề đúng tên nhưng là người khác.

```
Entities không còn ảnh dùng được (mọi ảnh là người khác)
Đinh Thị Duyên
Dương Đình Nghệ
Nguyễn Văn Thông
NSND Dịu Hương
Phạm Bảo
Phạm Công Hưng
Phạm Gia Chuyên
Phạm Gia Kỷ
Phạm Gia Môn
Phạm Hà Phương á hậu 1 HHVN 2024
Phạm Hồng Phú - VĐV Paralympic điền kinh
Phạm Hồng Văn
Phạm Huy Cơ
Phạm Minh Toàn
Phạm Nguyễn Du
Phạm Phước
Phạm Quang Hoàn
Phạm Tử Dương
Phạm Tử Nghi
Phạm Văn Cường (chính khách)
Phạm Văn Đức
Phạm Văn Hoàng
Phạm Văn Huy
Phạm Văn Nhân
Phạm Văn Tuấn
Phan Chính Nghị
Phan Đình Bình
Phan Huy Thông
Phan Huy Thực
Phan Thị Thùy Linh
Phan Thị Thùy Trang (cầu lông)
Phan Thu
Phan Văn Ái
Phương Loan
Quy Sắc
Sĩ Thanh
Thái Bá Cầu
Thái Thú
Thân Toàn
Thân Trọng Tiết
Thang Máy
Thế Anh
Thiếu Sơn
Tô Hiệu
Tô Trân
Tôn Thất Tế
Tôn Thất Tư
Trần Anh Vinh
Trần Bằng Việt
Trần Lựu
Trần Nguyễn Bảo Châu
Trần Văn Dư
Trần Văn Khánh

Sai lĩnh vực (ảnh đúng tên nhưng là người cùng tên ở lĩnh vực khác)
Phạm Thị Mỹ Hạnh
Phan Thanh (politicer)
Phan Thị Hà
Te
Thái Thuận
Thảo Đường
Trần Thị Phương Thảo

Entities không thể xác nhận
Nong Bee
Tạ Thông
Thanh Tùng
Thùy Linh (5 Dòng Kẻ)
Tin Tức Mới
Tnhan

Entities còn quá ít ảnh
Khánh Linh (đúng 2 ảnh)
Ninh Tốn (đúng 2 ảnh)
Ninh Viết Giao (đúng 1 ảnh)
NSND Bùi Đắc Sừ (đúng 1 ảnh)
NSND Nguyễn Lai (đúng 1 ảnh)
Phạm Chuyên (đúng 2 ảnh)
Phạm Đình Trọng (đúng 2 ảnh)
Phạm Hồng Sơn (đúng 2 ảnh)
Phạm Minh Tuyên (đúng 1 ảnh)
Phạm Thị Hoài (đúng 2 ảnh)
Phạm Vấn (đúng 1 ảnh)
Phạm Văn Toàn (đúng 2 ảnh)
Phan Bá Vành (đúng 1 ảnh)
Phan Thanh (scientist) (đúng 1 ảnh)
Phan Thành Nam (đúng 1 ảnh)
Phan Văn Đạt (đúng 1 ảnh)
Quốc Trụ (đúng 1 ảnh)
Riot Bigiman (đúng 2 ảnh)
Thái Vũ (đúng 1 ảnh)
Thắng (solo) (đúng 2 ảnh)
The Flob (đúng 2 ảnh)

Nhiều người giống tên (≥ 50% ảnh là người khác)
Lê Ngọc Lâm (đúng 3/13 ảnh)
NSND Trần Khánh (đúng 4/14 ảnh)
Phạm Đỗ Chí (đúng 6/12 ảnh)
Phạm Minh Hoàng (đúng 9/18 ảnh)
Phạm Thị Hương (đúng 5/16 ảnh)
Phạm Thị Yến (đúng 3/11 ảnh)
Phạm Văn (đúng 3/13 ảnh)
Phạm Văn Dòng (đúng 5/14 ảnh)
Phan Công Đức (đúng 3/10 ảnh)
Phan Hồng Giang (đúng 7/14 ảnh)
Phan Văn Hưng (đúng 3/17 ảnh)
Quỳnh Anh (đúng 7/19 ảnh)
Rosy (đúng 3/10 ảnh)
Thanh Tâm (đúng 4/15 ảnh)
Thảo Phương (đúng 3/7 ảnh)
Thu Hà (đúng 8/20 ảnh)
Tuấn Anh (đúng 3/8 ảnh)

Nhiều ảnh không tải được (≥ 30% link lỗi)
Te (1/1 ảnh lỗi)
Thân Trọng Tiết (2/5 ảnh lỗi)
The Flob (1/2 ảnh lỗi)
Thu Hà (8/20 ảnh lỗi)
Tô Trân (1/3 ảnh lỗi)
Tôn Thất Bách (9/22 ảnh lỗi)
Tôn Thất Tế (5/15 ảnh lỗi)
Trần Bắc Hà (6/18 ảnh lỗi)
```

## Nhóm 1a. Không xác định được entity là ai (6)

| # | Entity (slug) | Category | Query | Ảnh | Approved | Lý do loại chính |
|---|---|---|---|---|---|---|
| 1 | Nong Bee (`nong-bee-le-bong`) | celeb | chân dung Nong Bee | 19 | 0 | unresolved 19 |
| 2 | Thanh Tùng (`thanh-tung`) | singer | nghệ sĩ Thanh Tùng | 16 | 0 | unresolved 16 |
| 3 | Tnhan (`tnhan-lien-quan-tdt-esports`) | athletes | vận động viên Tnhan | 10 | 0 | unresolved 10 |
| 4 | Tin Tức Mới (`tin-tuc-moi-ts-khoa-1604`) | historic | lịch sử Tin Tức Mới | 9 | 0 | unresolved 9 |
| 5 | Tạ Thông (`ta-thong-ts-khoa-1475`) | historic | lịch sử Tạ Thông | 5 | 0 | unresolved 5 |
| 6 | Thùy Linh (5 Dòng Kẻ) (`thuy-linh-5-dong-ke`) | singer | nghệ sĩ Thùy Linh (5 Dòng Kẻ) | 4 | 0 | unresolved 4 |

## Nhóm 1b. Mọi ảnh đều là người khác (60)

| # | Entity (slug) | Category | Query | Ảnh | Approved | Lý do loại chính |
|---|---|---|---|---|---|---|
| 1 | Phạm Hồng Văn (`pham-hong-van`) | athletes | vận động viên Phạm Hồng Văn | 19 | 0 | wrong_person 16, name_mismatch 7 |
| 2 | Phan Thị Thùy Linh (`phan-thi-thuy-linh-libero`) | athletes | vận động viên Phan Thị Thùy Linh | 18 | 0 | wrong_person 12, name_mismatch 10 |
| 3 | Phạm Thị Mỹ Hạnh (`pham-thi-my-hanh`) | athletes | vận động viên Phạm Thị Mỹ Hạnh | 16 | 0 | wrong_person 16, name_mismatch 12 |
| 4 | Phạm Văn Đức (`pham-van-duc-para-cu-ta`) | athletes | vận động viên Phạm Văn Đức | 16 | 0 | wrong_person 16, name_mismatch 10 |
| 5 | Phạm Văn Hoàng (`pham-van-hoang-cu-ta`) | athletes | vận động viên Phạm Văn Hoàng | 13 | 0 | wrong_person 13, name_mismatch 8 |
| 6 | Phan Thị Hà (`phan-thi-ha-rowing`) | athletes | vận động viên Phan Thị Hà | 13 | 0 | wrong_person 13, name_mismatch 9 |
| 7 | Phan Thị Thùy Trang (cầu lông) (`phan-thi-thuy-trang-cau-long`) | athletes | vận động viên Phan Thị Thùy Trang (cầu lông) | 13 | 0 | wrong_person 13, name_mismatch 7 |
| 8 | Trần Thị Phương Thảo (`scope-23-tran-thi-phuong-thao`) | athletes | vận động viên Trần Thị Phương Thảo | 12 | 0 | wrong_person 12, name_mismatch 8 |
| 9 | Đinh Thị Duyên (`scope-23-dinh-thi-duyen`) | athletes | vận động viên Đinh Thị Duyên | 9 | 0 | wrong_person 9, name_mismatch 2 |
| 10 | Phạm Hồng Phú - VĐV Paralympic điền kinh (`pham-hong-phu-vdv-paralympic-dien-kinh`) | athletes | vận động viên Phạm Hồng Phú - VĐV Paralympic điền kinh | 3 | 0 | name_mismatch 3, wrong_person 3 |
| 11 | Thế Anh (`the-anh-ba-den`) | athletes | vận động viên Thế Anh | 3 | 0 | wrong_person 2, no_person 1 |
| 12 | Trần Nguyễn Bảo Châu (`tran-nguyen-bao-chau`) | athletes | vận động viên Trần Nguyễn Bảo Châu | 2 | 0 | name_mismatch 2, wrong_person 2 |
| 13 | Te (`te`) | athletes | vận động viên Te | 1 | 0 | name_mismatch 1, wrong_person 1 |
| 14 | Trần Bằng Việt (`tran-bang-viet-ceo-dong-a-podcast`) | businessman | doanh nhân Trần Bằng Việt | 15 | 0 | wrong_person 15, name_mismatch 5 |
| 15 | Phạm Minh Toàn (`pham-minh-toan-sang-lap-marathon-education`) | businessman | doanh nhân Phạm Minh Toàn | 11 | 0 | wrong_person 11, name_mismatch 3 |
| 16 | Sĩ Thanh (`si-thanh-nguyen-thi-si-thanh`) | celeb | chân dung Sĩ Thanh | 18 | 0 | wrong_person 18, name_mismatch 4 |
| 17 | Phạm Hà Phương á hậu 1 HHVN 2024 (`pham-ha-phuong-a-hau-1-hhvn-2024`) | celeb | chân dung Phạm Hà Phương á hậu 1 HHVN 2024 | 13 | 0 | wrong_person 13, name_mismatch 4 |
| 18 | Nguyễn Văn Thông (`scope-4-nguyen-van-thong`) | historic | lịch sử Nguyễn Văn Thông | 26 | 0 | wrong_person 24, name_mismatch 13 |
| 19 | Phạm Văn Nhân (`pham-van-nhan`) | historic | lịch sử Phạm Văn Nhân | 18 | 0 | wrong_person 18, name_mismatch 11 |
| 20 | Phạm Văn Huy (`pham-van-huy-ts-khoa-1829`) | historic | lịch sử Phạm Văn Huy | 16 | 0 | wrong_person 16, name_mismatch 3 |
| 21 | Thái Thú (`thai-thu-can-vuong`) | historic | lịch sử Thái Thú | 15 | 0 | wrong_person 13, name_mismatch 6 |
| 22 | Tôn Thất Tế (`ton-that-te`) | historic | lịch sử Tôn Thất Tế | 15 | 0 | wrong_person 15, name_mismatch 11 |
| 23 | Tôn Thất Tư (`ton-that-tu`) | historic | lịch sử Tôn Thất Tư | 13 | 0 | wrong_person 13, name_mismatch 6 |
| 24 | Phạm Tử Nghi (`pham-tu-nghi-ts-khoa-1463`) | historic | lịch sử Phạm Tử Nghi | 12 | 0 | wrong_person 12, name_mismatch 1 |
| 25 | Phạm Gia Môn (`pham-gia-mon-tham-hoa`) | historic | lịch sử Phạm Gia Môn | 9 | 0 | wrong_person 9, name_mismatch 2 |
| 26 | Thảo Đường (`thao-duong-thien-su`) | historic | lịch sử Thảo Đường | 9 | 0 | wrong_person 6, name_mismatch 4 |
| 27 | Phạm Bảo (`pham-bao-ts-khoa-1487`) | historic | lịch sử Phạm Bảo | 8 | 0 | wrong_person 8, name_mismatch 1 |
| 28 | Phan Huy Thông (`scope-4-phan-huy-thong`) | historic | lịch sử Phan Huy Thông | 8 | 0 | wrong_person 8, name_mismatch 3 |
| 29 | Trần Lựu (`tran-luu`) | historic | lịch sử Trần Lựu | 8 | 0 | name_mismatch 8, wrong_person 8 |
| 30 | Phạm Gia Chuyên (`pham-gia-chuyen-tien-si-dong-ngac-1831`) | historic | lịch sử Phạm Gia Chuyên | 7 | 0 | wrong_person 7, name_mismatch 3 |
| 31 | Phạm Công Hưng (`pham-cong-hung`) | historic | lịch sử Phạm Công Hưng | 6 | 0 | wrong_person 5, name_mismatch 2 |
| 32 | Phạm Nguyễn Du (`pham-nguyen-du`) | historic | lịch sử Phạm Nguyễn Du | 6 | 0 | name_mismatch 6, wrong_person 6 |
| 33 | Phạm Văn Tuấn (`pham-van-tuan-bang-nhan`) | historic | lịch sử Phạm Văn Tuấn | 6 | 0 | wrong_person 6, name_mismatch 2 |
| 34 | Thân Toàn (`than-toan-ts-khoa-1652`) | historic | lịch sử Thân Toàn | 6 | 0 | wrong_person 6, name_mismatch 1 |
| 35 | Phan Đình Bình (`phan-dinh-binh`) | historic | lịch sử Phan Đình Bình | 5 | 0 | wrong_person 5, name_mismatch 4 |
| 36 | Phan Huy Thực (`phan-huy-thuc`) | historic | lịch sử Phan Huy Thực | 5 | 0 | wrong_person 5, no_person 3 |
| 37 | Thân Trọng Tiết (`than-trong-tiet-ts-khoa-1849`) | historic | lịch sử Thân Trọng Tiết | 5 | 0 | wrong_person 5, name_mismatch 4 |
| 38 | Phạm Quang Hoàn (`pham-quang-hoan-tien-si-dong-ngac-1694`) | historic | lịch sử Phạm Quang Hoàn | 4 | 0 | wrong_person 4, name_mismatch 2 |
| 39 | Phan Chính Nghị (`phan-chinh-nghi`) | historic | lịch sử Phan Chính Nghị | 4 | 0 | wrong_person 4, name_mismatch 3 |
| 40 | Trần Văn Dư (`tran-van-du`) | historic | lịch sử Trần Văn Dư | 4 | 0 | name_mismatch 2, wrong_person 2 |
| 41 | Thái Thuận (`thai-thuan`) | historic | lịch sử Thái Thuận | 2 | 0 | name_mismatch 2, wrong_person 2 |
| 42 | Phan Văn Ái (`phan-van-ai`) | historic | lịch sử Phan Văn Ái | 1 | 0 | name_mismatch 1, wrong_person 1 |
| 43 | Phạm Phước (`pham-phuoc`) | politicer | chính khách Phạm Phước | 10 | 0 | wrong_person 10, name_mismatch 3 |
| 44 | Trần Anh Vinh (`tran-anh-vinh`) | politicer | chính khách Trần Anh Vinh | 8 | 0 | wrong_person 8, name_mismatch 6 |
| 45 | Phạm Văn Cường (chính khách) (`pham-van-cuong-chinh-khach`) | politicer | Phạm Văn Cường (chính khách) | 5 | 0 | name_mismatch 5, wrong_person 5 |
| 46 | Phan Thanh (`phan-thanh`) | politicer | chính khách Phan Thanh | 5 | 0 | wrong_person 5, name_mismatch 4 |
| 47 | Tô Hiệu (`to-hieu`) | politicer | chính khách Tô Hiệu | 3 | 0 | wrong_person 3, name_mismatch 2 |
| 48 | Phan Thu (`phan-thu`) | politicer | chính khách Phan Thu | 2 | 0 | name_mismatch 2, wrong_person 2 |
| 49 | Dương Đình Nghệ (`scope-4-duong-dinh-nghe-931-937`) | politicer | chính khách Dương Đình Nghệ | 2 | 0 | wrong_person 2, name_mismatch 1 |
| 50 | Phạm Huy Cơ (`pham-huy-co-bac-si`) | scientist | nhà khoa học Phạm Huy Cơ | 17 | 0 | wrong_person 17, name_mismatch 6 |
| 51 | Phạm Gia Kỷ (`pham-gia-ky-toan`) | scientist | nhà khoa học Phạm Gia Kỷ | 9 | 0 | wrong_person 9, name_mismatch 2 |
| 52 | Trần Văn Khánh (`tran-van-khanh`) | scientist | nhà khoa học Trần Văn Khánh | 4 | 0 | name_mismatch 4, wrong_person 4 |
| 53 | Tô Trân (`to-tran-su-hoc`) | scientist | nhà khoa học Tô Trân | 3 | 0 | no_person 2, wrong_person 1 |
| 54 | Phạm Tử Dương (`pham-tu-duong`) | scientist | nhà khoa học Phạm Tử Dương | 2 | 0 | name_mismatch 2, wrong_person 2 |
| 55 | Thái Bá Cầu (`thai-ba-cau`) | scientist | nhà khoa học Thái Bá Cầu | 2 | 0 | name_mismatch 2, wrong_person 2 |
| 56 | NSND Dịu Hương (`nsnd-diu-huong-cheo`) | singer | nghệ sĩ NSND Dịu Hương | 12 | 0 | wrong_person 12, name_mismatch 5 |
| 57 | Phương Loan (`phuong-loan`) | singer | nghệ sĩ Phương Loan | 12 | 0 | name_mismatch 12 |
| 58 | Thang Máy (`thang-may-ban-nhac-rock`) | singer | nghệ sĩ Thang Máy | 10 | 0 | wrong_person 10, name_mismatch 5 |
| 59 | Thiếu Sơn (`thieu-son`) | writer | nhà văn Thiếu Sơn | 11 | 0 | wrong_person 6, name_mismatch 5 |
| 60 | Quy Sắc (`quy-sac`) | writer | nhà văn Quy Sắc | 1 | 0 | name_mismatch 1, wrong_person 1 |

## Nhóm 2. Lẫn nhiều người, ≥ 50% ảnh sai người (33)

| # | Entity (slug) | Category | Query | Ảnh | Approved | Lý do loại chính |
|---|---|---|---|---|---|---|
| 1 | NSND Nguyễn Lai (`nsnd-nguyen-lai-tuong`) | singer | nghệ sĩ NSND Nguyễn Lai | 16 | 1 | wrong_person 15, name_mismatch 9 |
| 2 | Thái Vũ (`thai-vu-nha-van`) | writer | nhà văn Thái Vũ | 16 | 1 | wrong_person 15, name_mismatch 8 |
| 3 | Phạm Minh Tuyên (`pham-minh-tuyen-chinh-khach`) | politicer | chính khách Phạm Minh Tuyên | 15 | 1 | wrong_person 14, name_mismatch 12 |
| 4 | NSND Bùi Đắc Sừ (`nsnd-bui-dac-su-cheo`) | singer | nghệ sĩ NSND Bùi Đắc Sừ | 14 | 1 | wrong_person 11, name_mismatch 4 |
| 5 | Phan Thành Nam (`phan-thanh-nam-toan-giai-hermann-weyl`) | scientist | nhà khoa học Phan Thành Nam | 11 | 1 | wrong_person 10, name_mismatch 7 |
| 6 | Phan Thanh (`phan-thanh-nha-giao`) | scientist | nhà khoa học Phan Thanh | 9 | 1 | name_mismatch 8, wrong_person 8 |
| 7 | Phạm Văn Toàn (`pham-van-toan`) | historic | lịch sử Phạm Văn Toàn | 16 | 2 | wrong_person 14, name_mismatch 4 |
| 8 | Phạm Chuyên (`pham-chuyen`) | politicer | chính khách Phạm Chuyên | 14 | 2 | name_mismatch 12, wrong_person 12 |
| 9 | Phạm Hồng Sơn (`pham-hong-son-masan`) | businessman | doanh nhân Phạm Hồng Sơn | 14 | 2 | wrong_person 12, name_mismatch 3 |
| 10 | Phan Văn Hưng (`phan-van-hung-startup`) | businessman | doanh nhân Phan Văn Hưng | 17 | 3 | wrong_person 14, name_mismatch 13 |
| 11 | Phạm Vấn (`pham-van`) | historic | lịch sử Phạm Vấn | 5 | 1 | name_mismatch 4 |
| 12 | Phạm Văn (`pham-van-dich-gia`) | writer | nhà văn Phạm Văn | 13 | 3 | wrong_person 8, no_person 2 |
| 13 | Lê Ngọc Lâm (`scope-5-le-ngoc-lam`) | businessman | doanh nhân Lê Ngọc Lâm | 13 | 3 | name_mismatch 10, wrong_person 10 |
| 14 | Phan Văn Đạt (`phan-van-dat`) | historic | lịch sử Phan Văn Đạt | 4 | 1 | name_mismatch 2, wrong_person 2 |
| 15 | Khánh Linh (`scope-5-khanh-linh-2`) | singer | nghệ sĩ Khánh Linh | 8 | 2 | name_mismatch 6, wrong_person 6 |
| 16 | Thanh Tâm (`thanh-tam-nhac-si`) | singer | nghệ sĩ Thanh Tâm | 15 | 4 | name_mismatch 11, wrong_person 10 |
| 17 | Phạm Thị Yến (`pham-thi-yen`) | athletes | vận động viên Phạm Thị Yến | 11 | 3 | wrong_person 8 |
| 18 | NSND Trần Khánh (`nsnd-tran-khanh-opera-thinh-phong`) | singer | nghệ sĩ NSND Trần Khánh | 14 | 4 | wrong_person 10, name_mismatch 1 |
| 19 | Phan Công Đức (`phan-cong-duc-bong-chuyen`) | athletes | vận động viên Phan Công Đức | 10 | 3 | wrong_person 7, name_mismatch 1 |
| 20 | Rosy (`rosy-ban-nhac-rock`) | singer | nghệ sĩ Rosy | 10 | 3 | wrong_person 6, not_prominent 1 |
| 21 | Phạm Thị Hương (`pham-thi-huong-para-co-vua`) | athletes | vận động viên Phạm Thị Hương | 16 | 5 | wrong_person 11, name_mismatch 3 |
| 22 | Phạm Văn Dòng (`pham-van-dong-dai-dong-tien`) | businessman | doanh nhân Phạm Văn Dòng | 14 | 5 | name_mismatch 5, wrong_person 5 |
| 23 | Quỳnh Anh (`quynh-anh-ca-si-sinh-1993`) | singer | nghệ sĩ Quỳnh Anh | 19 | 7 | wrong_person 12, name_mismatch 10 |
| 24 | Tuấn Anh (`scope-23-tuan-anh`) | singer | nghệ sĩ Tuấn Anh | 8 | 3 | wrong_person 5 |
| 25 | Ninh Tốn (`ninh-ton`) | historic | lịch sử Ninh Tốn | 5 | 2 | name_mismatch 3 |
| 26 | Phạm Thị Hoài (`pham-thi-hoai-dich-gia`) | scientist | nhà khoa học Phạm Thị Hoài | 5 | 2 | name_mismatch 3, wrong_person 3 |
| 27 | Riot Bigiman (`riot-bigiman`) | celeb | chân dung Riot Bigiman | 5 | 2 | wrong_person 3 |
| 28 | Thu Hà (`thu-ha-dan-ca`) | singer | nghệ sĩ Thu Hà | 20 | 8 | wrong_person 12, name_mismatch 10 |
| 29 | Thảo Phương (`thao-phuong`) | writer | nhà văn Thảo Phương | 7 | 3 | wrong_person 4, name_mismatch 4 |
| 30 | Ninh Viết Giao (`ninh-viet-giao-van-hoa`) | scientist | nhà khoa học Ninh Viết Giao | 2 | 1 | wrong_person 1 |
| 31 | Phạm Đỗ Chí (`pham-do-chi-kinh-te-imf`) | scientist | nhà khoa học Phạm Đỗ Chí | 12 | 6 | wrong_person 5, name_mismatch 1 |
| 32 | Phạm Minh Hoàng (`pham-minh-hoang`) | politicer | chính khách Phạm Minh Hoàng | 18 | 9 | wrong_person 9, name_mismatch 1 |
| 33 | Phan Hồng Giang (`phan-hong-giang-nghien-cuu-dich-gia`) | scientist | nhà khoa học Phan Hồng Giang | 14 | 7 | wrong_person 7, name_mismatch 6 |

## Nhóm 3. Chỉ còn 1–2 ảnh approved (5)

| # | Entity (slug) | Category | Query | Ảnh | Approved | Lý do loại chính |
|---|---|---|---|---|---|---|
| 1 | Phạm Đình Trọng (`pham-dinh-trong`) | historic | lịch sử Phạm Đình Trọng | 2 | 2 | — |
| 2 | Thắng (solo) (`thang-solo`) | singer | nghệ sĩ Thắng (solo) | 2 | 2 | — |
| 3 | The Flob (`the-flob`) | singer | nghệ sĩ The Flob | 2 | 2 | — |
| 4 | Phan Bá Vành (`phan-ba-vanh`) | historic | lịch sử Phan Bá Vành | 1 | 1 | — |
| 5 | Quốc Trụ (`quoc-tru-nha-giao`) | scientist | nhà khoa học Quốc Trụ | 1 | 1 | — |

## Nhóm 4. ≥ 30% ảnh không tải được (8)

| # | Entity (slug) | Category | Ảnh | Không tải được |
|---|---|---|---|---|
| 1 | Te (`te`) | athletes | 1 | 1 |
| 2 | The Flob (`the-flob`) | singer | 2 | 1 |
| 3 | Tôn Thất Bách (`ton-that-bach`) | scientist | 22 | 9 |
| 4 | Thân Trọng Tiết (`than-trong-tiet-ts-khoa-1849`) | historic | 5 | 2 |
| 5 | Thu Hà (`thu-ha-dan-ca`) | singer | 20 | 8 |
| 6 | Tô Trân (`to-tran-su-hoc`) | scientist | 3 | 1 |
| 7 | Tôn Thất Tế (`ton-that-te`) | historic | 15 | 5 |
| 8 | Trần Bắc Hà (`tran-bac-ha-bidv`) | businessman | 18 | 6 |
