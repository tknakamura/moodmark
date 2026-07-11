# -*- coding: utf-8 -*-
"""Daily KPI Bot GA4 集計の単体テスト。"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pandas as pd

from tools.daily_kpi.ga4_collector import (
    _fetch_ec_purchase_landing,
    _fetch_engagement_metrics,
    _is_moodmark_ec_path,
    _metrics_from_landing_df,
)


def test_is_moodmark_ec_path():
    assert _is_moodmark_ec_path("/moodmark/shop/")
    assert not _is_moodmark_ec_path("/moodmarkgift/10128")
    assert not _is_moodmark_ec_path("")


def test_metrics_from_landing_df_excludes_engagement():
    df = pd.DataFrame(
        [
            {
                "sessions": 100,
                "activeUsers": 80,
                "screenPageViews": 200,
                "ecommercePurchases": 5,
                "purchaseRevenue": 50000,
            }
        ]
    )
    m = _metrics_from_landing_df(df)
    assert m.sessions == 100
    assert m.purchases == 5
    assert m.bounce_rate == 0.0
    assert m.avg_session_duration == 0.0


def test_fetch_engagement_metrics_from_site_summary():
    api = MagicMock()
    api.get_ga4_data_custom_range.return_value = pd.DataFrame(
        [{"bounceRate": 0.144, "averageSessionDuration": 275.0}]
    )
    bounce, duration = _fetch_engagement_metrics(api, date(2026, 7, 9), "moodmark")
    assert bounce == 0.144
    assert duration == 275.0


def test_fetch_ec_purchase_landing_uses_site_engagement_not_lp_mean():
    api = MagicMock()

    def fake_ga4(start, end, metrics=None, dimensions=None, site_name=None):
        if dimensions == ["date"]:
            return pd.DataFrame(
                [{"bounceRate": 0.144, "averageSessionDuration": 275.0}]
            )
        return pd.DataFrame(
            [
                {
                    "date": start,
                    "landingPage": "/moodmark/",
                    "sessions": 1000,
                    "activeUsers": 900,
                    "screenPageViews": 2000,
                    "ecommercePurchases": 10,
                    "purchaseRevenue": 50000,
                },
                {
                    "date": start,
                    "landingPage": "/moodmark/small/",
                    "sessions": 10,
                    "activeUsers": 10,
                    "screenPageViews": 10,
                    "ecommercePurchases": 0,
                    "purchaseRevenue": 0,
                },
                {
                    "date": start,
                    "landingPage": "/moodmarkgift/10128",
                    "sessions": 9999,
                    "activeUsers": 9999,
                    "screenPageViews": 9999,
                    "ecommercePurchases": 999,
                    "purchaseRevenue": 999999,
                },
            ]
        )

    api.get_ga4_data_custom_range.side_effect = fake_ga4
    metrics = _fetch_ec_purchase_landing(api, date(2026, 7, 9))

    assert metrics.sessions == 1010
    assert metrics.purchases == 10
    assert metrics.bounce_rate == 0.144
    assert metrics.avg_session_duration == 275.0
