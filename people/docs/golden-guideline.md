# Hướng dẫn gán nhãn golden dataset

Mỗi ảnh nhận **một** nhãn: `approved` hoặc `rejected`.
**Nguyên tắc chung: không chắc → `rejected`.** Thà loại nhầm ảnh tốt còn hơn duyệt nhầm ảnh xấu.

## 1. Trước khi duyệt một entity

1. Đọc `canonical_name` và `category` (vd ca sĩ, chính trị gia, nhân vật lịch sử).
2. Xem nhanh **tất cả ảnh** của entity, đọc `description` (tiêu đề trang) và `source_url`.
3. Xác định **người đúng**: dựa vào các ảnh có tiêu đề nêu **đúng tên đầy đủ, đúng dấu** và đúng nghề/vai trò.
   **Quy ước tên chặt:** `canonical_name` là chuẩn, không đoán là gõ sai. Người khác dấu hoặc khác vai trò là người khác, kể cả khi họ chiếm đa số ảnh.
4. Không xác định được người đúng (vd tên trùng nhiều người, không ảnh nào có tên khớp) → **toàn bộ ảnh của entity `rejected`**, lý do `unresolved`.

## 2. Rule cứng: sai một điều là `rejected`, không ngoại lệ

| Mã | Rule |
|----|------|
| `wrong_person` | Người trong ảnh **không phải** entity: người trùng tên, người thân, người đứng cạnh, hoặc **không chắc** là entity. |
| `wrong_person` (vai trò) | Đúng tên nhưng **sai vai trò** so với `category`/`query` (vd query "chính khách" mà ảnh là nhà văn; category "singer" mà ảnh là cầu thủ). |
| `name_mismatch` | Tiêu đề/URL nói về **người khác**: tên khác, **khác dấu** ("Hạ Vy" ≠ "Hà Vy", "Văn" ≠ "Vân", "Sơn" ≠ "Son"), hoặc chỉ người có quan hệ ("con trai của…", "vợ của…"). **Không** tính là sai lệch: tiêu đề không nhắc tên; tiêu đề viết **không dấu** ("WEAN LE", "Phuong Linh"); tên gốc không dấu ("Tho Nguyen"); đảo thứ tự tên kiểu tiếng Anh nếu đúng người. |
| `no_person` | Không có người thật; ảnh lỗi, không mở được. |
| `sensitive` | Lộ vùng nhạy cảm · bạo lực · **chính bức ảnh** thể hiện cảnh bắt giữ, còng tay, tòa án · sự kiện chính trị nhạy cảm (biểu tình, xét xử, bê bối, biểu tượng nhạy cảm). |

**Không** tính là nhạy cảm: người mẫu mặc đồ ít vải nhưng không lộ vùng nhạy cảm; ảnh chân dung bình thường nằm trong bài báo tiêu cực; chính trị gia trong ảnh chân dung, hội nghị, sự kiện thông thường.

## 3. Tiêu chí chất lượng: không đạt là `rejected`

| Mã | Đạt khi |
|----|---------|
| `not_clear` | Nhìn rõ người: không mờ, không quá tối/cháy sáng. |
| `too_small` | Người đủ lớn: nhận ra nét mặt **mà không cần phóng to**. (Ngưỡng số sẽ chốt sau pilot.) |
| `not_prominent` | Ảnh nhiều người: entity **nổi bật, dễ nhận ra ngay** (mặt to nhất hoặc ngang to nhất, là tâm điểm). Là một người lẫn trong đám đông → không đạt. |
| `hard_to_identify` | Không bị che khuất nhiều, không đồ che kín; không phải ảnh ghép, ảnh AI; không chỉnh sửa, hiệu ứng, nhiễu, chữ/logo đến mức khó nhận ra người. |

## 4. Trường hợp đặc biệt

- **Nhóm / ban nhạc:** `approved` khi ảnh có **phần lớn thành viên** và nhìn rõ (ngưỡng chốt sau pilot). Ảnh chỉ một thành viên → `rejected` · `not_prominent`.
- **Nhân vật lịch sử:** tranh vẽ, tượng, ảnh đen trắng cũ được `approved` nếu đúng người và qua các tiêu chí trên.
- **Ảnh trùng / gần trùng:** gán nhãn bình thường, không loại vì trùng.

## 5. Thứ tự kiểm tra mỗi ảnh

```
Có người thật?            không → rejected (no_person)
Đúng entity, chắc chắn?   không / không chắc → rejected (wrong_person)
Tiêu đề nói người khác?   có → rejected (name_mismatch)
Nhạy cảm?                 có → rejected (sensitive)
Rõ, đủ lớn, nổi bật, dễ nhận diện?   không → rejected (mã tương ứng)
                          tất cả đạt → approved
```

## 6. Ghi nhãn

| Cột | Giá trị |
|-----|---------|
| `flag` | `approved` / `rejected` |
| `reasons` | mã lý do (có thể nhiều, ngăn bằng `;`); để trống nếu `approved` |
| `identity` | `match` / `other` / `unsure`: người chính trong ảnh có phải entity không |
| `note` | ghi chú ngắn khi phân vân |

**Tự kiểm tra (một người gán):** sau vài ngày, gán lại **mù** khoảng 10% ảnh (không xem nhãn cũ). Ảnh có nhãn khác lần trước được xem lại để sửa hướng dẫn này cho rõ.
