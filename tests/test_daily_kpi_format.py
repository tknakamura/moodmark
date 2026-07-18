# -*- coding: utf-8 -*-
"""Daily KPI Bot フォーマット・前年同曜日比較の単体テスト。"""

from __future__ import annotations

from datetime import date

from tools.daily_kpi.format_slack import (
    build_parent_message,
    build_reply_alerts,
    build_reply_overview,
    build_slack_messages,
    fmt_metric_bullet,
    fmt_yoy_short,
    fmt_yen,
    short_path,
)
from tools.daily_kpi.ga4_collector import (
    DailyKpiReport,
    RankedRow,
    SiteDayMetrics,
    get_report_dates,
    yoy_pct,
)
from tools.daily_kpi.notify import _split_text


def test_yoy_pct():
    assert yoy_pct(110, 100) == 10.0
    assert yoy_pct(90, 100) == -10.0
    assert yoy_pct(0, 0) == 0.0
    assert yoy_pct(50, 0) is None


def test_fmt_yoy_short():
    assert fmt_yoy_short(110, 100) == "+10.0%"
    assert fmt_yoy_short(90, 100) == "-10.0%"


def test_fmt_yen():
    assert fmt_yen(10_500_000) == "¥10.5M"
    assert fmt_yen(50_000) == "¥5.0万"


def test_fmt_metric_bullet():
    line = fmt_metric_bullet("SS", 25550, 24980)
    assert line.startswith("• SS:")
    assert "*25,550*" in line
    assert "前年 24,980" in line
    assert "前年比 +2.3%" in line


def test_short_path():
    long = "/moodmarkgift/" + "a" * 60
    assert short_path(long, max_len=48).endswith("…")
    assert len(short_path(long, max_len=48)) == 48


def test_get_report_dates():
    from datetime import datetime, timezone, timedelta

    jst = timezone(timedelta(hours=9))
    ref = datetime(2026, 7, 11, 10, 0, tzinfo=jst)
    report_date, compare_date = get_report_dates(ref)
    assert report_date == date(2026, 7, 9)
    assert compare_date == date(2025, 7, 10)


def test_build_parent_message():
    report = DailyKpiReport(
        report_date=date(2026, 7, 10),
        compare_date=date(2026, 7, 3),
        moodmark=SiteDayMetrics(
            sessions=100_000,
            purchases=1812,
            purchase_revenue=10_500_000,
        ),
        moodmark_compare=SiteDayMetrics(purchases=1720),
        moodmarkgift=SiteDayMetrics(sessions=45_230),
        moodmarkgift_compare=SiteDayMetrics(sessions=43_800),
    )
    parent = build_parent_message(report)
    assert "MOO:D MARK Daily KPI（07/10）" in parent
    assert "EC: 購入 1,812件" in parent
    assert "IDEA: SS 45,230" in parent


def test_build_slack_messages_structure():
    report = DailyKpiReport(
        report_date=date(2026, 7, 10),
        compare_date=date(2026, 7, 3),
        moodmark=SiteDayMetrics(sessions=1000, purchases=10, purchase_revenue=50000),
        moodmarkgift=SiteDayMetrics(sessions=2000, page_views=5000),
        ec_devices=[RankedRow(label="mobile", sessions=800, purchases=8, purchase_revenue=40000)],
        idea_top_pages=[RankedRow(label="/moodmarkgift/article/", page_views=1000)],
    )
    parent, replies = build_slack_messages(report, run_url="https://example.com/run/1")
    assert "Daily KPI" in parent
    assert len(replies) == 4
    assert "サイト横断サマリ" in replies[0]
    assert "moodmark（EC）" in replies[1]
    assert "moodmarkgift（IDEA）" in replies[2]
    assert "example.com/run/1" in replies[3]


def test_no_markdown_tables_in_replies():
    report = DailyKpiReport(
        report_date=date(2026, 7, 10),
        compare_date=date(2026, 7, 3),
        moodmark=SiteDayMetrics(sessions=1000, purchases=10, purchase_revenue=50000),
        moodmarkgift=SiteDayMetrics(sessions=2000, page_views=5000),
        ec_devices=[RankedRow(label="mobile", sessions=800, purchases=8, purchase_revenue=40000)],
        ec_channels=[RankedRow(label="Organic Search", sessions=600, purchases=5, purchase_revenue=30000)],
        idea_top_pages=[RankedRow(label="/moodmarkgift/article/", page_views=1000)],
        idea_top_landings=[RankedRow(label="/moodmarkgift/", sessions=500)],
        idea_channels=[RankedRow(label="Organic Search", sessions=1500)],
    )
    _, replies = build_slack_messages(report)
    for reply in replies:
        assert "| ---" not in reply
        assert "| 指標 |" not in reply
        assert "| 項目 |" not in reply


def test_overview_uses_metric_bullets():
    report = DailyKpiReport(
        report_date=date(2026, 7, 10),
        compare_date=date(2026, 7, 3),
        moodmark=SiteDayMetrics(sessions=1000),
        moodmark_compare=SiteDayMetrics(sessions=900),
        moodmarkgift=SiteDayMetrics(sessions=2000),
        moodmarkgift_compare=SiteDayMetrics(sessions=1800),
    )
    text = build_reply_overview(report)
    assert "*EC*" in text
    assert "*IDEA*" in text
    assert "• SS:" in text
    assert "*合算*" in text


def test_build_reply_overview_contains_both_sites():
    report = DailyKpiReport(
        report_date=date(2026, 7, 10),
        compare_date=date(2026, 7, 3),
        moodmark=SiteDayMetrics(sessions=1000),
        moodmark_compare=SiteDayMetrics(sessions=900),
        moodmarkgift=SiteDayMetrics(sessions=2000),
        moodmarkgift_compare=SiteDayMetrics(sessions=1800),
    )
    text = build_reply_overview(report)
    assert "EC" in text
    assert "IDEA" in text
    assert "合算" in text


def test_ec_detail_uses_numbered_rankings():
    report = DailyKpiReport(
        report_date=date(2026, 7, 10),
        compare_date=date(2026, 7, 3),
        moodmark=SiteDayMetrics(sessions=1000, purchases=10, purchase_revenue=50000),
        ec_devices=[RankedRow(label="mobile", sessions=800, purchases=8, purchase_revenue=40000)],
    )
    _, replies = build_slack_messages(report)
    ec_detail = replies[1]
    assert "1. mobile —" in ec_detail
    assert "SS 800" in ec_detail


def test_build_reply_alerts_no_issues():
    report = DailyKpiReport(
        report_date=date(2026, 7, 10),
        compare_date=date(2026, 7, 3),
        moodmark=SiteDayMetrics(sessions=1000, bounce_rate=0.15, purchases=10),
        moodmark_compare=SiteDayMetrics(sessions=950, purchases=9),
        moodmarkgift=SiteDayMetrics(sessions=2000, bounce_rate=0.20),
        moodmarkgift_compare=SiteDayMetrics(sessions=1900),
    )
    text = build_reply_alerts(report)
    assert "異常なし" in text


def test_build_reply_alerts_bounce_high():
    report = DailyKpiReport(
        report_date=date(2026, 7, 10),
        compare_date=date(2026, 7, 3),
        moodmark=SiteDayMetrics(sessions=1000, bounce_rate=0.85, purchases=10),
        moodmark_compare=SiteDayMetrics(sessions=950, purchases=9),
        moodmarkgift=SiteDayMetrics(sessions=2000, bounce_rate=0.20),
        moodmarkgift_compare=SiteDayMetrics(sessions=1900),
    )
    text = build_reply_alerts(report)
    assert "直帰率が高い" in text


def test_split_text():
    long = "a" * 6000
    chunks = _split_text(long, limit=5000)
    assert len(chunks) == 2
    assert all(len(c) <= 5000 for c in chunks)
