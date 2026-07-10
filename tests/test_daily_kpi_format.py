# -*- coding: utf-8 -*-
"""Daily KPI Bot フォーマット・WoW 計算の単体テスト。"""

from __future__ import annotations

from datetime import date

from tools.daily_kpi.format_slack import (
    build_parent_message,
    build_reply_alerts,
    build_reply_overview,
    build_slack_messages,
    fmt_wow_short,
    fmt_yen,
)
from tools.daily_kpi.ga4_collector import (
    DailyKpiReport,
    RankedRow,
    SiteDayMetrics,
    get_report_dates,
    wow_pct,
)
from tools.daily_kpi.notify import _split_text


def test_wow_pct():
    assert wow_pct(110, 100) == 10.0
    assert wow_pct(90, 100) == -10.0
    assert wow_pct(0, 0) == 0.0
    assert wow_pct(50, 0) is None


def test_fmt_wow_short():
    assert fmt_wow_short(110, 100) == "+10.0%"
    assert fmt_wow_short(90, 100) == "-10.0%"


def test_fmt_yen():
    assert fmt_yen(10_500_000) == "¥10.5M"
    assert fmt_yen(50_000) == "¥5.0万"


def test_get_report_dates():
    from datetime import datetime, timezone, timedelta

    jst = timezone(timedelta(hours=9))
    ref = datetime(2026, 7, 11, 10, 0, tzinfo=jst)
    report_date, compare_date = get_report_dates(ref)
    assert report_date == date(2026, 7, 9)
    assert compare_date == date(2026, 7, 2)


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
    assert "合算 SS" in text


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
