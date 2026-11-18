"""Pure helper logic for the Smart Waste Segregation app.

Nothing in this module imports Streamlit or Ultralytics, so it can be unit-tested
quickly (see tests/test_waste_utils.py).
"""
from __future__ import annotations

import json
from datetime import datetime

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

CATEGORIES = ["Plastic", "Metal", "Paper", "Cloth", "Glass", "Organic", "Other / Unsure"]
UNSURE = "Other / Unsure"

# Bin colours follow a common colour-coded scheme. Local rules differ, so the app
# tells the user to check their own municipality's colours.
CATEGORY_INFO = {
    "Plastic": {
        "bin": "Blue bin", "color": "#2F6FDE", "route": "Recycle",
        "tip": "Rinse, remove caps and flatten bottles. Soft films and bags often need a drop-off point.",
    },
    "Metal": {
        "bin": "Grey bin", "color": "#6B7B8C", "route": "Recycle",
        "tip": "Rinse cans and tins. Wrap sharp items (blades, scissors) before binning.",
    },
    "Paper": {
        "bin": "Yellow bin", "color": "#E0A100", "route": "Recycle",
        "tip": "Keep it dry and clean. Greasy or wet paper belongs in compost or general waste.",
    },
    "Cloth": {
        "bin": "Violet bag", "color": "#8A5CD0", "route": "Reuse",
        "tip": "Donate wearable items. Worn-out textiles can go to a textile-recycling collection.",
    },
    "Glass": {
        "bin": "Teal bin", "color": "#12A3A3", "route": "Recycle",
        "tip": "Rinse and keep glass separate. Wrap broken pieces; ceramics and mirrors are not recyclable glass.",
    },
    "Organic": {
        "bin": "Green bin", "color": "#3E9B4F", "route": "Compost",
        "tip": "Food scraps and garden waste can be composted. Keep plastic out of the compost.",
    },
    UNSURE: {
        "bin": "Charcoal bin", "color": "#4A4F55", "route": "General waste",
        "tip": "Check the item's label or your local guidelines before choosing a bin.",
    },
}

# COCO class names (the general model's labels) -> conservative waste suggestions.
SUGGESTIONS = {
    "bottle": "Plastic",
    "wine glass": "Glass",
    "book": "Paper",
    "scissors": "Metal",
    "knife": "Metal",
    "spoon": "Metal",
    "fork": "Metal",
    "banana": "Organic",
    "apple": "Organic",
    "orange": "Organic",
    "broccoli": "Organic",
    "carrot": "Organic",
    "sandwich": "Organic",
    "donut": "Organic",
    "cake": "Organic",
    "pizza": "Organic",
    "hot dog": "Organic",
}

COL_CATEGORY = "Waste category"
COL_PIXELS = "Visible area (pixels)"
COL_SHARE = "Share of detected waste area (%)"
COL_IMAGE_SHARE = "Share of full image (%)"

PALETTE = [
    (0, 220, 80), (255, 170, 0), (0, 160, 255), (220, 0, 220),
    (255, 230, 0), (0, 220, 220), (255, 80, 80), (150, 150, 255),
]


def suggest_category(label: str) -> str:
    return SUGGESTIONS.get(label.lower(), UNSURE)


def polygon_to_mask(polygon, width: int, height: int) -> np.ndarray:
    """Rasterise a polygon (list of (x, y) in image pixels) to a boolean mask."""
    points = [(float(x), float(y)) for x, y in polygon]
    if len(points) < 3:
        return np.zeros((height, width), dtype=bool)
    canvas = Image.new("L", (width, height), 0)
    ImageDraw.Draw(canvas).polygon(points, fill=255)
    return np.array(canvas) > 127


def extract_detections(result, width: int, height: int) -> list[dict]:
    """Convert an Ultralytics segmentation result into plain dictionaries.

    Polygons (`masks.xy`) are already in original-image coordinates, so the masks
    line up with the photo even when the model letterboxes the input.
    """
    if result.masks is None or result.boxes is None:
        return []

    polygons = result.masks.xy
    boxes = result.boxes
    class_ids = boxes.cls.tolist()
    confidences = boxes.conf.tolist()
    xyxy = boxes.xyxy.tolist()
    names = result.names

    detections: list[dict] = []
    for idx, polygon in enumerate(polygons):
        mask = polygon_to_mask(polygon, width, height)
        pixels = int(mask.sum())
        if pixels == 0:
            continue
        label = names.get(int(class_ids[idx]), str(int(class_ids[idx])))
        detections.append({
            "index": len(detections),
            "label": label,
            "confidence": float(confidences[idx]),
            "mask": mask,
            "pixels": pixels,
            "suggested": suggest_category(label),
            "box": [int(v) for v in xyxy[idx]],
        })
    return detections


def build_category_map(detections: list[dict], assignments: list[str], height: int, width: int) -> np.ndarray:
    """Per-pixel category ids. Higher-confidence detections claim overlapping pixels first."""
    category_map = np.full((height, width), -1, dtype=np.int16)
    order = sorted(range(len(detections)), key=lambda k: detections[k]["confidence"], reverse=True)
    for i in order:
        category_id = CATEGORIES.index(assignments[i])
        category_map[detections[i]["mask"] & (category_map == -1)] = category_id
    return category_map


def summarise(category_map: np.ndarray) -> pd.DataFrame:
    height, width = category_map.shape
    valid = int((category_map >= 0).sum())
    rows = []
    for category_id, category in enumerate(CATEGORIES):
        count = int((category_map == category_id).sum())
        if count:
            rows.append({
                COL_CATEGORY: category,
                COL_PIXELS: count,
                COL_SHARE: round(count / valid * 100, 2),
                COL_IMAGE_SHARE: round(count / (height * width) * 100, 2),
            })
    df = pd.DataFrame(rows, columns=[COL_CATEGORY, COL_PIXELS, COL_SHARE, COL_IMAGE_SHARE])
    return df.sort_values(COL_PIXELS, ascending=False).reset_index(drop=True)


def recoverable_share(df: pd.DataFrame) -> float:
    """Percent of detected area that has a clear route (recycle / compost / reuse)."""
    if df.empty:
        return 0.0
    total = df[COL_PIXELS].sum()
    unsure = df.loc[df[COL_CATEGORY] == UNSURE, COL_PIXELS].sum()
    return round((total - unsure) / total * 100, 1)


def render_overlay(image: Image.Image, detections: list[dict], opacity: float = 0.45,
                   show_boxes: bool = True, show_labels: bool = True) -> Image.Image:
    base = np.array(image.convert("RGB")).astype(np.float32)
    for i, det in enumerate(detections):
        color = np.array(PALETTE[i % len(PALETTE)], dtype=np.float32)
        mask = det["mask"]
        base[mask] = base[mask] * (1 - opacity) + color * opacity

    out = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    if not (show_boxes or show_labels):
        return out

    draw = ImageDraw.Draw(out)
    try:
        font = ImageFont.load_default(size=max(12, out.width // 45))
    except TypeError:  # very old Pillow without size support
        font = ImageFont.load_default()
    for i, det in enumerate(detections):
        color = PALETTE[i % len(PALETTE)]
        x1, y1, x2, y2 = det["box"]
        if show_boxes:
            draw.rectangle((x1, y1, x2, y2), outline=color, width=3)
        if show_labels:
            text = f"{i + 1}. {det['label']} {det['confidence']:.2f}"
            left, top, right, bottom = draw.textbbox((x1, y1), text, font=font)
            text_h = bottom - top
            ty = max(0, y1 - text_h - 6)
            draw.rectangle((x1, ty, x1 + (right - left) + 8, ty + text_h + 6), fill=color)
            draw.text((x1 + 4, ty + 2), text, fill=(0, 0, 0), font=font)
    return out


def build_report(source: str, width: int, height: int, detections: list[dict],
                 assignments: list[str], df: pd.DataFrame, recoverable: float) -> str:
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "image": {"width": width, "height": height},
        "recoverable_share_percent": recoverable,
        "objects": [
            {
                "id": i + 1,
                "model_label": det["label"],
                "confidence": round(det["confidence"], 3),
                "assigned_category": assignments[i],
                "bin": CATEGORY_INFO[assignments[i]]["bin"],
                "visible_pixels": det["pixels"],
            }
            for i, det in enumerate(detections)
        ],
        "category_summary": df.to_dict(orient="records"),
        "note": "Areas are visible pixel estimates from segmentation masks, not weight or volume.",
    }
    return json.dumps(report, indent=2)
