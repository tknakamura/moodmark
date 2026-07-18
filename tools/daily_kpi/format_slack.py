# -*- coding: utf-8 -*-
"""Daily KPI Bot — Slack メッセージ整形。"""

from __future__ import annotations

import json
import os
from typing import Callable, List, Optional, Tuple

from tools.daily_kpi.ga4_collector import (
    DailyKpiReport,
    RankedRow,
    SiteDayMetrics,
    yoy_pct,
)


def _load_alert_config() -> dict:
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "config",
        "analytics_config.json",
    )
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("alerts", {}).get("performance_threshold", {})
    except (OSError, json.JSONDecodeError):
        return {}


def fmt_int(value: float) -> str:
    return f"{int(round(value)):,}"


def fmt_pct(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}%"


def fmt_yoy(current: float, previous: float) -> str:
    pct = yoy_pct(current, previous)
    if pct is None:
        return "前年比 n/a"
    sign = "+" if pct >= 0 else ""
    return f"前年比 {sign}{pct:.1f}%"


def fmt_yoy_short(current: float, previous: float) -> str:
    pct = yoy_pct(current, previous)
    if pct is None:
        return "n/a"
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%"


def fmt_yen(value: float) -> str:
    if value >= 1_000_000:
        return f"¥{value / 1_000_000:.1f}M"
    if value >= 10_000:
        return f"¥{value / 10_000:.1f}万"
    return f"¥{int(round(value)):,}"


def fmt_duration(seconds: float) -> str:
    total = int(round(seconds))
    minutes, secs = divmod(total, 60)
    if minutes >= 60:
        hours, minutes = divmod(minutes, 60)
        return f"{hours}h{minutes}m"
    return f"{minutes}m{secs}s"


def short_path(path: str, max_len: int = 48) -> str:
    """長い pagePath を Slack 向けに短縮。"""
    p = (path or "").strip()
    if len(p) <= max_len:
        return p
    keep = max_len - 1
    return p[:keep] + "…"


def fmt_metric_bullet(
    label: str,
    current: float,
    previous: float,
    *,
    formatter: Callable[[float], str] = fmt_int,
    show_yoy: bool = True,
) -> str:
    cur_s = formatter(current)
    prev_s = formatter(previous)
    if show_yoy:
        return f"• {label}: *{cur_s}*（前年 {prev_s} / 前年比 {fmt_yoy_short(current, previous)}）"
    return f"• {label}: *{cur_s}*（前年 {prev_s}）"


def fmt_rank_bullet(rank: int, label: str, parts: List[str]) -> str:
    detail = " / ".join(parts)
    return f"{rank}. {label} — {detail}"


def _bounce_rate_fmt(value: float) -> str:
    pct = value * 100 if value <= 1 else value
    return fmt_pct(pct)


def _combined_sessions(report: DailyKpiReport) -> Tuple[float, float]:
    cur = report.moodmark.sessions + report.moodmarkgift.sessions
    prev = report.moodmark_compare.sessions + report.moodmarkgift_compare.sessions
    return cur, prev


def build_parent_message(report: DailyKpiReport) -> str:
    d = report.report_date.strftime("%m/%d")
    ec = report.moodmark
    ec_prev = report.moodmark_compare
    idea = report.moodmarkgift
    idea_prev = report.moodmarkgift_compare

    ec_line = (
        f"EC: 購入 {fmt_int(ec.purchases)}件 / {fmt_yen(ec.purchase_revenue)} / "
        f"CVR {fmt_pct(ec.purchase_cvr)}（前年比 {fmt_yoy_short(ec.purchases, ec_prev.purchases)}）"
    )
    idea_line = (
        f"IDEA: SS {fmt_int(idea.sessions)}（前年比 {fmt_yoy_short(idea.sessions, idea_prev.sessions)}）"
    )
    title = f"*MOO:D MARK Daily KPI（{d}）*"
    return f"{title}\n{ec_line} · {idea_line}"


def _site_metric_bullets(
    current: SiteDayMetrics,
    previous: SiteDayMetrics,
    *,
    include_purchase: bool,
) -> List[str]:
    lines = [
        fmt_metric_bullet("SS", current.sessions, previous.sessions),
        fmt_metric_bullet("AU", current.active_users, previous.active_users),
        fmt_metric_bullet("PV", current.page_views, previous.page_views),
        fmt_metric_bullet(
            "直帰率",
            current.bounce_rate,
            previous.bounce_rate,
            formatter=_bounce_rate_fmt,
            show_yoy=False,
        ),
        fmt_metric_bullet(
            "滞在",
            current.avg_session_duration,
            previous.avg_session_duration,
            formatter=fmt_duration,
            show_yoy=False,
        ),
    ]
    if include_purchase:
        lines.extend(
            [
                fmt_metric_bullet("購入", current.purchases, previous.purchases),
                fmt_metric_bullet(
                    "売上",
                    current.purchase_revenue,
                    previous.purchase_revenue,
                    formatter=fmt_yen,
                ),
            ]
        )
    return lines


def build_reply_overview(report: DailyKpiReport) -> str:
    rd = report.report_date.strftime("%Y-%m-%d")
    cd = report.compare_date.strftime("%Y-%m-%d")
    combined_cur, combined_prev = _combined_sessions(report)

    lines = [
        f"*📊 サイト横断サマリ*（{rd} vs {cd}）",
        "",
        "*EC*",
        *_site_metric_bullets(
            report.moodmark, report.moodmark_compare, include_purchase=True
        ),
        "",
        "*IDEA*",
        *_site_metric_bullets(
            report.moodmarkgift, report.moodmarkgift_compare, include_purchase=False
        ),
        "",
        "*合算*",
        fmt_metric_bullet("SS", combined_cur, combined_prev),
    ]
    if report.errors:
        lines.extend(["", "*⚠️ データ取得警告*", *[f"• {e}" for e in report.errors]])
    return "\n".join(lines)


def _ranked_ec_bullets(rows: List[RankedRow]) -> List[str]:
    if not rows:
        return ["（データなし）"]
    lines: List[str] = []
    for i, row in enumerate(rows, 1):
        lines.append(
            fmt_rank_bullet(
                i,
                row.label,
                [
                    f"SS {fmt_int(row.sessions)}",
                    f"購入 {fmt_int(row.purchases)}",
                    fmt_yen(row.purchase_revenue),
                ],
            )
        )
    return lines


def build_reply_ec_detail(report: DailyKpiReport) -> str:
    ec = report.moodmark
    lines = [
        "*🛒 moodmark（EC）購買詳細*",
        "",
        f"購入: *{fmt_int(ec.purchases)}* 件 / 売上: *{fmt_yen(ec.purchase_revenue)}* / "
        f"CVR: *{fmt_pct(ec.purchase_cvr)}* / AOV: *{fmt_yen(ec.avg_order_value)}*",
        f"セッション: {fmt_int(ec.sessions)} · PV: {fmt_int(ec.page_views)} · "
        f"直帰率: {_bounce_rate_fmt(ec.bounce_rate)}",
        "",
        "*デバイス別 Top5*",
        *_ranked_ec_bullets(report.ec_devices),
        "",
        "*流入チャネル Top5*",
        *_ranked_ec_bullets(report.ec_channels),
    ]
    return "\n".join(lines)


def _ranked_page_bullets(rows: List[RankedRow], *, value_label: str) -> List[str]:
    if not rows:
        return ["（データなし）"]
    lines: List[str] = []
    for i, row in enumerate(rows, 1):
        if value_label == "PV":
            value = fmt_int(row.page_views)
        else:
            value = fmt_int(row.sessions)
        lines.append(f"{i}. `{short_path(row.label)}` — {value_label} {value}")
    return lines


def _ranked_channel_bullets(rows: List[RankedRow]) -> List[str]:
    if not rows:
        return ["（データなし）"]
    return [
        fmt_rank_bullet(i, row.label, [f"SS {fmt_int(row.sessions)}"])
        for i, row in enumerate(rows, 1)
    ]


def build_reply_idea_detail(report: DailyKpiReport) -> str:
    idea = report.moodmarkgift
    lines = [
        "*📖 moodmarkgift（IDEA）コンテンツ詳細*",
        "",
        f"セッション: *{fmt_int(idea.sessions)}* · PV: *{fmt_int(idea.page_views)}* · "
        f"直帰率: {_bounce_rate_fmt(idea.bounce_rate)} · "
        f"滞在: {fmt_duration(idea.avg_session_duration)}",
        "",
        "*記事 PV Top5*",
        *_ranked_page_bullets(report.idea_top_pages, value_label="PV"),
        "",
        "*ランディング Top5*",
        *_ranked_page_bullets(report.idea_top_landings, value_label="SS"),
        "",
        "*流入チャネル Top5*",
        *_ranked_channel_bullets(report.idea_channels),
    ]
    return "\n".join(lines)


def _bounce_rate_pct(metrics: SiteDayMetrics) -> float:
    br = metrics.bounce_rate
    return br * 100 if br <= 1 else br


def build_reply_alerts(report: DailyKpiReport, *, run_url: Optional[str] = None) -> str:
    thresholds = _load_alert_config()
    bounce_threshold = float(thresholds.get("bounce_rate", 0.7)) * 100
    session_drop_threshold = -20.0
    purchase_drop_threshold = -30.0

    alerts: List[str] = []

    for site_label, current, previous in (
        ("EC", report.moodmark, report.moodmark_compare),
        ("IDEA", report.moodmarkgift, report.moodmarkgift_compare),
    ):
        br = _bounce_rate_pct(current)
        if br > bounce_threshold:
            alerts.append(f"⚠️ {site_label} 直帰率が高い: {fmt_pct(br)}（閾値 {fmt_pct(bounce_threshold)}）")

        yoy_sessions = yoy_pct(current.sessions, previous.sessions)
        if yoy_sessions is not None and yoy_sessions <= session_drop_threshold:
            alerts.append(
                f"⚠️ {site_label} セッション急落: {fmt_yoy(current.sessions, previous.sessions)}"
            )

    yoy_purchases = yoy_pct(report.moodmark.purchases, report.moodmark_compare.purchases)
    if yoy_purchases is not None and yoy_purchases <= purchase_drop_threshold:
        alerts.append(
            f"⚠️ EC 購入数急落: {fmt_yoy(report.moodmark.purchases, report.moodmark_compare.purchases)}"
        )

    lines = ["*🔔 アラート・補足*", ""]
    if alerts:
        lines.extend(alerts)
    else:
        lines.append("異常なし")

    if report.errors:
        lines.extend(["", "*データ取得警告*", *[f"• {e}" for e in report.errors]])

    if run_url:
        lines.extend(["", f"<{run_url}|GitHub Actions の実行ログ>"])

    return "\n".join(lines)


def build_slack_messages(
    report: DailyKpiReport,
    *,
    run_url: Optional[str] = None,
) -> Tuple[str, List[str]]:
    """親メッセージとスレッド返信リストを返す。"""
    parent = build_parent_message(report)
    replies = [
        build_reply_overview(report),
        build_reply_ec_detail(report),
        build_reply_idea_detail(report),
        build_reply_alerts(report, run_url=run_url),
    ]
    return parent, replies
