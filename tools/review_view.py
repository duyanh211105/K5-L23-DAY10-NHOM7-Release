#!/usr/bin/env python3
"""Công cụ xem ảnh để review ứng viên (Pha 2) — nhóm 07.

Vẽ box detection và viền segment panoptic lên ảnh, tô đậm box/segment mà validator nghi lỗi,
kèm khung phóng to vùng nghi lỗi (ảnh nhỏ ~240x320 vẫn nhìn rõ).

    python tools/review_view.py runs/r7007/delivery --candidates runs/r7007/candidates.json --out runs/r7007/review_view
    python tools/review_view.py runs/r7007/delivery --images 000000000785 000000006471 --out runs/r7007/review_view

Mở <out>/index.html để xem lần lượt. Công cụ cũng ghi <out>/review_log_template.csv
(image,type đã điền sẵn; verdict và note để trống) — người xem ảnh tự điền rồi chép sang review_log.csv.

Dùng Pillow (được phép cho công cụ xem ảnh; validator thì không). Chỉ đọc delivery, không sửa gì.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import pngutil  # noqa: E402

PANEL_H = 420          # chiều cao mỗi panel sau khi co giãn
ZOOM_MIN = 360         # vùng phóng to tối thiểu 360 px cạnh dài
FOCUS = (255, 40, 40)  # màu tô đậm box/segment nghi lỗi
OTHER_BOX = (0, 200, 255)
PALETTE = [(230, 25, 75), (60, 180, 75), (255, 225, 25), (0, 130, 200), (245, 130, 48), (145, 30, 180),
           (70, 240, 240), (240, 50, 230), (210, 245, 60), (250, 190, 212), (0, 128, 128), (170, 110, 40)]


def load_font(size: int):
    for name in ("arial.ttf", "C:/Windows/Fonts/arial.ttf", "/Library/Fonts/Arial.ttf",
                 "/System/Library/Fonts/Supplemental/Arial.ttf", "DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT = load_font(14)
FONT_B = load_font(17)


def read_delivery(d: Path):
    manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["items"]
    classes = {}
    for line in (d / "classes.txt").read_text(encoding="utf-8").splitlines():
        if line.strip():
            i, _, n = line.strip().partition(" ")
            classes[int(i)] = n.strip()
    pan = json.loads((d / "panoptic.json").read_text(encoding="utf-8"))
    cats = {c["id"]: c for c in pan["categories"]}
    id2stem = {im["id"]: Path(im["file_name"]).stem for im in pan["images"]}
    anns = {}
    for a in pan["annotations"]:
        anns[Path(a.get("file_name", "")).stem or id2stem.get(a["image_id"])] = a
    return manifest, classes, cats, anns


def read_boxes(path: Path, classes: dict, W: int, H: int):
    out = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        p = line.split()
        if len(p) != 5:
            continue
        try:
            c = int(float(p[0])); x, y, w, h = map(float, p[1:])
        except ValueError:
            continue
        out.append((classes.get(c, f"?{c}"), ((x - w / 2) * W, (y - h / 2) * H, (x + w / 2) * W, (y + h / 2) * H)))
    return out


def seg_masks(mask_path: Path, wanted: set[int]) -> tuple[int, int, dict[int, Image.Image]]:
    """Trả về mask nhị phân (ảnh L) cho từng segment id cần vẽ."""
    W, H, pix = pngutil.read_rgb(mask_path)
    buf = {sid: bytearray(W * H) for sid in wanted}
    for i in range(W * H):
        sid = pix[3 * i] | (pix[3 * i + 1] << 8) | (pix[3 * i + 2] << 16)
        b = buf.get(sid)
        if b is not None:
            b[i] = 255
    return W, H, {sid: Image.frombytes("L", (W, H), bytes(b)) for sid, b in buf.items()}


def outline(m: Image.Image, width: int = 2) -> Image.Image:
    eroded = m
    for _ in range(width):
        eroded = eroded.filter(ImageFilter.MinFilter(3))
    from PIL import ImageChops
    return ImageChops.subtract(m, eroded)


def label(draw: ImageDraw.ImageDraw, xy, text: str, color, font=FONT):
    x, y = xy
    l, t, r, b = draw.textbbox((x, y), text, font=font)
    y = max(0, y - (b - t) - 4)
    draw.rectangle((x, y, x + (r - l) + 4, y + (b - t) + 4), fill=color)
    draw.text((x + 2, y + 1), text, fill=(0, 0, 0) if sum(color) > 380 else (255, 255, 255), font=font)


def render(d: Path, img: str, cand: dict | None, ctx) -> Image.Image:
    manifest, classes, cats, anns = ctx
    it = manifest.get(img, {})
    ip = d / it.get("image", f"images/{img}.jpg")
    mp = d / it.get("mask", f"masks/{img}.png")
    base = Image.open(ip).convert("RGB") if ip.exists() else None
    ann = anns.get(img, {"segments_info": []})
    segs = [s for s in ann["segments_info"] if cats.get(s["category_id"], {}).get("isthing")]
    W, H, masks = seg_masks(mp, {s["id"] for s in segs}) if mp.exists() else (0, 0, {})
    if base is None:
        base = Image.new("RGB", (W or 640, H or 480), (60, 60, 60))
        ImageDraw.Draw(base).text((10, 10), "THIẾU FILE ẢNH", fill=(255, 80, 80), font=FONT_B)
    if (W, H) != base.size and W:
        base = base.resize((W, H))
    W, H = base.size
    foc = (cand or {}).get("focus") or {}
    foc_boxes = [tuple(b["xyxy"]) for b in foc.get("boxes", [])]
    foc_sid = foc.get("seg_id")

    # Panel 2: detection
    det = base.copy()
    dd = ImageDraw.Draw(det)
    for cls, b in read_boxes(d / it.get("label", f"labels/{img}.txt"), classes, W, H):
        is_f = any(max(abs(b[k] - fb[k]) for k in range(4)) < 1.0 for fb in foc_boxes)
        col = FOCUS if is_f else OTHER_BOX
        dd.rectangle(b, outline=col, width=4 if is_f else 2)
        label(dd, (b[0], b[1]), cls, col)

    # Panel 3: panoptic (viền mọi segment thing, segment nghi lỗi tô đỏ mờ)
    pan = base.copy()
    for k, s in enumerate(segs):
        m = masks.get(s["id"])
        if m is None:
            continue
        name = cats[s["category_id"]]["name"] + (" (crowd)" if s.get("iscrowd") else "")
        is_f = s["id"] == foc_sid
        col = FOCUS if is_f else PALETTE[k % len(PALETTE)]
        if is_f:
            pan = Image.composite(Image.blend(pan, Image.new("RGB", pan.size, FOCUS), 0.45), pan, m)
        pan.paste(Image.new("RGB", pan.size, col), (0, 0), outline(m, 3 if is_f else 2))
        bb = m.getbbox()
        if bb:
            label(ImageDraw.Draw(pan), (bb[0], bb[1]), name, col)

    panels = [base, det, pan]
    titles = ["Ảnh gốc", "Detection (box)", "Panoptic (segment)"]

    # Panel 4: phóng to vùng nghi lỗi (trên ảnh detection + viền segment)
    region = [tuple(foc["seg_xyxy"])] if foc.get("seg_xyxy") else []
    region += foc_boxes
    if region:
        x0 = min(r[0] for r in region); y0 = min(r[1] for r in region)
        x1 = max(r[2] for r in region); y1 = max(r[3] for r in region)
        pad = 0.25 * max(x1 - x0, y1 - y0) + 10
        box = (max(0, int(x0 - pad)), max(0, int(y0 - pad)), min(W, int(x1 + pad)), min(H, int(y1 + pad)))
        z = det.copy()
        if foc_sid in masks:
            z.paste(Image.new("RGB", z.size, FOCUS), (0, 0), outline(masks[foc_sid], 2))
        z = z.crop(box)
        scale = max(1.0, ZOOM_MIN / max(z.size))
        panels.append(z.resize((int(z.width * scale), int(z.height * scale)), Image.LANCZOS))
        titles.append(f"Phóng to x{scale:.1f} (đỏ = box + viền segment nghi lỗi)")

    # Ghép ngang, co về cùng chiều cao
    scaled = []
    for p in panels:
        s = PANEL_H / p.height
        scaled.append(p.resize((max(1, int(p.width * s)), PANEL_H), Image.LANCZOS))
    head_h = 70
    total_w = sum(p.width for p in scaled) + 10 * (len(scaled) + 1)
    sheet = Image.new("RGB", (total_w, PANEL_H + head_h + 30), (25, 25, 30))
    dr = ImageDraw.Draw(sheet)
    kind = (cand or {}).get("type", "")
    alt = (cand or {}).get("alt_types") or []
    dr.text((10, 8), f"{img}   [{kind}]  {'hoặc ' + ', '.join(alt) if alt else ''}   {W}x{H}",
            fill=(255, 220, 120), font=FONT_B)
    dr.text((10, 34), (cand or {}).get("detail", "")[:230], fill=(230, 230, 230), font=FONT)
    x = 10
    for p, t in zip(scaled, titles):
        dr.text((x, head_h + 4), t, fill=(180, 200, 255), font=FONT)
        sheet.paste(p, (x, head_h + 26))
        x += p.width + 10
    return sheet


def main() -> int:
    ap = argparse.ArgumentParser(description="Vẽ box + segment để review ứng viên")
    ap.add_argument("delivery")
    ap.add_argument("--candidates", help="candidates.json của validator")
    ap.add_argument("--images", nargs="*", default=[], help="xem thêm các ảnh này (tên ảnh không đuôi)")
    ap.add_argument("--out", required=True, help="thư mục ghi ảnh PNG + index.html")
    args = ap.parse_args()

    d, out = Path(args.delivery), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    ctx = read_delivery(d)
    cands = json.loads(Path(args.candidates).read_text(encoding="utf-8"))["candidates"] if args.candidates else []
    todo = [(c["image"], c) for c in cands] + [(i, None) for i in args.images if i not in {c["image"] for c in cands}]

    rows = []
    for n, (img, cand) in enumerate(todo, 1):
        sheet = render(d, img, cand, ctx)
        fn = f"{n:03d}_{img}.png"
        sheet.save(out / fn)
        rows.append((fn, img, cand))
        print(f"[{n}/{len(todo)}] {fn}  {cand['type'] if cand else ''}")

    with open(out / "index.html", "w", encoding="utf-8") as f:
        f.write("<!doctype html><meta charset='utf-8'><title>Review ứng viên</title>"
                "<style>body{background:#111;color:#eee;font-family:sans-serif;margin:16px}"
                "img{max-width:100%;border:1px solid #444}h3{color:#ffd27a;margin:28px 0 4px}"
                "p{margin:2px 0 8px;color:#ccc}</style>"
                f"<h1>Review ứng viên — {html.escape(str(d))} ({len(rows)} ảnh)</h1>"
                "<p>Đỏ = box/segment validator nghi lỗi. Ghi review_log.csv: image,type,verdict,note — note nói <b>thấy gì</b> trong ảnh.</p>")
        for fn, img, cand in rows:
            t = cand["type"] if cand else "(xem thêm)"
            alt = " hoặc " + ", ".join(cand["alt_types"]) if cand and cand.get("alt_types") else ""
            f.write(f"<h3>{html.escape(img)} — {html.escape(t)}{html.escape(alt)}</h3>"
                    f"<p>{html.escape(cand['detail']) if cand else ''}</p><a href='{fn}'><img src='{fn}'></a>")

    tpl = out / "review_log_template.csv"
    with open(tpl, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["image", "type", "verdict", "note"])
        for _, img, cand in rows:
            w.writerow([img, cand["type"] if cand else "", "", ""])
    print(f"-> {out / 'index.html'}\n-> {tpl} (điền verdict + note rồi chép sang review_log.csv)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
