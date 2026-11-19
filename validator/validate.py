#!/usr/bin/env python3
"""Validator của nhóm 07 — Day 10 Lab.

    python validator/validate.py <delivery> --out <errors.json> [--candidates <candidates.json>]

- Chỉ đọc thư mục delivery được truyền vào. Chỉ thư viện chuẩn + scripts/pngutil.py. Không mạng.
- `--out` chỉ chứa lỗi LUẬT (máy tự chứng minh được từ file).
- `--candidates` chứa ứng viên lỗi GÁN NHÃN (đối chiếu detection <-> panoptic), phải mở ảnh xem
  rồi ghi review_log.csv trước khi đưa vào errors.json (scripts/merge_review.py).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import pngutil  # noqa: E402

# ---------------------------------------------------------------------------
# Ngưỡng (chọn bằng cách đo trên lô sạch runs/clean, xem REPORT.md)
# ---------------------------------------------------------------------------
OOB_TOL_PX = 0.5          # box tràn mép quá 0.5 px mới tính là out-of-bounds (tránh sai số làm tròn 6 chữ số)
DUP_SIZE_TOL_PX = 1.0     # duplicate: chênh w/h <= 1 px (cùng kích thước)
DUP_SHIFT_MAX_PX = 3.0    # duplicate: tâm lệch <= 3 px
AREA_TOL_PX = 0           # thing_overlap: area khai > số pixel thật + tol

# Đối chiếu dựa trên "cov" = tỉ lệ pixel của segment nằm trong box. Ở COCO sạch, box của một vật
# chứa ~100% pixel segment (vật bị che thì segment nhỏ lại nhưng VẪN nằm trong box), nên IoU bbox
# thấp không phải là lỗi; pixel rơi ra ngoài box mới là dấu hiệu.
MIN_SEG_PX = 0.001        # bỏ segment < 0.1% diện tích ảnh (lệch 1 px đã làm cov tụt)
OK_COV = 0.97             # box cùng lớp chứa >= 97% pixel segment => khớp, không báo
DRIFT_COV_MIN = 0.20      # box cùng lớp chứa 20%..97% => bbox_drift (đúng vật nhưng lệch)
SWAP_IOU = 0.75           # box khác lớp trùng vị trí segment (IoU bbox) ...
SWAP_COV = 0.90           # ... và chứa >= 90% pixel segment
MISSING_MIN_PX = 0.003    # missing_box: segment >= 0.3% ảnh mà không có box cùng lớp nào gần
MERGE_COV_EACH = 0.15     # instance_merge: >= 2 box cùng lớp, mỗi box chứa >= 15% pixel segment
MERGE_COV_SUM = 0.80      # ... và cộng lại >= 80%, không box nào chứa >= MERGE_MAX_PART
MERGE_MAX_PART = 0.90
MERGE_FILL = 0.40         # box "mồ côi" mà >= 40% diện tích là pixel của MỘT segment cùng lớp đã có box khác => gộp
DRIFT_SIZE_TOL = 0.06     # drift thật: box giữ kích thước của vật (lệch <= 6%), chỉ dịch tâm.
                          # Box khác kích thước nhiều thường là lệch tự nhiên (che khuất, cách vẽ) -> vẫn đưa ra, ưu tiên thấp


# ---------------------------------------------------------------------------
# Đọc file
# ---------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_classes(path: Path) -> dict[int, str]:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        idx, _, name = line.partition(" ")
        out[int(idx)] = name.strip()
    return out


def read_labels(path: Path) -> list[tuple[int, float, float, float, float]]:
    boxes = []
    if not path.exists():
        return boxes
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) != 5:
            continue
        try:
            cls = int(float(parts[0]))
            x, y, w, h = (float(p) for p in parts[1:])
        except ValueError:
            continue
        boxes.append((cls, x, y, w, h))
    return boxes


def png_size(path: Path) -> tuple[int, int] | None:
    try:
        with open(path, "rb") as f:
            head = f.read(24)
        if head[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")
    except OSError:
        return None


def jpeg_size(path: Path) -> tuple[int, int] | None:
    """Đọc (width, height) từ marker SOF của JPEG, chỉ thư viện chuẩn."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if data[:2] != b"\xff\xd8":
        return None
    pos = 2
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        seglen = int.from_bytes(data[pos + 2 : pos + 4], "big")
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            h = int.from_bytes(data[pos + 5 : pos + 7], "big")
            w = int.from_bytes(data[pos + 7 : pos + 9], "big")
            return w, h
        pos += 2 + seglen
    return None


# ---------------------------------------------------------------------------
# Lỗi luật
# ---------------------------------------------------------------------------
def check_rules(d: Path, ctx: dict) -> list[dict]:
    errors: dict[str, str] = {}   # image -> type (mỗi ảnh nhiều nhất một lỗi; giữ lỗi đầu tiên theo thứ tự ưu tiên)
    scene_errors: list[dict] = []

    def add(img: str, kind: str):
        errors.setdefault(img, kind)

    items = ctx["manifest"]
    classes = ctx["classes"]

    # 1. File: missing_image, wrong_hash
    for img, it in items.items():
        ip = d / it.get("image", f"images/{img}.jpg")
        if not ip.exists():
            add(img, "missing_image")
            continue
        for key in ("image", "label", "mask"):
            rel, want = it.get(key), it.get(f"{key}_sha256")
            if not rel or not want:
                continue
            p = d / rel
            if p.exists() and sha256_file(p) != want.lower():
                add(img, "wrong_hash")
                break

    # 2. Detection: invalid_class, bbox_out_of_bounds, duplicate_box
    for img, it in items.items():
        if img in errors:
            continue
        size = ctx["sizes"].get(img)
        boxes = read_labels(d / it.get("label", f"labels/{img}.txt"))
        if any(b[0] not in classes for b in boxes):
            add(img, "invalid_class")
            continue
        if size:
            W, H = size
            tx, ty = OOB_TOL_PX / W, OOB_TOL_PX / H
            for _, x, y, w, h in boxes:
                if x - w / 2 < -tx or x + w / 2 > 1 + tx or y - h / 2 < -ty or y + h / 2 > 1 + ty:
                    add(img, "bbox_out_of_bounds")
                    break
            if img in errors:
                continue
            px = [(c, x * W, y * H, w * W, h * H) for c, x, y, w, h in boxes]
            found = False
            for i in range(len(px)):
                for j in range(i + 1, len(px)):
                    a, b = px[i], px[j]
                    if a[0] != b[0]:
                        continue
                    if abs(a[3] - b[3]) > DUP_SIZE_TOL_PX or abs(a[4] - b[4]) > DUP_SIZE_TOL_PX:
                        continue
                    shift = max(abs(a[1] - b[1]), abs(a[2] - b[2]))
                    if shift <= DUP_SHIFT_MAX_PX:
                        found = True
                        break
                if found:
                    break
            if found:
                add(img, "duplicate_box")

    # 3. Metadata: guideline_mismatch (so với job), scene_leak
    jobs = ctx["jobs"]
    for m in ctx["meta"]:
        img = m["image"]
        job = jobs.get(m.get("job_id"))
        if job and m.get("guideline_version") != job["guideline"]:
            add(img, "guideline_mismatch")
    by_scene = defaultdict(set)
    for m in ctx["meta"]:
        by_scene[m["scene_id"]].add(m["split"])
    for scene, splits in sorted(by_scene.items()):
        if len(splits) > 1:
            scene_errors.append({"type": "scene_leak", "target": scene})

    # 4. Panoptic: invalid_category_id, thing_overlap
    cat_ids = set(ctx["cats"])
    for img, ann in ctx["pan_ann"].items():
        if img in errors:
            continue
        if any(s["category_id"] not in cat_ids for s in ann["segments_info"]):
            add(img, "invalid_category_id")
            continue
        seg = ctx["mask_stats"](img)
        if seg is None:
            continue
        for s in ann["segments_info"]:
            real = seg["count"].get(s["id"], 0)
            if s.get("area", 0) > real + AREA_TOL_PX:
                add(img, "thing_overlap")
                break

    out = [{"type": k, "target": img} for img, k in errors.items()] + scene_errors
    return sorted(out, key=lambda e: (e["type"], e["target"]))


# ---------------------------------------------------------------------------
# Mask: đếm pixel, bbox thật, và đếm pixel segment nằm trong một box
# ---------------------------------------------------------------------------
class MaskCache:
    def __init__(self, d: Path, items: dict, pan_ann: dict):
        self.d, self.items, self.pan_ann = d, items, pan_ann
        self.cache: dict[str, dict | None] = {}

    def __call__(self, img: str) -> dict | None:
        if img in self.cache:
            return self.cache[img]
        rel = self.items.get(img, {}).get("mask") or self.pan_ann.get(img, {}).get("file_name")
        p = self.d / rel if rel and "/" in rel else self.d / "masks" / f"{img}.png"
        res = None
        if p.exists():
            try:
                W, H, pix = pngutil.read_rgb(p)
                ids = [pix[i] | (pix[i + 1] << 8) | (pix[i + 2] << 16) for i in range(0, len(pix), 3)]
                count = Counter(ids)
                bbox = {}
                for y in range(H):
                    row = ids[y * W : (y + 1) * W]
                    for sid in set(row):
                        xs0 = row.index(sid)
                        xs1 = W - 1 - row[::-1].index(sid)
                        b = bbox.get(sid)
                        if b is None:
                            bbox[sid] = [xs0, y, xs1, y]
                        else:
                            b[0] = min(b[0], xs0); b[2] = max(b[2], xs1); b[3] = y
                res = {"W": W, "H": H, "ids": ids, "count": count, "bbox": bbox}
            except Exception:  # noqa: BLE001
                res = None
        self.cache[img] = res
        return res


def pixels_in_box(m: dict, box: tuple[float, float, float, float]) -> Counter:
    W, H, ids = m["W"], m["H"], m["ids"]
    x0 = max(0, int(round(box[0]))); x1 = min(W, int(round(box[2])))
    y0 = max(0, int(round(box[1]))); y1 = min(H, int(round(box[3])))
    c = Counter()
    if x1 <= x0 or y1 <= y0:
        return c
    for y in range(y0, y1):
        c.update(ids[y * W + x0 : y * W + x1])
    return c


def same_size(a, b, tol: float = DRIFT_SIZE_TOL) -> bool:
    wa, ha, wb, hb = a[2] - a[0], a[3] - a[1], b[2] - b[0], b[3] - b[1]
    return abs(wa - wb) <= tol * max(wa, wb) + 2 and abs(ha - hb) <= tol * max(ha, hb) + 2


def iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


# ---------------------------------------------------------------------------
# Đối chiếu detection <-> panoptic: sinh ứng viên
# ---------------------------------------------------------------------------
def cross_check(d: Path, ctx: dict, skip: set[str]) -> list[dict]:
    classes, cats = ctx["classes"], ctx["cats"]
    cands = []
    for img, ann in sorted(ctx["pan_ann"].items()):
        if img in skip or img not in ctx["manifest"]:
            continue
        m = ctx["mask_stats"](img)
        if m is None:
            continue
        W, H = m["W"], m["H"]
        img_px = W * H
        raw = read_labels(d / ctx["manifest"][img].get("label", f"labels/{img}.txt"))
        boxes = []
        for c, x, y, w, h in raw:
            if c not in classes:
                continue
            boxes.append({"cls": classes[c], "xyxy": ((x - w / 2) * W, (y - h / 2) * H, (x + w / 2) * W, (y + h / 2) * H)})
        segs = []
        for s in ann["segments_info"]:
            cat = cats.get(s["category_id"])
            if not cat or not cat.get("isthing") or s.get("iscrowd"):
                continue
            n = m["count"].get(s["id"], 0)
            bb = m["bbox"].get(s["id"])
            if n == 0 or bb is None:
                continue
            segs.append({"id": s["id"], "cls": cat["name"], "n": n,
                         "xyxy": (bb[0], bb[1], bb[2] + 1, bb[3] + 1)})
        crowd_cls = {cats.get(s["category_id"], {}).get("name") for s in ann["segments_info"] if s.get("iscrowd")}

        # cov[bi][sid] = tỉ lệ pixel của segment nằm trong box
        cov = []
        for b in boxes:
            inside = pixels_in_box(m, b["xyxy"])
            cov.append({s["id"]: inside.get(s["id"], 0) / s["n"] for s in segs})

        # box_ok[bi]: box đã có segment cùng lớp khớp nó (chứa >= OK_COV pixel)
        box_ok = [any(b["cls"] == s["cls"] and cov[bi][s["id"]] >= OK_COV for s in segs) for bi, b in enumerate(boxes)]

        def focus(s, bis):
            """Vị trí cần xem: segment nghi lỗi + các box liên quan (công cụ xem ảnh tô đậm)."""
            return {"seg_id": s["id"], "seg_cls": s["cls"], "seg_xyxy": [round(v) for v in s["xyxy"]],
                    "boxes": [{"cls": boxes[k]["cls"], "xyxy": [round(v, 1) for v in boxes[k]["xyxy"]]} for k in bis]}

        found = []  # (độ ưu tiên, type, alt, detail, focus)
        for s in segs:
            if s["n"] < MIN_SEG_PX * img_px:
                continue
            sid = s["id"]
            same = [bi for bi in range(len(boxes)) if boxes[bi]["cls"] == s["cls"]]
            best = max((cov[bi][sid] for bi in same), default=0.0)
            if best >= OK_COV:
                continue
            # 1. swap: box khác lớp trùng vị trí segment, box đó không khớp segment cùng lớp nào
            other = [bi for bi in range(len(boxes)) if boxes[bi]["cls"] != s["cls"] and not box_ok[bi]
                     and iou(boxes[bi]["xyxy"], s["xyxy"]) >= SWAP_IOU and cov[bi][sid] >= SWAP_COV]
            if other and best < DRIFT_COV_MIN:
                bi = max(other, key=lambda k: iou(boxes[k]["xyxy"], s["xyxy"]))
                io = iou(boxes[bi]["xyxy"], s["xyxy"])
                found.append((3 + io, "class_swap", ["category_swap"],
                              f"detection ghi {boxes[bi]['cls']}, panoptic ghi {s['cls']} cùng vị trí (IoU {io:.2f}); "
                              f"mở ảnh: nếu vật là {s['cls']} thì class_swap, nếu là {boxes[bi]['cls']} thì category_swap",
                              focus(s, [bi])))
                continue
            # 2. instance_merge: segment trải qua >= 2 box cùng lớp, không box nào chứa trọn
            parts = [bi for bi in same if cov[bi][sid] >= MERGE_COV_EACH]
            if (len(parts) >= 2 and sum(cov[bi][sid] for bi in parts) >= MERGE_COV_SUM
                    and max(cov[bi][sid] for bi in parts) < MERGE_MAX_PART):
                found.append((2 + s["n"] / img_px, "instance_merge", [],
                              f"segment {s['cls']} ({s['n']} px) trải qua {len(parts)} box {s['cls']} "
                              f"(" + ", ".join(f"{cov[bi][sid]:.0%}" for bi in parts) + ")", focus(s, parts)))
                continue
            # 3. bbox_drift: box cùng lớp chứa một phần segment, phần còn lại rơi ra ngoài.
            #    Nếu không box nào chứa >= 20% nhưng có box cùng lớp "mồ côi" cùng kích thước => box bị đẩy xa.
            far = [bi for bi in same if not box_ok[bi] and same_size(boxes[bi]["xyxy"], s["xyxy"])]
            if best >= DRIFT_COV_MIN or far:
                bi = max(same, key=lambda k: cov[k][sid]) if best >= DRIFT_COV_MIN else far[0]
                b, sx = boxes[bi]["xyxy"], s["xyxy"]
                dx = ((b[0] + b[2]) - (sx[0] + sx[2])) / 2
                dy = ((b[1] + b[3]) - (sx[1] + sx[3])) / 2
                keep_size = same_size(b, sx)
                found.append(((2 if keep_size else 0) + (1 - cov[bi][sid]), "bbox_drift",
                              [] if keep_size else ["(có thể lệch tự nhiên: box khác kích thước segment)"],
                              f"box {s['cls']} chỉ chứa {cov[bi][sid]:.0%} pixel segment; tâm box lệch ({dx:+.0f},{dy:+.0f}) px, "
                              f"box {b[2] - b[0]:.0f}x{b[3] - b[1]:.0f} vs segment {sx[2] - sx[0]:.0f}x{sx[3] - sx[1]:.0f}"
                              + ("" if keep_size else " — KHÁC kích thước, nhiều khả năng che khuất/tự nhiên"), focus(s, [bi])))
                continue
            # 4. missing_box: segment đáng kể mà không có box cùng lớp nào gần
            if s["n"] >= MISSING_MIN_PX * img_px and s["cls"] not in crowd_cls:
                found.append((1 + s["n"] / img_px, "missing_box", [],
                              f"segment {s['cls']} {s['n']} px ({s['n'] / img_px:.1%} ảnh) không có box {s['cls']} nào", focus(s, [])))

        # 5. Box mồ côi nằm trong segment cùng lớp của box khác => hai vật bị gộp trong panoptic
        seg_by_id = {s["id"]: s for s in segs}
        for bi, b in enumerate(boxes):
            if any(boxes[bi]["cls"] == s["cls"] and cov[bi][s["id"]] >= 0.5 for s in segs):
                continue
            x0, y0, x1, y1 = b["xyxy"]
            barea = max(1.0, (x1 - x0) * (y1 - y0))
            inside = pixels_in_box(m, b["xyxy"])
            for sid, cnt in inside.most_common():
                s = seg_by_id.get(sid)
                if s is None or s["cls"] != b["cls"]:
                    continue
                owner = [bj for bj in range(len(boxes)) if bj != bi and boxes[bj]["cls"] == s["cls"] and cov[bj][sid] >= 0.5]
                if cnt / barea >= MERGE_FILL and owner:
                    found.append((2 + cnt / barea, "instance_merge", [],
                                  f"box {b['cls']} [{x0:.0f},{y0:.0f},{x1:.0f},{y1:.0f}] không có segment riêng; "
                                  f"{cnt / barea:.0%} diện tích box là pixel của segment {s['cls']} thuộc box khác", focus(s, [bi] + owner)))
                break
        if found:
            found.sort(key=lambda f: -f[0])
            sc, kind, alt, detail, foc = found[0]
            cands.append({"image": img, "type": kind, "alt_types": alt, "score": round(sc, 4),
                          "detail": detail, "focus": foc, "other_signals": [f[1] for f in found[1:]]})
    return cands


# ---------------------------------------------------------------------------
def build_ctx(d: Path) -> dict:
    manifest = load_json(d / "manifest.json")["items"]
    meta = load_json(d / "metadata.json")["items"]
    classes = read_classes(d / "classes.txt")
    with open(d / "jobs.csv", encoding="utf-8", newline="") as f:
        jobs = {r["job_id"]: r for r in csv.DictReader(f)}
    pan = load_json(d / "panoptic.json")
    cats = {c["id"]: c for c in pan["categories"]}
    id2stem = {im["id"]: Path(im["file_name"]).stem for im in pan["images"]}
    pan_ann = {}
    for a in pan["annotations"]:
        stem = Path(a.get("file_name", "")).stem or id2stem.get(a["image_id"])
        pan_ann[stem] = a
    sizes = {}
    for im in pan["images"]:
        sizes[Path(im["file_name"]).stem] = (im["width"], im["height"])
    for img, it in manifest.items():   # ưu tiên kích thước thật của file ảnh
        s = jpeg_size(d / it.get("image", "")) if it.get("image") else None
        s = s or (png_size(d / it["mask"]) if it.get("mask") else None)
        if s:
            sizes[img] = s
    ctx = {"manifest": manifest, "meta": meta, "classes": classes, "jobs": jobs,
           "cats": cats, "pan_ann": pan_ann, "sizes": sizes}
    ctx["mask_stats"] = MaskCache(d, manifest, pan_ann)
    return ctx


def main() -> int:
    ap = argparse.ArgumentParser(description="Validator nhóm 07: lỗi luật + ứng viên đối chiếu")
    ap.add_argument("delivery")
    ap.add_argument("--out", required=True, help="errors.json (lỗi luật)")
    ap.add_argument("--candidates", help="candidates.json (ứng viên lỗi gán nhãn, cần xem ảnh)")
    args = ap.parse_args()
    d = Path(args.delivery)
    ctx = build_ctx(d)

    rules = check_rules(d, ctx)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"errors": rules}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(rules)} lỗi luật -> {args.out}  {dict(Counter(e['type'] for e in rules))}")

    if args.candidates:
        skip = {e["target"] for e in rules if e["type"] != "scene_leak"}
        cands = sorted(cross_check(d, ctx, skip), key=lambda c: -c["score"])  # ưu tiên cao xem trước
        Path(args.candidates).parent.mkdir(parents=True, exist_ok=True)
        Path(args.candidates).write_text(json.dumps({"candidates": cands}, indent=1, ensure_ascii=False) + "\n",
                                         encoding="utf-8")
        print(f"{len(cands)} ứng viên -> {args.candidates}  {dict(Counter(c['type'] for c in cands))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
