# Báo cáo nhóm 07

## 1. Số liệu luyện tập

### F1 tự đo (`score_findings.py`, làm tròn 1 chữ số)

| Lô | Cách tạo | Lỗi luật báo | F1 luật | F1 gán nhãn | F1 tổng |
|---|---|---:|---|---|---|
| r7007 (seed luyện tập) | `run_lab.py --seeds 7007` | 12 | ≈ 1.0 | **≈ 0.9** (sau review) | **≈ 1.0** |
| r11 (seed phụ) | `inject_release.py --seed 11` | 13 | ≈ 1.0 | (*) | |
| r23 (seed phụ) | `inject_release.py --seed 23` | 8 | ≈ 1.0 | (*) | |
| opq (mô phỏng đề ẩn) | `inject_release.py --seed 99 --opaque` | 11 | ≈ 1.0 | (*) | |
| clean (lô sạch) | `inject_release.py --seed 5 --no-faults` | 0 | 1.0 (không báo thừa) | 1.0 | 1.0 |

(*) Seed phụ chỉ dùng để đo **độ phủ của bộ sinh ứng viên**: gộp thẳng ứng viên ưu tiên cao vào errors.json
(không review) được F1 gán nhãn ≈ 0.6 (r11), 0.9 (r23), 0.8 (opq). Phần sai còn lại chủ yếu là **chiều swap**
(`class_swap` vs `category_swap`), thứ dữ liệu không phân biệt được — chỉ mở ảnh mới biết. Không dùng các số này
làm kết quả review; seed luyện tập 7007 được review bằng mắt.

Lỗi luật r7007: missing_image 1, wrong_hash 1, invalid_class 2, bbox_out_of_bounds 1, duplicate_box 1,
scene_leak 1, guideline_mismatch 2, invalid_category_id 2, thing_overlap 1.

### Nhiễu tự nhiên và hàng đợi

- Số ứng viên trên lô sạch (`--no-faults`, 50 ảnh calib): **0**.
- Hàng đợi trên seed luyện tập: **9 ảnh** (2 swap, 2 instance_merge, 4 bbox_drift, 1 missing_box).
- Ứng viên xuất hiện ở **mọi** seed thử (7007, 11, 23) dù lỗi gài đổi theo seed: 000000000872, 000000001818,
  000000012748 → dấu hiệu lệch tự nhiên của COCO. Validator xếp chúng cuối hàng đợi (box khác kích thước segment).

### Ngưỡng đã chọn và cách chọn (không dùng `_private`)

Tín hiệu chính là **cov = tỉ lệ pixel của segment nằm trong box** (không phải IoU bbox):

| Ngưỡng | Giá trị | Lý do |
|---|---|---|
| `OK_COV` | 0.97 | Ở COCO sạch, box chứa ~100% pixel segment kể cả khi vật bị che (segment nhỏ lại nhưng vẫn trong box). Lô sạch: 0 segment dưới 0.97. |
| `DRIFT_COV_MIN` | 0.20 | Box cùng lớp chứa 20–97% pixel → cùng vật nhưng lệch (`bbox_drift`). |
| `DRIFT_SIZE_TOL` | 6% | Box lệch thật giữ kích thước, chỉ dịch tâm; box khác kích thước nhiều → nhiều khả năng che khuất/cách vẽ, ưu tiên thấp. |
| `SWAP_IOU` / `SWAP_COV` | 0.75 / 0.90 | Box khác lớp trùng vị trí segment, box đó không có segment cùng lớp nào. |
| `MERGE_*` | mỗi box ≥ 15%, tổng ≥ 80%, không box nào ≥ 90% | Segment trải qua ≥ 2 box cùng lớp. Thêm luật "box mồ côi nằm trong segment cùng lớp của box khác" (ca 23899: người thứ 2 nằm gọn trong bbox người thứ 1). |
| `MISSING_MIN_PX` | 0.3% ảnh | Segment đáng kể không có box cùng lớp; bỏ segment `iscrowd`. |
| `MIN_SEG_PX` | 0.1% ảnh | Segment quá nhỏ: lệch 1 px đã làm cov tụt. |
| `DUP_*` (luật) | cùng lớp, w/h chênh ≤ 1 px, tâm lệch ≤ 3 px | Không dùng IoU vì COCO có cặp box tự nhiên chồng nhau tới IoU ~0.66. |
| `OOB_TOL_PX` (luật) | 0.5 px | Tránh báo nhầm do làm tròn 6 chữ số của YOLO. |

Cách chọn: (1) chạy trên lô sạch phải ra 0 lỗi luật và 0 ứng viên; (2) so tín hiệu giữa nhiều seed — tín hiệu
lặp lại ở mọi seed là lệch tự nhiên; (3) hàng đợi phải đủ nhỏ để cả nhóm xem hết trong 40 phút đề ẩn (~10 ảnh).

## 2. Vì sao báo hết ứng viên làm F1 giảm?

F1 tính trên cặp `(type, target)`: mỗi cặp báo thừa (FP) kéo precision xuống y như mỗi cặp bỏ sót (FN) kéo
recall xuống. Số đo thật của nhóm trên seed 7007:

| Cách nộp | Số lỗi nộp | F1 gán nhãn | F1 tổng |
|---|---:|---|---|
| Nộp cả 9 ứng viên với type validator đoán, **không xem ảnh** | 21 | ≈ 0.6 | ≈ 0.8 |
| Sau khi **xem ảnh** (6 confirmed, 3 rejected) | 18 | ≈ 0.9 | ≈ 1.0 |

Báo hết thì bị trừ ở hai chỗ:
1. **Lệch tự nhiên thành FP.** 3 ứng viên 000000001818, 000000012748, 000000000872 khi xem ảnh là lệch sẵn có của
   COCO (ngựa vằn lớn bị cắt ở mép ảnh không có box riêng; box chỉ hụt đỉnh đầu; hai cầu thủ chồng lấn). Chúng
   xuất hiện ở mọi seed đã thử, trong khi lỗi gài đổi theo seed. Nộp chúng = 3 FP.
2. **Sai chiều swap thành vừa FP vừa FN.** Dữ liệu chỉ cho biết detection và panoptic bất đồng về lớp, không cho
   biết bên nào sai. Validator mặc định đoán `class_swap`; mở ảnh 000000006471 thấy vật là ghế băng trong dugout
   (detection ghi `bench` đúng, panoptic ghi `couch` sai) → phải là `category_swap`. Nộp sai type = 1 FP + 1 FN.

Xem ảnh loại được cả hai loại sai này; nên trên đề ẩn mọi lỗi gán nhãn đều phải có dòng `confirmed` ghi rõ thấy gì.

## 3. Quyết định và lineage

### QC v1 và kết luận

Lô v1 `lab250_20c5f74a77e2` (seed 7007), 250 ảnh. `errors.json` có **18 lỗi trên 18 target khác nhau**
(17 ảnh + cảnh `scene_593`). Mỗi ảnh mang nhiều nhất một lỗi; `scene_leak` tính là một ảnh.

| Nhóm | Số | Chi tiết |
|---|---:|---|
| Lỗi luật | 12 | missing_image 1, wrong_hash 1, invalid_class 2, bbox_out_of_bounds 1, duplicate_box 1, scene_leak 1, guideline_mismatch 2, invalid_category_id 2, thing_overlap 1 |
| Lỗi gán nhãn (đã `confirmed` bằng mắt) | 6 | class_swap 1, category_swap 1, instance_merge 2, bbox_drift 1, missing_box 1 |

**QC v1 = 18/250 = 7,2% > 2% → HOLD** (ngưỡng Day 7). Kể cả chỉ tính 12 lỗi luật (12/250 = 4,8%) lô vẫn vượt
ngưỡng, nên quyết định HOLD không phụ thuộc vào phần review bằng mắt.

Ngưỡng tính theo **tỉ lệ ảnh lỗi**, không theo số lỗi: 18 lỗi trên 250 ảnh khác hẳn 18 lỗi trên 10.000 ảnh. Tỉ lệ
cho biết model sẽ học bao nhiêu phần dữ liệu sai, và so sánh được giữa các lô có kích thước khác nhau.

### Lineage

```
py -X utf8 scripts/lineage.py record --event decision --release-id lab250_20c5f74a77e2 --decision HOLD
py -X utf8 scripts/lineage.py impact --release-id lab250_20c5f74a77e2
R-021: affected=True action=review_or_retrain
```

Chuỗi trong `lineage.jsonl`: `inject` (seed 7007) → `train` R-021 trên v1 → `decision` HOLD v1.
Pha 4 thêm `release` v2 với `parent` = v1.

### Vì sao R-021 phải xem lại hoặc train lại

R-021 đã train trên v1 **trước** khi QC. Trọng số của model đã học từ nhãn sai. HOLD v1 hay làm v2 chỉ đổi dữ liệu,
không đổi model đã train: R-021 vẫn mang các lỗi đó cho tới khi được đánh giá lại hoặc train lại.

Những gì R-021 đã học sai (theo `errors.json` và `review_log.csv` của nhóm):
- **Nhãn detection sai lớp hoặc vị trí:** 000000013177 xe đạp bị gán `motorcycle`; 000000023126 box `person` bị
  dịch xuống, cắt mất đầu; 000000000785 thiếu box `skis` (model học rằng ván trượt là nền); 000000020247 box lặp;
  000000016451 box tràn mép ảnh; 000000003845, 000000004765 có class_id ngoài 0–79 (tuỳ dataloader: lỗi khi train
  hoặc bị bỏ qua âm thầm).
- **Rò rỉ train/val:** `scene_593` có ảnh ở cả train và val. Ảnh cùng cảnh gần giống nhau nên điểm val của R-021 bị
  thổi phồng; không tin được số đánh giá đã báo.
- **Guideline cũ của lớp `truck`:** ticket của team AI (model bỏ sót `truck` bị che) khớp với thay đổi v1.2 → v1.3.
  Các job theo v1.2 được phép bỏ box `truck` bị che, nên R-021 đã học bỏ qua chúng (chi tiết ở mục 5).
- Lỗi chỉ ở panoptic (6 ảnh) không ảnh hưởng trực tiếp R-021 nếu run chỉ dùng nhãn detection.

Việc cần làm:
1. **Xem lại:** đánh giá R-021 trên tập val đã sửa (v2, không còn cảnh rò), tập trung vào các lớp bị ảnh hưởng
   (`bicycle`/`motorcycle`, `person`, `skis`, `truck`), rồi so với số đã báo.
2. **Train lại** trên v2 (sau khi các ảnh trong `rework_queue.csv` được gán lại) nếu kết quả giảm hoặc không còn tin
   được, và ghi run mới vào lineage gắn với release v2.

Nhờ lineage, nhóm biết chính xác run nào bị ảnh hưởng (`impact`) thay vì phải đoán hay kiểm mọi model.

## 4. Hash chứng minh gì, không chứng minh gì?

### Hash chứng minh điều gì?
1. **Tính toàn vẹn (Data Integrity):** File dữ liệu (ảnh, nhãn) không bị biến đổi, hỏng hóc hoặc bị can thiệp dù chỉ 1 bit trong quá trình truyền tải và lưu trữ. Thuật toán SHA-256 bảo đảm hiệu ứng tuyết lở (avalanche effect).
2. **Tính tái lập và kiểm toán (Reproducibility & Auditability):** Khi đóng gói `pack_release.py`, gói bàn giao zip và mã `.sha256` được tạo ra có tính tất định (thứ tự file, mốc thời gian và quyền cố định), giúp bất kỳ ai tải về ở máy khác cũng kiểm tra được đúng mã băm.
3. **Bảo toàn nguyên tắc bất biến (Immutability):** v1 (`lab250_20c5f74a77e2`) được giữ nguyên mã hash ban đầu, chứng minh nhóm không sửa đè vào lịch sử. Bản v2 là một bản phát hành mới có hash độc lập và liên kết cha-con (`Parent: v1`).

### Hash KHÔNG chứng minh điều gì?
1. **Không chứng minh chất lượng ngữ nghĩa (Semantic Correctness):** Một file nhãn gán sai hoàn toàn (nhầm xe đạp thành xe máy, box trôi khỏi người) hoặc một file ảnh bị lỗi vẫn có mã hash sha256 hợp lệ 64 ký tự. Hash chỉ đo byte của file chứ không hiểu nội dung bức ảnh.
2. **Không chứng minh file còn tốt nếu manifest sai:** Điển hình như ca ảnh `000000016010` (`wrong_hash`), bản thân file ảnh mở lên hiển thị hoàn toàn bình thường, nguyên vẹn nhưng mã hash trong manifest lại là mã của ảnh khác. Ngược lại, một file bị hỏng byte vẫn có thể tự sinh ra một hash khớp với chính nó.
3. **Không chứng minh thẩm quyền:** Bất kỳ ai sửa file cũng có thể tính lại mã hash mới. Hash phải đi kèm quy trình ký nhận, lineage và phân quyền mới có giá trị xác thực.

### Xử lý trong v2: Sửa trực tiếp vs Gán lại
- **Sửa ngay trong v2 (không cần gán lại):**
  - `wrong_hash` (`000000016010`): Đã mở ảnh kiểm tra nguyên vẹn, chỉ cần cập nhật mã sha256 thật vào `manifest.csv`.
  - `scene_leak` (`scene_593`): Đưa cả 5 ảnh về split đa số (`train`) trong `truyvet.csv`.
  - `guideline_mismatch` (`000000011615`, `000000024567`): Chuẩn hóa guideline trong `truyvet.csv` theo `jobs.csv`.
- **Chuyển sang rework_queue (loại khỏi v2, 8 ảnh):**
  - Thiếu file hoặc lỗi nhãn detection (`missing_image`, `invalid_class`, `bbox_out_of_bounds`, `duplicate_box`, `class_swap`, `bbox_drift`, `missing_box`). Bỏ khỏi v2 và phân về đúng annotator/reviewer theo `jobs.csv` để gán lại.
- **Giữ lại trong v2 (6 ảnh):**
  - Các ảnh chỉ bị lỗi ở phần panoptic (`invalid_category_id`, `thing_overlap`, `category_swap`, `instance_merge`). Nhãn detection của chúng vẫn hoàn toàn chính xác nên được giữ lại trong v2 phục vụ train model detection, kèm ghi chú trong `README.txt` để báo team panoptic.

## 5. Truy vết

### Tiêu chí xác định tầng A và tầng B

Changelog cho biết quy tắc lớp `truck` thay đổi từ v1.2 sang v1.3: v1.2 cho phép bỏ qua vật bị che trên 50% hoặc bị cắt ở mép ảnh, còn v1.3 yêu cầu vẫn phải gán box.

- **Tier A:** ảnh thuộc các cảnh team AI báo (`scene_370`, `scene_532`), thuộc job dùng guideline cũ theo `jobs.csv`, và có box detection lớp `truck`: `000000001532`, `000000007088`.
- **Tier B:** ảnh khác thỏa điều kiện guideline cũ và có box `truck`, nhưng không thuộc cảnh đã báo: `000000000724`, `000000006040`, `000000006723`, `000000007386`, `000000009769`.
- **Notify:** annotator và reviewer của các job có ảnh thuộc Tier A/B (`J01`, `J03`, `J04`): `A03`, `A04`, `Q01`, `Q02`, `Q03`.

### Vì sao lấy guideline theo job

Phiên bản guideline để truy vết được lấy từ `jobs.csv`, không lấy từ `metadata.json` của từng ảnh. Metadata ảnh có thể sai do lỗi `guideline_mismatch`; ví dụ `000000011615` và `000000024567` có metadata ghi v1.2 nhưng job của chúng dùng v1.3. Dùng guideline theo job giúp xác định đúng những ảnh và người làm việc theo quy tắc cũ.

Đã kiểm tra bằng `score_findings.py`: F1 truy vết của `tier_a`, `tier_b` và `notify` đều ≈ 1.0.

## 6. Bug hoặc điểm chưa rõ trong lab (nếu có)
- Không phát hiện bug trong bộ scripts của lab. Bộ kiểm tra `check_handover.py` và công thức F1 của `score_findings.py` hoạt động nhất quán, chính xác theo đúng rubric.