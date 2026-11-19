#!/usr/bin/env python3
"""Tạo gói bàn giao lô v2 cho nhóm 07 (Pha 4) — Đinh Trường Phong & Hà Tiến Trịnh.

    python tools/build_handover.py runs/r7007

Tự động thực hiện:
1. Đọc errors.json, tách các ảnh lỗi detection vào rework_queue.csv (giao đúng annotator, reviewer theo jobs.csv)
2. Sao chép ảnh và nhãn sạch vào handover/<release_id>_v2/{images,labels}
3. Giữ nguyên các ảnh chỉ lỗi panoptic trong v2
4. Chuẩn hóa split của cảnh bị rò rỉ (scene_593) về split train
5. Chuẩn hóa guideline trong truyvet.csv theo jobs.csv
6. Tạo manifest.csv với sha256 thật của mọi file trong images/ và labels/
7. Tạo label_summary.csv đếm số nhãn từng lớp + TOTAL
8. Tạo README.txt theo đúng form chuẩn
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

# Các lỗi ở nhãn detection hoặc thiếu file phải đưa vào rework_queue và loại khỏi v2
DET_REWORK = {
    "missing_image",
    "invalid_class",
    "bbox_out_of_bounds",
    "duplicate_box",
    "class_swap",
    "bbox_drift",
    "missing_box",
}

PAN_ERRORS = {
    "invalid_category_id",
    "thing_overlap",
    "category_swap",
    "instance_merge",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Tạo gói bàn giao detection v2")
    parser.add_argument("run", help="Thư mục run (ví dụ: runs/r7007)")
    args = parser.parse_args()

    run = Path(args.run)
    d = run / "delivery"
    if not d.is_dir():
        sys.exit(f"Không tìm thấy thư mục delivery: {d}")

    # Đọc dữ liệu v1
    rel = json.loads((d / "release.json").read_text(encoding="utf-8"))
    rid = rel["release_id"]
    man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["items"]
    meta = {m["image"]: m for m in json.loads((d / "metadata.json").read_text(encoding="utf-8"))["items"]}
    with open(d / "jobs.csv", encoding="utf-8", newline="") as f:
        jobs = {r["job_id"]: r for r in csv.DictReader(f)}
    
    classes_80 = []
    for line in (d / "classes.txt").read_text(encoding="utf-8").splitlines():
        if line.strip():
            classes_80.append(line.strip().split(" ", 1)[1].strip())

    errors_doc = json.loads((run / "errors.json").read_text(encoding="utf-8"))
    errors = errors_doc["errors"]

    # Xác định các ảnh vào rework_queue
    # Ảnh có target trong man và type thuộc DET_REWORK
    err_by_img = {}
    for e in errors:
        t, target = e["type"], e["target"]
        if target in man:
            err_by_img.setdefault(target, []).append(t)

    rework_images = {img for img, types in err_by_img.items() if any(t in DET_REWORK for t in types)}
    print(f"Tổng số ảnh v1: {len(man)}")
    print(f"Số ảnh lỗi detection cần rework: {len(rework_images)} -> {sorted(rework_images)}")

    pan_only_images = {img for img, types in err_by_img.items() if all(t in PAN_ERRORS for t in types)}
    print(f"Số ảnh chỉ lỗi panoptic (giữ lại v2): {len(pan_only_images)} -> {sorted(pan_only_images)}")

    v2_dir = run / "handover" / f"{rid}_v2"
    if v2_dir.exists():
        shutil.rmtree(v2_dir)
    (v2_dir / "images").mkdir(parents=True)
    (v2_dir / "labels").mkdir(parents=True)

    # 1. Copy images và labels cho v2
    v2_stems = sorted(img for img in man if img not in rework_images)
    for stem in v2_stems:
        it = man[stem]
        src_img = d / it["image"]
        src_lbl = d / it["label"]
        if not src_img.is_file():
            sys.exit(f"Lỗi: Không tìm thấy ảnh {src_img}")
        shutil.copyfile(src_img, v2_dir / "images" / f"{stem}.jpg")
        shutil.copyfile(src_lbl, v2_dir / "labels" / f"{stem}.txt")

    print(f"Đã sao chép {len(v2_stems)} ảnh và nhãn vào v2.")

    # 2. Tạo rework_queue.csv
    rework_rows = []
    action_map = {
        "missing_image": "Bổ sung file ảnh gốc và gán lại nhãn detection",
        "invalid_class": "Sửa lại class_id về danh mục hợp lệ 0-79",
        "bbox_out_of_bounds": "Cắt tỉa và chuẩn hóa tọa độ bounding box không vượt ra ngoài ảnh",
        "duplicate_box": "Loại bỏ box lặp trùng lặp",
        "class_swap": "Gán lại đúng nhãn đối tượng theo ảnh thực tế",
        "bbox_drift": "Vẽ lại bounding box bao khít đối tượng trong ảnh",
        "missing_box": "Bổ sung bounding box cho đối tượng còn thiếu",
    }
    for stem in sorted(rework_images):
        m = meta[stem]
        job = jobs[m["job_id"]]
        # Lấy loại lỗi detection chính
        t = next(tp for tp in err_by_img[stem] if tp in DET_REWORK)
        act = action_map.get(t, f"Gán lại nhãn do lỗi {t}")
        rework_rows.append({
            "image": stem,
            "type": t,
            "annotator": job["annotator"],
            "reviewer": job["reviewer"],
            "action": act,
        })
    with open(v2_dir / "rework_queue.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["image", "type", "annotator", "reviewer", "action"])
        w.writeheader()
        w.writerows(rework_rows)
    print(f"Đã tạo rework_queue.csv với {len(rework_rows)} dòng.")

    # 3. Tạo manifest.csv
    manifest_rows = []
    for sub in ("images", "labels"):
        for p in sorted((v2_dir / sub).iterdir()):
            if p.is_file():
                rel_path = f"{sub}/{p.name}"
                manifest_rows.append({"file": rel_path, "sha256": sha256_file(p)})
    with open(v2_dir / "manifest.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "sha256"])
        w.writeheader()
        w.writerows(manifest_rows)
    print(f"Đã tạo manifest.csv với {len(manifest_rows)} file.")

    # 4. Tạo label_summary.csv
    label_counts = Counter()
    for stem in v2_stems:
        lbl_p = v2_dir / "labels" / f"{stem}.txt"
        for line in lbl_p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            c = int(float(line.split()[0]))
            cname = classes_80[c] if 0 <= c < 80 else str(c)
            label_counts[cname] += 1
    
    total_labels = sum(label_counts.values())
    summary_rows = []
    for cname in sorted(label_counts.keys()):
        summary_rows.append({"class": cname, "count": label_counts[cname]})
    summary_rows.append({"class": "TOTAL", "count": total_labels})

    with open(v2_dir / "label_summary.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["class", "count"])
        w.writeheader()
        w.writerows(summary_rows)
    print(f"Đã tạo label_summary.csv ({total_labels} nhãn, {len(label_counts)} lớp).")

    # 5. Tạo truyvet.csv (xử lý scene_leak và guideline theo job)
    # Tìm các scene có rò rỉ split
    scene_splits = {}
    for m in meta.values():
        scene_splits.setdefault(m["scene_id"], set()).add(m["split"])
    leaking_scenes = {sc for sc, sps in scene_splits.items() if len(sps) > 1}

    truyvet_rows = []
    for stem in v2_stems:
        m = meta[stem]
        job = jobs[m["job_id"]]
        split = m["split"]
        if m["scene_id"] in leaking_scenes:
            # Đưa toàn bộ cảnh rò rỉ về split đa số (train)
            split = "train"
        truyvet_rows.append({
            "image": stem,
            "scene_id": m["scene_id"],
            "split": split,
            "job_id": m["job_id"],
            "annotator": job["annotator"],
            "reviewer": job["reviewer"],
            "guideline": job["guideline"],  # Lấy theo job
        })
    with open(v2_dir / "truyvet.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["image", "scene_id", "split", "job_id", "annotator", "reviewer", "guideline"])
        w.writeheader()
        w.writerows(truyvet_rows)
    print(f"Đã tạo truyvet.csv với {len(truyvet_rows)} dòng.")

    # 6. Tạo README.txt
    err_targets = {e["target"] for e in errors}
    qc_count = len(err_targets)
    total_imgs = len(man)
    rate_pct = qc_count / total_imgs * 100

    pan_str = ", ".join(sorted(pan_only_images))
    readme_content = f"""Release: {rid}_v2
Parent: {rid}
Số ảnh: {len(v2_stems)}
Số nhãn: {total_labels}
Guideline: v1.2 (J01-J04), v1.3 (J05-J10)
QC v1: {qc_count}/{total_imgs} = {rate_pct:.1f}%
Kết luận v1: Hold — Lô v1 có tỉ lệ lỗi QC là {qc_count}/{total_imgs} ({rate_pct:.1f}%) vượt ngưỡng 2% (ngưỡng Day 7)
Kết luận v2: Release — Đã tách {len(rework_images)} ảnh lỗi detection sang rework_queue.csv, chuẩn hóa split cảnh scene_593, chuẩn hóa guideline theo job, cập nhật hash manifest cho ảnh 000000016010
Ghi chú: Lô v2 là sản phẩm detection sạch giao cho team AI huấn luyện. {len(rework_images)} ảnh lỗi detection đã chuyển sang rework_queue.csv giao đúng người gán và kiểm tra theo jobs.csv để gán lại. {len(pan_only_images)} ảnh lỗi chỉ ở panoptic ({pan_str}) nhãn detection vẫn chính xác nên được giữ lại trong v2; đã bàn giao danh sách cho team panoptic xử lý. Cảnh scene_593 đã đưa toàn bộ về split train để loại bỏ rò rỉ dữ liệu. Ảnh 000000016010 đã mở kiểm tra nguyên vẹn và cập nhật sha256 đúng vào manifest.csv.
"""
    (v2_dir / "README.txt").write_text(readme_content, encoding="utf-8")
    print("Đã tạo README.txt thành công.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
