#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
画像正方形クロップ（短辺基準・長辺を中央で均等に切り落とし）
"""

import io
import os
import sys
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


def crop_square(img: Image.Image) -> Image.Image:
    w, h = img.size
    s = min(w, h)
    left = (w - s) // 2
    top = (h - s) // 2
    return img.crop((left, top, left + s, top + s))


def image_bytes_to_square_jpeg(data: bytes, quality: int) -> bytes:
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)
    img = _to_rgb(img)
    out = crop_square(img)
    out = out.resize(OUTPUT_SIZE, Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


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
        "短辺に合わせて長辺を中央から均等に切り落とし、正方形にしたうえで **600×600 ピクセル** の JPEG にします。"
    )
    st.caption(
        f"**上限**: 最大 {MAX_FILES} 枚・合計 {MAX_TOTAL_BYTES // (1024 * 1024)} MB まで。"
        " 対応: JPEG / PNG / WebP / GIF（HEIC 等は非対応）。"
    )

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

    upload_sig = tuple((f.name, f.size) for f in files)
    if st.session_state.get("_img_crop_sig") != upload_sig:
        st.session_state.pop("_img_crop_results", None)
        st.session_state["_img_crop_sig"] = upload_sig

    quality = st.slider("JPEG 品質", min_value=85, max_value=95, value=90, step=1)

    if st.button("正方形にクロップして生成", type="primary"):
        results = []
        errors = []
        stem_count = {}
        for f in files:
            try:
                raw = f.getvalue()
                jpeg = image_bytes_to_square_jpeg(raw, quality)
                stem = safe_stem(f.name)
                n = stem_count.get(stem, 0)
                stem_count[stem] = n + 1
                out_name = (
                    f"{stem}_square.jpg" if n == 0 else f"{stem}_{n + 1}_square.jpg"
                )
                results.append((out_name, jpeg))
            except Exception as e:
                errors.append(f"{f.name}: {e}")
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
