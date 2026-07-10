# -*- coding: utf-8 -*-
"""Daily KPI Bot — Slack メッセージ整形。"""

from __future__ import annotations

import json
import os
from typing import List, Optional, Tuple

from tools.daily_kpi.ga4_collector import (
    DailyKpiReport,
    RankedRow,
    SiteDayMetrics,
    wow_pct,
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


def fmt_wow(current: float, previous: float) -> str:
    pct = wow_pct(current, previous)
    if pct is None:
        return "WoW n/a"
    sign = "+" if pct >= 0 else ""
    return f"WoW {sign}{pct:.1f}%"


def fmt_wow_short(current: float, previous: float) -> str:
    pct = wow_pct(current, previous)
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
        f"CVR {fmt_pct(ec.purchase_cvr)}（{fmt_wow_short(ec.purchases, ec_prev.purchases)}）"
    )
    idea_line = (
        f"IDEA: SS {fmt_int(idea.sessions)}（{fmt_wow_short(idea.sessions, idea_prev.sessions)}）"
    )
    title = f"*MOO:D MARK Daily KPI（{d}）*"
    return f"{title}\n{ec_line} · {idea_line}"


def _site_row(
    label: str,
    current: SiteDayMetrics,
    previous: SiteDayMetrics,
    *,
    include_purchase: bool,
) -> List[str]:
    rows = [
        f"| {label} | {fmt_int(current.sessions)} | {fmt_int(previous.sessions)} | {fmt_wow_short(current.sessions, previous.sessions)} |",
        f"| {label} AU | {fmt_int(current.active_users)} | {fmt_int(previous.active_users)} | {fmt_wow_short(current.active_users, previous.active_users)} |",
        f"| {label} PV | {fmt_int(current.page_views)} | {fmt_int(previous.page_views)} | {fmt_wow_short(current.page_views, previous.page_views)} |",
        f"| {label} 直帰率 | {fmt_pct(current.bounce_rate * 100 if current.bounce_rate <= 1 else current.bounce_rate)} | {fmt_pct(previous.bounce_rate * 100 if previous.bounce_rate <= 1 else previous.bounce_rate)} | — |",
        f"| {label} 滞在 | {fmt_duration(current.avg_session_duration)} | {fmt_duration(previous.avg_session_duration)} | — |",
    ]
    if include_purchase:
        rows.extend(
            [
                f"| {label} 購入 | {fmt_int(current.purchases)} | {fmt_int(previous.purchases)} | {fmt_wow_short(current.purchases, previous.purchases)} |",
                f"| {label} 売上 | {fmt_yen(current.purchase_revenue)} | {fmt_yen(previous.purchase_revenue)} | {fmt_wow_short(current.purchase_revenue, previous.purchase_revenue)} |",
            ]
        )
    return rows


def build_reply_overview(report: DailyKpiReport) -> str:
    rd = report.report_date.strftime("%Y-%m-%d")
    cd = report.compare_date.strftime("%Y-%m-%d")
    combined_cur, combined_prev = _combined_sessions(report)

    lines = [
        f"*📊 サイト横断サマリ*（{rd} vs {cd}）",
        "",
        "| 指標 | 対象日 | 前週同曜 | WoW |",
        "| --- | ---: | ---: | ---: |",
    ]
    lines.extend(
        _site_row("EC", report.moodmark, report.moodmark_compare, include_purchase=True)
    )
    lines.extend(
        _site_row(
            "IDEA",
            report.moodmarkgift,
            report.moodmarkgift_compare,
            include_purchase=False,
        )
    )
    lines.append(
        f"| 合算 SS | {fmt_int(combined_cur)} | {fmt_int(combined_prev)} | {fmt_wow_short(combined_cur, combined_prev)} |"
    )
    if report.errors:
        lines.extend(["", "*⚠️ データ取得警告*", *[f"• {e}" for e in report.errors]])
    return "\n".join(lines)


def _ranked_ec_table(title: str, rows: List[RankedRow]) -> List[str]:
    lines = [title, "", "| 項目 | SS | 購入 | 売上 |", "| --- | ---: | ---: | ---: |"]
    if not rows:
        lines.append("| — | — | — | — |")
        return lines
    for row in rows:
        lines.append(
            f"| {row.label} | {fmt_int(row.sessions)} | {fmt_int(row.purchases)} | {fmt_yen(row.purchase_revenue)} |"
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
        f"直帰率: {fmt_pct(ec.bounce_rate * 100 if ec.bounce_rate <= 1 else ec.bounce_rate)}",
        "",
    ]
    lines.extend(_ranked_ec_table("*デバイス別 Top5*", report.ec_devices))
    lines.append("")
    lines.extend(
        _ranked_ec_table("*流入チャネル Top5*", report.ec_channels)
    )
    return "\n".join(lines)


def build_reply_idea_detail(report: DailyKpiReport) -> str:
    idea = report.moodmarkgift
    lines = [
        "*📖 moodmarkgift（IDEA）コンテンツ詳細*",
        "",
        f"セッション: *{fmt_int(idea.sessions)}* · PV: *{fmt_int(idea.page_views)}* · "
        f"直帰率: {fmt_pct(idea.bounce_rate * 100 if idea.bounce_rate <= 1 else idea.bounce_rate)} · "
        f"滞在: {fmt_duration(idea.avg_session_duration)}",
        "",
        "*記事 PV Top5*",
        "",
        "| ページ | PV |",
        "| --- | ---: |",
    ]
    if report.idea_top_pages:
        for row in report.idea_top_pages:
            lines.append(f"| `{row.label}` | {fmt_int(row.page_views)} |")
    else:
        lines.append("| — | — |")

    lines.extend(["", "*ランディング Top5*", "", "| LP | SS |", "| --- | ---: |"])
    if report.idea_top_landings:
        for row in report.idea_top_landings:
            lines.append(f"| `{row.label}` | {fmt_int(row.sessions)} |")
    else:
        lines.append("| — | — |")

    lines.extend(
        ["", "*流入チャネル Top5*", "", "| チャネル | SS |", "| --- | ---: |"]
    )
    if report.idea_channels:
        for row in report.idea_channels:
            lines.append(f"| {row.label} | {fmt_int(row.sessions)} |")
    else:
        lines.append("| — | — |")

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

        wow_sessions = wow_pct(current.sessions, previous.sessions)
        if wow_sessions is not None and wow_sessions <= session_drop_threshold:
            alerts.append(
                f"⚠️ {site_label} セッション急落: {fmt_wow(current.sessions, previous.sessions)}"
            )

    wow_purchases = wow_pct(report.moodmark.purchases, report.moodmark_compare.purchases)
    if wow_purchases is not None and wow_purchases <= purchase_drop_threshold:
        alerts.append(
            f"⚠️ EC 購入数急落: {fmt_wow(report.moodmark.purchases, report.moodmark_compare.purchases)}"
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
