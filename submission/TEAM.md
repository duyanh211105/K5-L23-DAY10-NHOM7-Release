# Nhóm 07

- Seed luyện tập: 7007
- Repo: https://github.com/duyanh211105/K5-L23-DAY10-NHOM7-Release

| # | Họ và tên | MSHV | Tài khoản GitHub | Phần chính |
|---|---|---|---|---|
| 1 | Trương Duy Anh | 2A202603027 | duyanh211105 | Validator luật (Pha 1) + chuẩn bị dữ liệu (Pha 0) |
| 2 | Hà Tiến Trinh | <<MSHV>> | <<github>> | Đối chiếu det ↔ panoptic, công cụ xem ảnh (Pha 2) |
| 3 | Nguyễn Trường An | <<MSHV>> | <<github>> | Review ảnh, chốt `errors.json`, `REPORT.md` (Pha 2–3) |
| 4 | Đinh Trường Phong | <<MSHV>> | <<github>> | Bàn giao v2, lineage, `check_handover.py` (Pha 3–4) |
| 5 | Nguyễn Hoàng Việt Anh | <<MSHV>> | <<github>> | Truy vết ticket `trace.json` + `security.md` (Pha 5–6) |

## Chia việc theo pha

| Pha | Việc | Phụ trách | Hỗ trợ |
|---|---|---|---|
| 0 | Tải dữ liệu, tạo lô seed 7007, lô sạch `runs/clean` | TV1 | |
| 1 | `validator/validate.py`: 9 lỗi luật, thử trên lô sạch và seed phụ | TV1 | TV2 |
| 2 | Phần `--candidates` (đối chiếu pixel mask), `tools/review_view.py` | TV2 | TV1 |
| 2 | **Xem ảnh ứng viên — cả 5 người** (chia hàng đợi bên dưới), ghi `review_log.csv` | TV3 | tất cả |
| 3 | Tỉ lệ lỗi v1, quyết định HOLD, `lineage.py impact` | TV4 | TV3 |
| 4 | Lô v2: `rework_queue`, manifest, label_summary, truyvet, README, đóng gói | TV4 | TV1 |
| 5 | `trace.json` (tier_a / tier_b / notify) theo guideline của job | TV5 | TV4 |
| 6 | `security.md`; đề ẩn 40' (cả nhóm) | TV5 | tất cả |
| — | `REPORT.md`, `prompts.md`, `export_submission.py` | TV3 | tất cả |

## Chia hàng đợi review seed 7007 (9 ứng viên trong `runs/r7007/candidates.json`)

| Người xem (thực tế, theo `review_log.csv`) | Ảnh | Kết luận |
|---|---|---|
| Trương Duy Anh | 000000013177, 000000006471 | class_swap, category_swap — confirmed |
| Hà Tiến Trinh | 000000023899 | instance_merge — confirmed |
| Nguyễn Trường An | 000000015079, 000000023126 | instance_merge, bbox_drift — confirmed |
| Đinh Trường Phong | 000000000785, 000000001818 | missing_box confirmed; bbox_drift rejected |
| Nguyễn Hoàng Việt Anh | 000000012748, 000000000872 | bbox_drift rejected (cả hai) |

Mỗi dòng trong `review_log.csv` ghi rõ ai xem (tên người xem ở cuối note) và **thấy gì** trong ảnh.

## Đề ẩn (40 phút)

- 0–5': TV1 chạy validator, TV2 chạy `tools/review_view.py`.
- 5–30': cả 5 người chia hàng đợi xem ảnh, TV3 gom `review_log.csv` → `merge_review.py`.
- 5–30' (song song): TV5 làm `trace.json` cho đề ẩn.
- 30–40': TV4 kiểm `submission/de_an/`, commit + push.
