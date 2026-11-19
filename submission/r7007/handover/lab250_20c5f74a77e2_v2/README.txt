Release: lab250_20c5f74a77e2_v2
Parent: lab250_20c5f74a77e2
Số ảnh: 242
Số nhãn: 1691
Guideline: v1.2 (J01-J04), v1.3 (J05-J10)
QC v1: 18/250 = 7.2%
Kết luận v1: Hold — Lô v1 có tỉ lệ lỗi QC là 18/250 (7.2%) vượt ngưỡng 2% (ngưỡng Day 7)
Kết luận v2: Release — Đã tách 8 ảnh lỗi detection sang rework_queue.csv, chuẩn hóa split cảnh scene_593, chuẩn hóa guideline theo job, cập nhật hash manifest cho ảnh 000000016010
Ghi chú: Lô v2 là sản phẩm detection sạch giao cho team AI huấn luyện. 8 ảnh lỗi detection đã chuyển sang rework_queue.csv giao đúng người gán và kiểm tra theo jobs.csv để gán lại. 6 ảnh lỗi chỉ ở panoptic (000000006471, 000000011511, 000000015079, 000000018491, 000000018833, 000000023899) nhãn detection vẫn chính xác nên được giữ lại trong v2; đã bàn giao danh sách cho team panoptic xử lý. Cảnh scene_593 đã đưa toàn bộ về split train để loại bỏ rò rỉ dữ liệu. Ảnh 000000016010 đã mở kiểm tra nguyên vẹn và cập nhật sha256 đúng vào manifest.csv.
