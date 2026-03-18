#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
画像正方形クロップ（短辺基準・長辺方向の切り出し位置は中央 or AI 推定）
"""

import base64
import io
import json
import os
import sys
from typing import Optional, Tuple
import zipfile
from datetime import datetime

import streamlit as st
from PIL import Image, ImageOps

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from csv_to_html_dashboard import check_authentication, login_page

MAX_FILES = 30
MAX_TOTAL_BYTES = 50 * 1024 * 1024
UPLOAD_TYPES = ["jpg", "jpeg", "png", "webp", "gif"]
OUTPUT_SIZE = (600, 600)
VISION_MAX_LONG_EDGE = 1024


def _to_rgb(img: Image.Image) -> Image.Image:
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        return bg
    if img.mode == "P":
        img = img.convert("RGBA")
        return _to_rgb(img)
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def crop_square_at(img: Image.Image, left: int, top: int, s: int) -> Image.Image:
    w, h = img.size
    left = max(0, min(left, w - s))
    top = max(0, min(top, h - s))
    return img.crop((left, top, left + s, top + s))


def _extract_json_object(text: str) -> Optional[dict]:
    if not text:
        return None
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def openai_suggest_square_offset(
    img_rgb: Image.Image, api_key: str, model: str
) -> Tuple[int, int]:
    """
    Vision API で正方形クロップの (left, top) を推定。
    一辺 s = min(w,h)。縦長は top、横長は left を決める。
    """
    w, h = img_rgb.size
    s = min(w, h)
    if w == h:
        return 0, 0

    scale = VISION_MAX_LONG_EDGE / max(w, h)
    wv = max(1, round(w * scale))
    hv = max(1, round(h * scale))
    vis = img_rgb.resize((wv, hv), Image.Resampling.LANCZOS)
    vbuf = io.BytesIO()
    vis.save(vbuf, format="JPEG", quality=85)
    b64 = base64.standard_b64encode(vbuf.getvalue()).decode()

    portrait = h > w
    if portrait:
        sv = wv
        tmax = max(0, hv - sv)
        prompt = (
            f"This is a product photo. Preview size {wv}x{hv} pixels "
            f"(same aspect ratio as the original {w}x{h} image).\n"
            f"We crop a square using the FULL WIDTH ({wv}px), sliding vertically. "
            f"The square height equals the width ({sv}px).\n"
            f"Valid `top` (Y of top-left of square): integer from 0 to {tmax}. "
            f"top=0 shows the top of the image; top={tmax} shows the bottom.\n"
            f"If the product sits low in the frame (empty space on top), choose a LARGER top "
            f"so the product is not cut off at the bottom.\n"
            f"Return ONLY this JSON on one line, no markdown: {{\"top\": <integer>}}"
        )
    else:
        sv = hv
        lmax = max(0, wv - sv)
        prompt = (
            f"Product photo preview {wv}x{hv}px (original {w}x{h}px).\n"
            f"Square crop uses full height ({hv}px), slides horizontally. "
            f"Valid `left`: 0 to {lmax}.\n"
            f"Place the main product inside the square.\n"
            f"Return ONLY JSON: {{\"left\": <integer>}}"
        )

    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError("openai パッケージが必要です") from e

    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64}",
                            "detail": "low",
                        },
                    },
                ],
            }
        ],
        max_tokens=80,
    )
    text = (resp.choices[0].message.content or "").strip()
    obj = _extract_json_object(text)
    if not obj:
        raise ValueError(f"JSON parse failed: {text[:200]}")

    if portrait:
        topv = int(obj.get("top", tmax // 2))
        topv = max(0, min(tmax, topv))
        top = int(round(topv * h / hv))
        top = max(0, min(h - s, top))
        left = (w - s) // 2
    else:
        leftv = int(obj.get("left", lmax // 2))
        leftv = max(0, min(lmax, leftv))
        left = int(round(leftv * w / wv))
        left = max(0, min(w - s, left))
        top = (h - s) // 2

    return left, top


def image_bytes_to_square_jpeg(
    data: bytes,
    quality: int,
    *,
    use_ai: bool = False,
    api_key: str | None = None,
    model: str = "gpt-4o-mini",
) -> Tuple[bytes, Optional[str]]:
    """
    Returns (jpeg_bytes, warning_message or None).
    """
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)
    img = _to_rgb(img)
    w, h = img.size
    s = min(w, h)
    warn = None

    if use_ai and api_key:
        try:
            left, top = openai_suggest_square_offset(img, api_key, model)
        except Exception as e:
            left = (w - s) // 2
            top = (h - s) // 2
            warn = f"AI推定に失敗したため中央クロップにしました: {e}"
    else:
        left = (w - s) // 2
        top = (h - s) // 2

    out = crop_square_at(img, left, top, s)
    out = out.resize(OUTPUT_SIZE, Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue(), warn


def safe_stem(name: str) -> str:
    base = os.path.splitext(os.path.basename(name))[0]
    s = "".join(c if c.isalnum() or c in "._-" else "_" for c in base)
    return s or "image"


def main():
    st.set_page_config(
        page_title="MOODMARK 画像正方形クロップ",
        page_icon="🖼️",
        layout="wide",
    )

    if not check_authentication():
        login_page()
        return

    st.title("🖼️ 画像正方形クロップ")
    st.markdown(
        "短辺に合わせて長辺を切り落とし正方形にし、**600×600 ピクセル** の JPEG にします。"
    )
    st.caption(
        f"**上限**: 最大 {MAX_FILES} 枚・合計 {MAX_TOTAL_BYTES // (1024 * 1024)} MB まで。"
        " 対応: JPEG / PNG / WebP / GIF（HEIC 等は非対応）。"
    )

    mode = st.radio(
        "クロップモード",
        options=["通常モード（長辺を中央で均等に切り落とし）", "AIリサイズモード（商品が切れにくい位置を OpenAI が推定）"],
        horizontal=False,
        help="AIモードは画像が OpenAI に送信され、枚数分 API 課金されます。環境変数 OPENAI_API_KEY が必要です。",
    )
    use_ai = mode.startswith("AI")

    if use_ai:
        st.info(
            "**AIリサイズ**: 各画像が Vision API（OpenAI）に送信されます。"
            " 商品が下寄りの構図でも切りにくいよう、長辺方向の位置を推定します。"
        )
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.error(
                "OPENAI_API_KEY が設定されていません。Render の Environment にキーを設定してください。"
            )
        model = os.getenv("OPENAI_CROP_MODEL", "gpt-4o-mini")
        st.caption(f"使用モデル: `{model}`（`OPENAI_CROP_MODEL` で変更可）")

    uploaded = st.file_uploader(
        "画像を選択（複数可）",
        type=UPLOAD_TYPES,
        accept_multiple_files=True,
        help=f"最大{MAX_FILES}枚、合計50MBまで",
    )

    if not uploaded:
        st.info("画像をアップロードしてください。")
        return

    files = list(uploaded)
    total_size = sum(f.size for f in files)

    if len(files) > MAX_FILES:
        st.error(f"画像は最大 {MAX_FILES} 枚までです（現在 {len(files)} 枚）。")
        return
    if total_size > MAX_TOTAL_BYTES:
        st.error(
            f"合計サイズが上限を超えています（上限 {MAX_TOTAL_BYTES // (1024 * 1024)} MB、現在約 {total_size / (1024 * 1024):.1f} MB）。"
        )
        return

    if use_ai and not os.getenv("OPENAI_API_KEY"):
        return

    upload_sig = (tuple((f.name, f.size) for f in files), mode)
    if st.session_state.get("_img_crop_sig") != upload_sig:
        st.session_state.pop("_img_crop_results", None)
        st.session_state["_img_crop_sig"] = upload_sig

    quality = st.slider("JPEG 品質", min_value=85, max_value=95, value=90, step=1)

    api_key = os.getenv("OPENAI_API_KEY") or ""
    model = os.getenv("OPENAI_CROP_MODEL", "gpt-4o-mini")

    if st.button("正方形にクロップして生成", type="primary"):
        results = []
        errors = []
        stem_count = {}
        progress = st.progress(0.0) if use_ai and len(files) > 1 else None
        for idx, f in enumerate(files):
            try:
                raw = f.getvalue()
                jpeg, warn = image_bytes_to_square_jpeg(
                    raw,
                    quality,
                    use_ai=use_ai,
                    api_key=api_key if use_ai else None,
                    model=model,
                )
                if warn:
                    st.warning(f"{f.name}: {warn}")
                stem = safe_stem(f.name)
                n = stem_count.get(stem, 0)
                stem_count[stem] = n + 1
                out_name = (
                    f"{stem}_square.jpg" if n == 0 else f"{stem}_{n + 1}_square.jpg"
                )
                results.append((out_name, jpeg))
            except Exception as e:
                errors.append(f"{f.name}: {e}")
            if progress is not None:
                progress.progress((idx + 1) / len(files))
        if progress is not None:
            progress.empty()
        if errors:
            for msg in errors:
                st.error(msg)
        if results:
            st.session_state["_img_crop_results"] = results
            st.success(f"{len(results)} 件を生成しました。下からダウンロードできます。")
        elif not errors:
            st.warning("生成できた画像がありません。")

    results = st.session_state.get("_img_crop_results")
    if not results:
        return

    st.markdown("---")
    st.subheader("加工後のプレビュー")
    if len(results) == 1:
        _name, _data = results[0]
        st.image(io.BytesIO(_data), caption=_name, width=400)
    else:
        _cols = 3
        for _i in range(0, len(results), _cols):
            _row = results[_i : _i + _cols]
            _columns = st.columns(_cols)
            for _j, (_name, _data) in enumerate(_row):
                with _columns[_j]:
                    st.image(io.BytesIO(_data), caption=_name, width=200)

    st.markdown("---")
    st.subheader("ダウンロード")

    if len(files) == 1 and len(results) == 1:
        name, data = results[0]
        st.download_button(
            label=f"📥 {name} をダウンロード",
            data=data,
            file_name=name,
            mime="image/jpeg",
        )
    else:
        zbuf = io.BytesIO()
        used_names = set()
        with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, data in results:
                arc = name
                if arc in used_names:
                    base, ext = os.path.splitext(name)
                    n = 1
                    while f"{base}_{n}{ext}" in used_names:
                        n += 1
                    arc = f"{base}_{n}{ext}"
                used_names.add(arc)
                zf.writestr(arc, data)
        zbuf.seek(0)
        zip_name = f"moodmark_square_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        st.download_button(
            label=f"📥 全 {len(results)} 枚を ZIP でダウンロード",
            data=zbuf.getvalue(),
            file_name=zip_name,
            mime="application/zip",
        )


main()
