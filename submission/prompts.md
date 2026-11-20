# Dùng AI

| # | Ai dùng | Công cụ | Prompt (tóm tắt) | AI sai ở đâu | Nhóm kiểm lại thế nào |
|---|---|---|---|---|---|
| 1 | Trương Duy Anh | Claude Code (Claude Opus 5.5) | "Đọc folder này" — tóm tắt đề, các pha, rubric | — | Đối chiếu với README/GUIDE/RUBRIC |
| 2 | Trương Duy Anh | Claude Code | "Tải dữ liệu và tạo lô" (seed 7007 = nhóm 07 × 1000 + 7) | — | Kiểm `runs/r7007/delivery` có đủ file, lineage có `R-021` |
| 3 | Trương Duy Anh | Claude Code | "Viết validator" — 9 lỗi luật + sinh ứng viên đối chiếu det ↔ panoptic | Bản đầu dùng IoU bbox ≥ 0.7 làm tiêu chí khớp → báo nhầm `instance_merge` ở ảnh đám đông (2685, 4134): box to hơn segment do vật bị che. Bản đầu bỏ sót `missing_box` ảnh 785 (xét cả box khác lớp) và ca gộp người nằm trong bbox người khác (23899). | Chạy lô sạch (phải 0 ứng viên); so tín hiệu giữa seed 7007/11/23 (lặp lại ở mọi seed = tự nhiên); đổi sang tín hiệu tỉ lệ pixel segment trong box; thêm luật box mồ côi. Lỗi luật F1 ≈ 1.0 trên 4 lô. |
| 4 | Trương Duy Anh | Claude Code | "Viết công cụ vẽ box" (`tools/review_view.py`, Pillow) | — | Mở thử ảnh 23899, 23126: box/segment vẽ đúng vị trí |
| 5 | Hà Tiến Trịnh | Claude Code (Claude Opus 5.5) | "Đọc repo và hướng dẫn tôi làm bài lab" — tóm tắt đề, 6 pha, rubric, lệnh chạy trên Windows | Không phát hiện sai | Đối chiếu với README, GUIDE, RUBRIC, RULES, SUBMISSION, docs/DELIVERY.md |
| 6 | Hà Tiến Trịnh | Claude Code | "git pull rồi import submission/r7007", "chạy review_view" | — | Lô tạo lại có `release_id` = `lab250_20c5f74a77e2`, khớp bản gốc; `score_findings.py` ra F1 tổng ≈ 1.0 như REPORT. AI chỉ tạo ảnh review, **không xem ảnh và không kết luận review** (RULES) |
| 7 | Đinh Trường Phong | Antigravity (Gemini 3.8 Flash) | "Viết script tools/build_handover.py đóng gói lô detection v2, tạo 7 thành phần, đóng gói sha256 và ghi lineage" | Cần chú ý phân loại: nhầm ảnh chỉ lỗi panoptic vào rework_queue | Đối chiếu GUIDE.md Pha 4: ảnh lỗi panoptic giữ lại v2; kiểm tra bằng `check_handover.py` đạt PASS tuyệt đối từ H1 đến H15 |
| 8 | Nguyễn Trường An | glm-5.3| Kiểm tra mọi người đã hoàn thành các pha được giao chưa | AI đọc commit và kiểm tra | Đối chiếu kết quả rồi hoàn thành nốt báo cáo pha 6 |




Ghi chú: ảnh COCO là dữ liệu công khai, được phép hỏi AI (RULES). ;
kết luận cuối trong `review_log.csv` do thành viên nhóm kiểm lại bằng mắt và ký tên.
