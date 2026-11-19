# Nhóm 07

- Seed luyện tập: **7007**
- Repo: https://github.com/duyanh211105/K5-L23-DAY10-NHOM7-Release

## Thành viên

| # | Họ và tên | MSHV | Tài khoản GitHub | Phần chính |
|---|---|---|---|---|
| 1 | Trương Duy Anh | 2A202603027 | duyanh211105 | Pha 0–2: chuẩn bị dữ liệu, validator lỗi luật, đối chiếu detection ↔ panoptic, công cụ xem ảnh, gom review |
| 2 | Hà Tiến Trinh | <<MSHV>> | <<github>> | Pha 3–4: quyết định HOLD, lineage, bàn giao v2 |
| 3 | Đinh Trường Phong | <<MSHV>> | <<github>> | Pha 3–4: bàn giao v2, đóng gói, `check_handover.py` |
| 4 | Nguyễn Hoàng Việt Anh | <<MSHV>> | <<github>> | Pha 5–6: truy vết ticket `trace.json`, đề ẩn |
| 5 | Nguyễn Trường An | <<MSHV>> | <<github>> | Pha 5–6: `security.md`, đề ẩn, `REPORT.md` |

## Chia việc theo pha

| Pha | Việc | Phụ trách | Hỗ trợ |
|---|---|---|---|
| 0 | Tải dữ liệu, tạo lô seed 7007 và lô sạch `runs/clean` | Trương Duy Anh | |
| 1 | `validator/validate.py`: 9 lỗi luật, thử trên lô sạch và seed phụ (11, 23, opaque) | Trương Duy Anh | |
| 2 | Sinh ứng viên `--candidates`, `tools/review_view.py`, `tools/check_review.py`, gộp `merge_review.py` | Trương Duy Anh | |
| 2 | **Xem ảnh ứng viên — cả 5 người**, ghi `review_log.csv` | cả nhóm | |
| 3 | Tỉ lệ lỗi v1, quyết định HOLD, `lineage.py record` + `impact` | Hà Tiến Trinh | Đinh Trường Phong |
| 4 | Lô v2: `rework_queue`, manifest, label_summary, truyvet, README | Hà Tiến Trinh | Đinh Trường Phong |
| 4 | Đóng gói `pack_release.py`, lineage release v2, `check_handover.py` hết FAIL | Đinh Trường Phong | Hà Tiến Trinh |
| 5 | `trace.json` (tier_a / tier_b / notify) theo guideline của job | Nguyễn Hoàng Việt Anh | Nguyễn Trường An |
| 6 | `security.md` (ca USB, 5 việc được/không, ca khuôn mặt) | Nguyễn Trường An | Nguyễn Hoàng Việt Anh |
| 6 | Đề ẩn 40 phút | cả nhóm | |
| Nộp | `REPORT.md`, `prompts.md`, `export_submission.py` | Nguyễn Trường An | cả nhóm |

## Review seed 7007 (9 ứng viên trong `candidates.json`)

| Người xem | Ảnh | Kết luận |
|---|---|---|
| Trương Duy Anh | 000000013177, 000000006471 | class_swap, category_swap — confirmed |
| Hà Tiến Trinh | 000000023899 | instance_merge — confirmed |
| Nguyễn Trường An | 000000015079, 000000023126 | instance_merge, bbox_drift — confirmed |
| Đinh Trường Phong | 000000000785, 000000001818 | missing_box — confirmed; bbox_drift — rejected |
| Nguyễn Hoàng Việt Anh | 000000012748, 000000000872 | bbox_drift — rejected (cả hai) |

Tổng: 6 confirmed, 3 rejected. Mỗi dòng trong `review_log.csv` ghi **thấy gì** trong ảnh và tên người xem ở cuối note.

## Kế hoạch đề ẩn (40 phút)

| Thời gian | Việc | Người làm |
|---|---|---|
| 0–5' | Giải nén `de_an.zip`, chạy `validator/validate.py` và `tools/review_view.py` | Trương Duy Anh |
| 5–30' | Chia hàng đợi, cả 5 người xem ảnh, ghi `submission/de_an/review_log.csv` | cả nhóm |
| 5–30' | Làm `submission/de_an/trace.json` (song song) | Nguyễn Hoàng Việt Anh |
| 30–35' | `check_review.py` → `merge_review.py` → `errors.json` | Trương Duy Anh |
| 35–40' | Kiểm `submission/de_an/`, commit + push (không commit `delivery/`) | Nguyễn Trường An |
