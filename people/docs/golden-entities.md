# Golden set: 50 entity (664 ảnh)

## Đợt 1: 10 entity chọn tay (156 ảnh)

Chọn trong phạm vi dòng 13329 đến hết của [approved-results.csv](approved-results.csv). Duyệt theo [golden-guideline.md](golden-guideline.md).

| # | slug | canonical_name | category | Dòng | Số ảnh | Kiểm tra điều gì | Dự đoán (chỉ dựa trên tiêu đề, chưa xem ảnh) |
|---|------|---------------|----------|------|-------|------------------|------------------|
| 1 | `tuan-duong-btv-vtv` | Tuấn Dương | celeb | 20557–20576 | 20 | Ca dễ làm mốc: tiêu đề gần như đều đúng tên | Phần lớn approved |
| 2 | `nhat-phong` | Nhật Phong | singer | 14452–14464 | 13 | Ca dễ: chân dung một người | Phần lớn approved |
| 3 | `vua-ham-nghi` | Vua Hàm Nghi | historic | 21756–21768 | 13 | Ảnh cũ, tranh vẽ, tượng của nhân vật lịch sử | Lẫn approved/rejected |
| 4 | `phan-hien` | Phan Hiển | athletes | 15886–15900 | 15 | Ảnh nhiều người (93% ≥ 2 mặt, chủ yếu chụp cùng vợ Khánh Thi): rule "nổi bật" | Nhiều rejected `not_prominent` |
| 5 | `nhom-ac-m` | Nhóm AC&M | singer | 14496–14510 | 15 | Entity nhóm nhạc: rule "đủ thành viên" | Lẫn; dùng để chốt ngưỡng thành viên |
| 6 | `truong-my-lan-cuu-chu-tich-van-thinh-phat` | Trương Mỹ Lan | businessman | 20429–20443 | 15 | Đúng người nhưng nhiều ảnh tại tòa, bị bắt: rule `sensitive` theo nội dung ảnh | Nhiều rejected `sensitive` |
| 7 | `phuong-loan` | Phương Loan | singer | 16305–16319 | 15 | Lẫn **Phương Loan** (ca sĩ) và **Phượng Loan** (NSƯT cải lương): khác dấu | Nhiều rejected `name_mismatch` |
| 8 | `tran-van-khanh` | Trần Văn Khánh | scientist | 19877–19889 | 13 | Lẫn **Trần Văn Khánh**, **Trần Vân Khánh**, **Trần Văn Khanh** | Nhiều rejected `name_mismatch` |
| 9 | `nhu-binh` | Như Bình | writer | 14534–14551 | 18 | Nhà văn Như Bình lẫn nữ MC, ca sĩ Như Bình, VĐV bóng chuyền | Nhiều rejected `wrong_person` |
| 10 | `nguyen-viet-thanh` | Nguyễn Viết Thanh | politicer | 13941–13959 | 19 | Gần như toàn bộ là nhà văn **Viet Thanh Nguyen** (Mỹ), không phải chính khách | Có thể rejected cả entity (`wrong_person` / `unresolved`) |

**Độ phủ:** đủ 8 category · 2 ca dễ · 1 nhóm nhạc · 1 nhân vật lịch sử · 1 ca nhiều người · 1 ca nhạy cảm · 4 ca danh tính khó (khác dấu, trùng tên, sai người cả entity).

**Lưu ý:**
- Đợt này cố ý nhiều ca khó để **thử guideline**. Tỉ lệ rejected sẽ cao hơn dữ liệu thật, nên chưa dùng đợt này để ước lượng tỉ lệ approved chung.

## Đợt 2: 40 entity (508 ảnh)

Sinh bằng `python tools/select_golden.py` (seed cố định): **30 ngẫu nhiên** phân tầng theo category để đại diện cho dữ liệu, **10 chọn có chủ đích** để có thêm ca loại cho việc đo rule.

| # | slug | canonical_name | category | Dòng | Số ảnh | Lý do chọn |
|---|------|---------------|----------|------|-------|-----------|
| 11 | `quoc-dai` | Quốc Đại | singer | 16522–16534 | 13 | ngẫu nhiên |
| 12 | `thang-solo` | Thắng (solo) | singer | 17847–17853 | 7 | ngẫu nhiên |
| 13 | `nhac-si-thai-co` | Nhạc sĩ Thái Cơ | singer | 14309–14327 | 19 | ngẫu nhiên |
| 14 | `scope-5-hieuthuhai` | HIEUTHUHAI | singer | 17174–17191 | 18 | ngẫu nhiên |
| 15 | `wean-le` | Wean Lê | singer | 21892–21906 | 15 | ngẫu nhiên |
| 16 | `wukong-rapper` | Wukong | singer | 21938–21954 | 17 | ngẫu nhiên |
| 17 | `viet-khang` | Việt Khang | singer | 20871–20879 | 9 | ngẫu nhiên |
| 18 | `pham-dinh-trong` | Phạm Đình Trọng | historic | 14963–14968 | 6 | ngẫu nhiên |
| 19 | `tinh-khong-thien-su` | Tịnh Không (thiền sư) | historic | 18257–18265 | 9 | ngẫu nhiên |
| 20 | `pham-nguyen-du` | Phạm Nguyễn Du | historic | 15246–15252 | 7 | ngẫu nhiên |
| 21 | `vu-vi-pho-bang-khoa-1901` | Vũ Vĩ | historic | 21705–21710 | 6 | ngẫu nhiên |
| 22 | `tran-thi-hai-linh` | Trần Thị Hải Linh | athletes | 19577–19589 | 13 | ngẫu nhiên |
| 23 | `vu-thi-nguyet-anh` | Vũ Thị Nguyệt Ánh | athletes | 21622–21637 | 16 | ngẫu nhiên |
| 24 | `patrik-le-giang` | Patrik Lê Giang | athletes | 14832–14845 | 14 | ngẫu nhiên |
| 25 | `tran-nguyen-bao-chau` | Trần Nguyễn Bảo Châu | athletes | 19186–19192 | 7 | ngẫu nhiên |
| 26 | `nguyen-van-hong-can-tho` | Nguyễn Văn Hồng | politicer | 13359–13376 | 18 | ngẫu nhiên |
| 27 | `vo-van-hung` | Võ Văn Hưng | politicer | 21170–21182 | 13 | ngẫu nhiên |
| 28 | `pham-the-tung` | Phạm Thế Tùng | politicer | 15404–15418 | 15 | ngẫu nhiên |
| 29 | `pham-chuyen` | Phạm Chuyên | politicer | 14921–14934 | 14 | ngẫu nhiên |
| 30 | `thanh-thanh-huyen` | Thanh Thanh Huyền | celeb | 17953–17971 | 19 | ngẫu nhiên |
| 31 | `phan-phuong-oanh` | Phan Phương Oanh | celeb | 15926–15940 | 15 | ngẫu nhiên |
| 32 | `phuong-linh-a-hau-miss-international` | Phương Linh | celeb | 16290–16304 | 15 | ngẫu nhiên |
| 33 | `pham-cong-thien-triet-gia-hoc-gia` | Phạm Công Thiện | scientist | 14943–14949 | 7 | ngẫu nhiên |
| 34 | `phan-hong-giang-nghien-cuu-dich-gia` | Phan Hồng Giang | scientist | 15901–15914 | 14 | ngẫu nhiên |
| 35 | `vu-hai-quan` | Vũ Hải Quân | scientist | 21383–21396 | 14 | ngẫu nhiên |
| 36 | `phan-van-hung-startup` | Phan Văn Hưng | businessman | 16115–16131 | 17 | ngẫu nhiên |
| 37 | `to-manh-cuong-mobifone` | Tô Mạnh Cường | businessman | 18293–18306 | 14 | ngẫu nhiên |
| 38 | `tran-thi-le` | Trần Thị Lệ | businessman | 19606–19616 | 11 | ngẫu nhiên |
| 39 | `tran-ninh-ho` | Trần Ninh Hồ | writer | 19193–19205 | 13 | ngẫu nhiên |
| 40 | `pham-xuan-truong` | Phạm Xuân Trường | writer | 15822–15833 | 12 | ngẫu nhiên |
| 41 | `tran-luu` | Trần Lựu | historic | 18985–18993 | 9 | tên khác dấu |
| 42 | `tho-nguyen-tho-nguyen` | Tho Nguyen | celeb | 18108–18123 | 16 | tên khác dấu |
| 43 | `nguyen-xuan-son-sonx` | Nguyễn Xuân Sơn | singer | 14097–14115 | 19 | tên khác dấu |
| 44 | `nguyen-van-luyen-y-hoc` | Nguyễn Văn Luyện | scientist | 13501–13510 | 10 | tiêu đề hiếm khi nhắc tên |
| 45 | `nguyen-van-quyen` | Nguyễn Văn Quyến | athletes | 13620–13637 | 18 | tiêu đề hiếm khi nhắc tên |
| 46 | `van-dong-vien-cu-ta` | Vận động viên cử tạ | athletes | 20685–20694 | 10 | nhiều mặt rất nhỏ |
| 47 | `tu-do-ban-nhac-rock` | Tự Do | singer | 20533–20538 | 6 | nhiều mặt rất nhỏ |
| 48 | `thuy-linh-5-dong-ke` | Thùy Linh (5 Dòng Kẻ) | singer | 18207–18220 | 14 | nhiều ảnh đông người |
| 49 | `scope-5-da-lab` | Da LAB | singer | 17068–17079 | 12 | nhiều ảnh đông người |
| 50 | `tran-quoc-toan-cu-ta` | Trần Quốc Toàn (cử tạ) | athletes | 19348–19354 | 7 | tiêu đề có từ khóa bắt/xử |

**Lưu ý đợt 2:**
- `tho-nguyen-tho-nguyen`: `canonical_name` là "Tho Nguyen" **không dấu**, nên tool sẽ báo "khác dấu" với mọi tiêu đề "Thơ Nguyễn". Đây là cảnh báo giả; xét theo người trong ảnh.
- `van-dong-vien-cu-ta`: `canonical_name` là "Vận động viên cử tạ", không phải tên người cụ thể. Có thể phải loại cả entity (`unresolved`).
- 1 ảnh có link chết (dòng 18263, `tinh-khong-thien-su`): rejected · `no_person` theo quy ước "ảnh tải lỗi → rejected".
