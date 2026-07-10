# -*- coding: utf-8 -*-
"""GA4 前々日・WoW 日次 KPI データ収集。"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from analytics.google_apis_integration import GoogleAPIsIntegration  # noqa: E402

JST = timezone(timedelta(hours=9))
SITES = ("moodmark", "moodmarkgift")
# GA4 日次確定の遅延を避けるため、毎朝 09:00 JST 時点では前々日を対象とする
REPORT_LAG_DAYS = 2


@dataclass
class SiteDayMetrics:
    sessions: float = 0.0
    active_users: float = 0.0
    page_views: float = 0.0
    bounce_rate: float = 0.0
    avg_session_duration: float = 0.0
    purchases: float = 0.0
    purchase_revenue: float = 0.0

    @property
    def purchase_cvr(self) -> float:
        if self.sessions <= 0:
            return 0.0
        return self.purchases / self.sessions * 100.0

    @property
    def avg_order_value(self) -> float:
        if self.purchases <= 0:
            return 0.0
        return self.purchase_revenue / self.purchases


@dataclass
class RankedRow:
    label: str
    sessions: float = 0.0
    page_views: float = 0.0
    purchases: float = 0.0
    purchase_revenue: float = 0.0


@dataclass
class DailyKpiReport:
    report_date: date
    compare_date: date
    moodmark: SiteDayMetrics = field(default_factory=SiteDayMetrics)
    moodmark_compare: SiteDayMetrics = field(default_factory=SiteDayMetrics)
    moodmarkgift: SiteDayMetrics = field(default_factory=SiteDayMetrics)
    moodmarkgift_compare: SiteDayMetrics = field(default_factory=SiteDayMetrics)
    ec_devices: List[RankedRow] = field(default_factory=list)
    ec_channels: List[RankedRow] = field(default_factory=list)
    idea_top_pages: List[RankedRow] = field(default_factory=list)
    idea_top_landings: List[RankedRow] = field(default_factory=list)
    idea_channels: List[RankedRow] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def get_report_dates(
    reference: Optional[datetime] = None,
    *,
    offset_days: int = 0,
) -> tuple[date, date]:
    """前々日（JST）と前週同曜日を返す。offset_days で対象日をさらに過去へずらせる（テスト用）。"""
    now_jst = reference or datetime.now(JST)
    target = (now_jst - timedelta(days=REPORT_LAG_DAYS + offset_days)).date()
    compare = target - timedelta(days=7)
    return target, compare


def wow_pct(current: float, previous: float) -> Optional[float]:
    if previous == 0:
        if current == 0:
            return 0.0
        return None
    return (current - previous) / previous * 100.0


def _date_str(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def _is_moodmark_ec_path(path: str) -> bool:
    p = path or ""
    return "/moodmark" in p and "/moodmarkgift/" not in p


def _safe_sum(df: pd.DataFrame, col: str) -> float:
    if df.empty or col not in df.columns:
        return 0.0
    return float(df[col].sum())


def _safe_mean(df: pd.DataFrame, col: str) -> float:
    if df.empty or col not in df.columns:
        return 0.0
    return float(df[col].mean())


def _metrics_from_summary_df(df: pd.DataFrame) -> SiteDayMetrics:
    return SiteDayMetrics(
        sessions=_safe_sum(df, "sessions"),
        active_users=_safe_sum(df, "activeUsers"),
        page_views=_safe_sum(df, "screenPageViews"),
        bounce_rate=_safe_mean(df, "bounceRate"),
        avg_session_duration=_safe_mean(df, "averageSessionDuration"),
        purchases=_safe_sum(df, "ecommercePurchases"),
        purchase_revenue=_safe_sum(df, "purchaseRevenue"),
    )


def _fetch_site_summary(
    api: GoogleAPIsIntegration,
    day: date,
    site_name: str,
    *,
    include_purchase: bool,
) -> SiteDayMetrics:
    metrics = [
        "sessions",
        "activeUsers",
        "screenPageViews",
        "bounceRate",
        "averageSessionDuration",
    ]
    if include_purchase:
        metrics.extend(["ecommercePurchases", "purchaseRevenue"])

    ds = _date_str(day)
    df = api.get_ga4_data_custom_range(
        ds,
        ds,
        metrics=metrics,
        dimensions=["date"],
        site_name=site_name,
    )
    return _metrics_from_summary_df(df)


def _fetch_ec_purchase_landing(
    api: GoogleAPIsIntegration,
    day: date,
) -> SiteDayMetrics:
    """EC 購入 KPI（landingPage ベース、analyze_7days_purchase_only と同方式）。"""
    ds = _date_str(day)
    df = api.get_ga4_data_custom_range(
        ds,
        ds,
        metrics=[
            "sessions",
            "activeUsers",
            "screenPageViews",
            "bounceRate",
            "averageSessionDuration",
            "ecommercePurchases",
            "purchaseRevenue",
        ],
        dimensions=["date", "landingPage"],
        site_name="moodmark",
    )
    if df.empty:
        return SiteDayMetrics()
    ec = df[df["landingPage"].apply(_is_moodmark_ec_path)]
    if ec.empty:
        return SiteDayMetrics()
    grouped = ec.groupby("date", as_index=False).agg(
        {
            "sessions": "sum",
            "activeUsers": "sum",
            "screenPageViews": "sum",
            "bounceRate": "mean",
            "averageSessionDuration": "mean",
            "ecommercePurchases": "sum",
            "purchaseRevenue": "sum",
        }
    )
    return _metrics_from_summary_df(grouped)


def _fetch_ec_breakdown(
    api: GoogleAPIsIntegration,
    day: date,
    dimension: str,
    limit: int = 5,
) -> List[RankedRow]:
    ds = _date_str(day)
    df = api.get_ga4_data_custom_range(
        ds,
        ds,
        metrics=["sessions", "ecommercePurchases", "purchaseRevenue"],
        dimensions=[dimension],
        site_name="moodmark",
    )
    if df.empty or dimension not in df.columns:
        return []
    agg = (
        df.groupby(dimension, as_index=False)
        .agg(
            {
                "sessions": "sum",
                "ecommercePurchases": "sum",
                "purchaseRevenue": "sum",
            }
        )
        .sort_values("sessions", ascending=False)
        .head(limit)
    )
    rows: List[RankedRow] = []
    for _, row in agg.iterrows():
        rows.append(
            RankedRow(
                label=str(row[dimension]),
                sessions=float(row["sessions"]),
                purchases=float(row["ecommercePurchases"]),
                purchase_revenue=float(row["purchaseRevenue"]),
            )
        )
    return rows


def _fetch_idea_top_pages(
    api: GoogleAPIsIntegration,
    day: date,
    limit: int = 5,
) -> List[RankedRow]:
    ds = _date_str(day)
    df = api.get_ga4_data_custom_range(
        ds,
        ds,
        metrics=["screenPageViews"],
        dimensions=["pagePath"],
        site_name="moodmarkgift",
    )
    if df.empty:
        return []
    agg = (
        df.groupby("pagePath", as_index=False)
        .agg({"screenPageViews": "sum"})
        .sort_values("screenPageViews", ascending=False)
        .head(limit)
    )
    return [
        RankedRow(label=str(r["pagePath"]), page_views=float(r["screenPageViews"]))
        for _, r in agg.iterrows()
    ]


def _fetch_idea_top_landings(
    api: GoogleAPIsIntegration,
    day: date,
    limit: int = 5,
) -> List[RankedRow]:
    ds = _date_str(day)
    df = api.get_ga4_data_custom_range(
        ds,
        ds,
        metrics=["sessions"],
        dimensions=["landingPage"],
        site_name="moodmarkgift",
    )
    if df.empty:
        return []
    agg = (
        df.groupby("landingPage", as_index=False)
        .agg({"sessions": "sum"})
        .sort_values("sessions", ascending=False)
        .head(limit)
    )
    return [
        RankedRow(label=str(r["landingPage"]), sessions=float(r["sessions"]))
        for _, r in agg.iterrows()
    ]


def _fetch_idea_channels(
    api: GoogleAPIsIntegration,
    day: date,
    limit: int = 5,
) -> List[RankedRow]:
    ds = _date_str(day)
    df = api.get_ga4_data_custom_range(
        ds,
        ds,
        metrics=["sessions"],
        dimensions=["sessionDefaultChannelGroup"],
        site_name="moodmarkgift",
    )
    if df.empty:
        return []
    dim = "sessionDefaultChannelGroup"
    agg = (
        df.groupby(dim, as_index=False)
        .agg({"sessions": "sum"})
        .sort_values("sessions", ascending=False)
        .head(limit)
    )
    return [
        RankedRow(label=str(r[dim]), sessions=float(r["sessions"]))
        for _, r in agg.iterrows()
    ]


def collect_daily_kpi(
    *,
    report_date: Optional[date] = None,
    compare_date: Optional[date] = None,
    api: Optional[GoogleAPIsIntegration] = None,
) -> DailyKpiReport:
    """前々日・WoW 比較の Daily KPI レポートを収集。"""
    if report_date is None or compare_date is None:
        report_date, compare_date = get_report_dates()

    report = DailyKpiReport(report_date=report_date, compare_date=compare_date)
    client = api or GoogleAPIsIntegration()

    if not client.ga4_service:
        report.errors.append("GA4 サービスが初期化されていません（GOOGLE_CREDENTIALS_JSON を確認）")
        return report

    try:
        report.moodmark = _fetch_ec_purchase_landing(client, report_date)
        report.moodmark_compare = _fetch_ec_purchase_landing(client, compare_date)
    except Exception as exc:
        report.errors.append(f"moodmark EC KPI 取得エラー: {exc}")

    try:
        report.moodmarkgift = _fetch_site_summary(
            client, report_date, "moodmarkgift", include_purchase=False
        )
        report.moodmarkgift_compare = _fetch_site_summary(
            client, compare_date, "moodmarkgift", include_purchase=False
        )
    except Exception as exc:
        report.errors.append(f"moodmarkgift KPI 取得エラー: {exc}")

    try:
        report.ec_devices = _fetch_ec_breakdown(client, report_date, "deviceCategory")
        report.ec_channels = _fetch_ec_breakdown(
            client, report_date, "sessionDefaultChannelGroup"
        )
    except Exception as exc:
        report.errors.append(f"EC 内訳取得エラー: {exc}")

    try:
        report.idea_top_pages = _fetch_idea_top_pages(client, report_date)
        report.idea_top_landings = _fetch_idea_top_landings(client, report_date)
        report.idea_channels = _fetch_idea_channels(client, report_date)
    except Exception as exc:
        report.errors.append(f"IDEA 内訳取得エラー: {exc}")

    return report
