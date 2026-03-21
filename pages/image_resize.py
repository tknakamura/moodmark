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

from csv_to_html_dashboard import render_likepass_footer, require_dashboard_login
from tools.streamlit_branding import render_page_title_with_logo

MAX_FILES = 30
MAX_TOTAL_BYTES = 50 * 1024 * 1024
UPLOAD_TYPES = ["jpg", "jpeg", "png", "webp", "gif"]
OUTPUT_SIZE = (600, 600)
VISION_MAX_LONG_EDGE = 1024
# 縦長時、API の top が上寄りすぎて下端が欠けるのを防ぐ下限（tmax に対する比率）。0.85〜0.92 で調整可。
PORTRAIT_TOP_MIN_RATIO = float(os.getenv("AI_CROP_PORTRAIT_TOP_MIN_RATIO", "0.88"))


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
            f"Product photo. Preview {wv}x{hv}px (original {w}x{h}).\n"
            f"Square crop: full width {wv}px, height {sv}px. Integer `top` from 0 to {tmax}. "
            f"Larger `top` = window moves DOWN (shows lower part of image).\n"
            f"PRIORITY 1: The bottom edge of the main product (box/packaging) must be FULLY inside "
            f"the square—never clipped. A SMALL `top` cuts off the bottom of low-sitting products.\n"
            f"PRIORITY 2: For products near the bottom of the photo, `top` should be LARGE, "
            f"typically close to {tmax}.\n"
            f"PRIORITY 3: If there is visible background BELOW the product in the photo, you may "
            f"use `top` slightly less than {tmax} to show a thin strip of that background under the product. "
            f"If unsure or the product touches the photo bottom, use `top` near {tmax}.\n"
            f"Return ONLY JSON: {{\"top\": <integer>}}"
        )
    else:
        sv = hv
        lmax = max(0, wv - sv)
        prompt = (
            f"Product photo preview {wv}x{hv}px (original {w}x{h}px).\n"
            f"Square uses full height ({hv}px), slides horizontally. `left` in 0..{lmax}.\n"
            f"Keep full product visible. Avoid flush framing—leave a bit of natural background "
            f"between product and left/right edges of the square when possible.\n"
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
        default_top = tmax if tmax <= 0 else max(0, min(tmax, int(round(tmax * 0.95))))
        topv = int(obj.get("top", default_top))
        topv = max(0, min(tmax, topv))
        if tmax > 0:
            top_floor = int(tmax * PORTRAIT_TOP_MIN_RATIO)
            topv = max(topv, min(tmax, top_floor))
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


def jpeg_target_size_bytes(
    img: Image.Image, min_b: int = 10000, max_b: int = 20000
) -> Tuple[bytes, Optional[str]]:
    """JPEG を目標ファイルサイズ帯（デフォルト 10〜20KB）に近づける。"""

    def enc(q: int) -> bytes:
        b = io.BytesIO()
        img.save(b, format="JPEG", quality=q, optimize=True)
        return b.getvalue()

    for q in range(95, 39, -1):
        data = enc(q)
        if min_b <= len(data) <= max_b:
            return data, None

    d40 = enc(40)
    if len(d40) > max_b:
        return d40, "20KB以下に収まりませんでした（品質40で保存）"

    d95 = enc(95)
    if len(d95) < min_b:
        return d95, "10KB以上にできませんでした（画質上限で保存）"

    best_q, best_d = 40, d40
    best_dist = min(abs(len(d40) - min_b), abs(len(d40) - max_b))
    if len(d40) > max_b:
        best_dist = len(d40) - max_b
    for q in range(41, 96):
        d = enc(q)
        L = len(d)
        if min_b <= L <= max_b:
            return d, None
        if L < min_b:
            dist = min_b - L
        else:
            dist = L - max_b
        if dist < best_dist:
            best_dist = dist
            best_q, best_d = q, d
    kb = len(best_d) // 1024
    return best_d, f"目標10〜20KBから外れました（約{kb}KB・品質{best_q}）"


def image_bytes_to_square_jpeg(
    data: bytes,
    *,
    use_ai: bool = False,
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
) -> Tuple[bytes, Optional[str]]:
    """
    Returns (jpeg_bytes, warning_message or None).
    複数警告は最初の1件に集約する場合は呼び出し側で連結。
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
    jpeg, size_warn = jpeg_target_size_bytes(out)
    if size_warn:
        warn = f"{warn} {size_warn}".strip() if warn else size_warn
    return jpeg, warn


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

    require_dashboard_login()

    render_page_title_with_logo(
        "🖼️ 画像正方形クロップ",
        title_element_id="image-resize-title",
    )
    st.markdown(
        "短辺に合わせて長辺を切り落とし正方形にし、**600×600 ピクセル** の JPEG にします。"
    )
    st.caption(
        f"**上限**: 最大 {MAX_FILES} 枚・合計 {MAX_TOTAL_BYTES // (1024 * 1024)} MB まで。"
        " 対応: JPEG / PNG / WebP / GIF（HEIC 等は非対応）。"
        " **JPEG ファイルサイズは約 10〜20KB になるよう品質を自動調整** します。"
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
        render_likepass_footer()
        return

    files = list(uploaded)
    total_size = sum(f.size for f in files)

    if len(files) > MAX_FILES:
        st.error(f"画像は最大 {MAX_FILES} 枚までです（現在 {len(files)} 枚）。")
        render_likepass_footer()
        return
    if total_size > MAX_TOTAL_BYTES:
        st.error(
            f"合計サイズが上限を超えています（上限 {MAX_TOTAL_BYTES // (1024 * 1024)} MB、現在約 {total_size / (1024 * 1024):.1f} MB）。"
        )
        render_likepass_footer()
        return

    if use_ai and not os.getenv("OPENAI_API_KEY"):
        render_likepass_footer()
        return

    upload_sig = (tuple((f.name, f.size) for f in files), mode)
    if st.session_state.get("_img_crop_sig") != upload_sig:
        st.session_state.pop("_img_crop_results", None)
        st.session_state["_img_crop_sig"] = upload_sig

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
                    use_ai=use_ai,
                    api_key=api_key if use_ai else None,
                    model=model,
                )
                if warn:
                    st.warning(f"{f.name}: {warn}")
                stem = safe_stem(f.name)
                n = stem_count.get(stem, 0)
                stem_count[stem] = n + 1
                out_name = f"{stem}.jpg" if n == 0 else f"{stem}_{n + 1}.jpg"
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
        render_likepass_footer()
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

    render_likepass_footer()


main()
