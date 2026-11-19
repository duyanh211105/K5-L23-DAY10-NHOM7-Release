#!/usr/bin/env python3
"""Kiểm review_log.csv trước khi gộp (nhóm 07). Chỉ kiểm cách ghi, không kết luận thay người xem.

    python tools/check_review.py runs/r7007/review_log.csv [--candidates runs/r7007/candidates.json]

Kiểm: header đúng; verdict là confirmed/rejected; type là lỗi gán nhãn; note >= 20 ký tự,
không trùng nhau, không phải câu chung chung; mỗi ứng viên đã có một dòng; không có ảnh trùng.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

SEMANTIC = {"class_swap", "bbox_drift", "missing_box", "category_swap", "instance_merge"}
VAGUE = {"ok", "có lỗi", "co loi", "lỗi", "loi", "đúng", "sai", "khong loi", "không lỗi", "tu nhien", "tự nhiên"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("review_log")
    ap.add_argument("--candidates")
    a = ap.parse_args()
    with open(a.review_log, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        rows = list(reader)
    problems = []
    if header != ["image", "type", "verdict", "note"]:
        problems.append(f"header phải là image,type,verdict,note (đang là {header})")
    notes = Counter(r.get("note", "").strip() for r in rows)
    images = Counter(r.get("image", "").strip() for r in rows)
    for i, r in enumerate(rows, 2):
        img, t, v, n = (r.get(k, "").strip() for k in ("image", "type", "verdict", "note"))
        tag = f"dòng {i} ({img})"
        if v not in ("confirmed", "rejected"):
            problems.append(f"{tag}: verdict '{v}' phải là confirmed hoặc rejected")
        if t not in SEMANTIC:
            problems.append(f"{tag}: type '{t}' không phải lỗi gán nhãn {sorted(SEMANTIC)}")
        if len(n) < 20:
            problems.append(f"{tag}: note quá ngắn ({len(n)} ký tự, cần >= 20) — ghi THẤY GÌ trong ảnh")
        elif n.lower().strip(" .") in VAGUE:
            problems.append(f"{tag}: note chung chung, phải nói thấy gì")
        if "<tên>" in n or "<ten>" in n:
            problems.append(f"{tag}: chưa ký tên — người xem ảnh tự mở ảnh, kiểm lại rồi thay <tên> bằng tên mình")
        if n and notes[n] > 1:
            problems.append(f"{tag}: note bị trùng với dòng khác")
        if images[img] > 1:
            problems.append(f"{tag}: ảnh xuất hiện {images[img]} lần — mỗi ảnh một kết luận")
    if a.candidates:
        cands = json.loads(Path(a.candidates).read_text(encoding="utf-8"))["candidates"]
        missing = [c["image"] for c in cands if c["image"] not in images]
        if missing:
            problems.append(f"chưa review {len(missing)} ứng viên: {', '.join(missing)}")
    conf = Counter(r["type"].strip() for r in rows if r.get("verdict", "").strip() == "confirmed")
    rej = sum(1 for r in rows if r.get("verdict", "").strip() == "rejected")
    print(f"{len(rows)} dòng: confirmed {sum(conf.values())} {dict(conf)}, rejected {rej}")
    if problems:
        print("CẦN SỬA:")
        for p in problems:
            print("  -", p)
        return 1
    print("OK — có thể chạy scripts/merge_review.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
