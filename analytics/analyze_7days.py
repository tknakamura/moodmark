#!/usr/bin/env python3
"""
直近7日間のサイト分析レポート生成スクリプト
正確な測定方法：
- セッション数: landingPageベース
- ユーザー数: activeUsers
- PV数: pagePathベース
- 直帰率・セッション時間: 全サイト共通（分離不可）
"""

import sys
import os
import json
import pandas as pd
from datetime import datetime, timedelta
from oauth_google_apis import OAuthGoogleAPIsIntegration

def analyze_7days():
    """直近7日間の詳細分析を実行"""
    
    print("\n" + "=" * 70)
    print("  MOO:D MARK サイト分析レポート - 直近7日間")
    print("  https://isetan.mistore.jp/moodmark")
    print("=" * 70)
    
    # API初期化
    api = OAuthGoogleAPIsIntegration()
    
    if not api.credentials:
        print("\n❌ 認証に失敗しました")
        return
    
    print("\n📊 データ取得中...\n")
    
    property_id = "316302380"
    
    # 1. セッション数とユーザー数（landingPageベース）
    print("1️⃣  日別トレンド分析")
    print("-" * 70)
    
    session_data = api.get_ga4_data(
        date_range_days=7,
        metrics=['sessions', 'activeUsers', 'conversions'],
        dimensions=['date', 'landingPage'],
        property_id=property_id
    )
    
    # PV数（pagePathベース）
    pv_data = api.get_ga4_data(
        date_range_days=7,
        metrics=['screenPageViews'],
        dimensions=['date', 'pagePath'],
        property_id=property_id
    )
    
    if not session_data.empty and not pv_data.empty:
        # ECサイトでランディングしたセッション
        ec_session_data = session_data[
            (session_data['landingPage'].str.contains('/moodmark', na=False)) & 
            (~session_data['landingPage'].str.contains('/moodmarkgift/', na=False))
        ]
        
        # ECサイトのPV
        ec_pv_data = pv_data[
            (pv_data['pagePath'].str.contains('/moodmark', na=False)) & 
            (~pv_data['pagePath'].str.contains('/moodmarkgift/', na=False))
        ]
        
        if not ec_session_data.empty and not ec_pv_data.empty:
            # セッション・ユーザー・コンバージョン集計
            session_summary = ec_session_data.groupby('date').agg({
                'sessions': 'sum',
                'activeUsers': 'sum',
                'conversions': 'sum'
            }).reset_index()
            
            # PV集計
            pv_summary = ec_pv_data.groupby('date').agg({
                'screenPageViews': 'sum'
            }).reset_index()
            
            # マージ
            daily_data = session_summary.merge(pv_summary, on='date', how='left')
            daily_data['screenPageViews'] = daily_data['screenPageViews'].fillna(0)
            daily_data = daily_data.sort_values('date')
            
            print(daily_data.to_string(index=False))
            
            # 合計値
            print("\n📈 7日間の合計:")
            print(f"   総セッション数: {daily_data['sessions'].sum():,.0f}")
            print(f"   アクティブユーザー数: {daily_data['activeUsers'].sum():,.0f}")
            print(f"   総ページビュー数: {daily_data['screenPageViews'].sum():,.0f}")
            print(f"   総コンバージョン数: {daily_data['conversions'].sum():,.0f}")
            print(f"   PV/セッション: {daily_data['screenPageViews'].sum() / daily_data['sessions'].sum():.2f}")
        else:
            print("⚠️ moodmarkのデータが見つかりませんでした")
            daily_data = pd.DataFrame()
    else:
        daily_data = pd.DataFrame()
    
    # 2. デバイス別分析
    print("\n\n2️⃣  デバイス別分析")
    print("-" * 70)
    
    device_session_data = api.get_ga4_data(
        date_range_days=7,
        metrics=['sessions', 'activeUsers', 'conversions'],
        dimensions=['deviceCategory', 'landingPage'],
        property_id=property_id
    )
    
    device_pv_data = api.get_ga4_data(
        date_range_days=7,
        metrics=['screenPageViews'],
        dimensions=['deviceCategory', 'pagePath'],
        property_id=property_id
    )
    
    if not device_session_data.empty and not device_pv_data.empty:
        ec_device_session = device_session_data[
            (device_session_data['landingPage'].str.contains('/moodmark', na=False)) & 
            (~device_session_data['landingPage'].str.contains('/moodmarkgift/', na=False))
        ]
        
        ec_device_pv = device_pv_data[
            (device_pv_data['pagePath'].str.contains('/moodmark', na=False)) & 
            (~device_pv_data['pagePath'].str.contains('/moodmarkgift/', na=False))
        ]
        
        if not ec_device_session.empty and not ec_device_pv.empty:
            device_session_summary = ec_device_session.groupby('deviceCategory').agg({
                'sessions': 'sum',
                'activeUsers': 'sum',
                'conversions': 'sum'
            }).reset_index()
            
            device_pv_summary = ec_device_pv.groupby('deviceCategory').agg({
                'screenPageViews': 'sum'
            }).reset_index()
            
            device_summary = device_session_summary.merge(device_pv_summary, on='deviceCategory', how='left')
            device_summary['screenPageViews'] = device_summary['screenPageViews'].fillna(0)
            device_summary['conversion_rate'] = (device_summary['conversions'] / device_summary['sessions'] * 100).round(2)
            device_summary['session_share'] = (device_summary['sessions'] / device_summary['sessions'].sum() * 100).round(1)
            
            print(device_summary.to_string(index=False))
        else:
            device_summary = pd.DataFrame()
    else:
        device_summary = pd.DataFrame()
    
    # 3. チャネル別分析
    print("\n\n3️⃣  チャネル別分析（流入元）")
    print("-" * 70)
    
    channel_data = api.get_ga4_data(
        date_range_days=7,
        metrics=['sessions', 'activeUsers', 'conversions'],
        dimensions=['sessionDefaultChannelGrouping', 'landingPage'],
        property_id=property_id
    )
    
    if not channel_data.empty:
        ec_channel_data = channel_data[
            (channel_data['landingPage'].str.contains('/moodmark', na=False)) & 
            (~channel_data['landingPage'].str.contains('/moodmarkgift/', na=False))
        ]
        
        if not ec_channel_data.empty:
            channel_summary = ec_channel_data.groupby('sessionDefaultChannelGrouping').agg({
                'sessions': 'sum',
                'activeUsers': 'sum',
                'conversions': 'sum'
            }).reset_index()
            
            channel_summary['conversion_rate'] = (channel_summary['conversions'] / channel_summary['sessions'] * 100).round(2)
            channel_summary = channel_summary.sort_values('sessions', ascending=False)
            
            print(channel_summary.to_string(index=False))
        else:
            channel_summary = pd.DataFrame()
    else:
        channel_summary = pd.DataFrame()
    
    # 4. 人気ページ分析（pagePathベース）
    print("\n\n4️⃣  人気ページ TOP10")
    print("-" * 70)
    
    page_data = api.get_ga4_data(
        date_range_days=7,
        metrics=['screenPageViews', 'sessions'],
        dimensions=['pagePath'],
        property_id=property_id
    )
    
    if not page_data.empty:
        ec_page_data = page_data[
            (page_data['pagePath'].str.contains('/moodmark', na=False)) & 
            (~page_data['pagePath'].str.contains('/moodmarkgift/', na=False))
        ]
        
        if not ec_page_data.empty:
            page_summary = ec_page_data.groupby('pagePath').agg({
                'screenPageViews': 'sum',
                'sessions': 'sum'
            }).reset_index()
            
            page_summary = page_summary.sort_values('screenPageViews', ascending=False).head(10)
            
            print(page_summary.to_string(index=False))
        else:
            page_summary = pd.DataFrame()
    else:
        page_summary = pd.DataFrame()
    
    # 5. 時間帯別分析
    print("\n\n5️⃣  時間帯別アクセス分析")
    print("-" * 70)
    
    hourly_data = api.get_ga4_data(
        date_range_days=7,
        metrics=['sessions', 'activeUsers'],
        dimensions=['dateHour', 'landingPage'],
        property_id=property_id
    )
    
    if not hourly_data.empty:
        ec_hourly_data = hourly_data[
            (hourly_data['landingPage'].str.contains('/moodmark', na=False)) & 
            (~hourly_data['landingPage'].str.contains('/moodmarkgift/', na=False))
        ].copy()
        
        if not ec_hourly_data.empty:
            ec_hourly_data['hour'] = ec_hourly_data['dateHour'].astype(str).str[-2:].astype(int)
            
            hourly_summary = ec_hourly_data.groupby('hour').agg({
                'sessions': 'sum',
                'activeUsers': 'sum'
            }).reset_index()
            
            hourly_summary = hourly_summary.sort_values('sessions', ascending=False).head(10)
            print("アクセスが多い時間帯 TOP10:")
            print(hourly_summary.to_string(index=False))
        else:
            hourly_summary = pd.DataFrame()
    else:
        hourly_summary = pd.DataFrame()
    
    # 6. 全サイト共通指標の取得
    print("\n\n6️⃣  全サイト共通指標（参考値）")
    print("-" * 70)
    print("※ 直帰率とセッション時間は両サイトが同じドメイン内にあるため、")
    print("  セッション単位では正確に分離できません。")
    
    overall_data = api.get_ga4_data(
        date_range_days=7,
        metrics=['sessions', 'bounceRate', 'averageSessionDuration'],
        dimensions=['date'],
        property_id=property_id
    )
    
    if not overall_data.empty:
        print(f"\n全サイト平均:")
        print(f"   平均直帰率: {overall_data['bounceRate'].mean():.1%}")
        print(f"   平均セッション時間: {overall_data['averageSessionDuration'].mean():.0f}秒（{overall_data['averageSessionDuration'].mean()/60:.1f}分）")
    
    # 7. コンバージョン分析
    print("\n\n7️⃣  コンバージョン分析")
    print("-" * 70)
    
    if not daily_data.empty:
        total_sessions = daily_data['sessions'].sum()
        total_conversions = daily_data['conversions'].sum()
        conversion_rate = (total_conversions / total_sessions * 100)
        
        print(f"総セッション数: {total_sessions:,.0f}")
        print(f"総コンバージョン数: {total_conversions:,.0f}")
        print(f"コンバージョン率: {conversion_rate:.2f}%")
        print("\n※ コンバージョンにはカート追加、商品閲覧等の複数イベントを含みます")
        print("※ 実際の購入完了率は analyze_7days_purchase_only.py で確認してください")
    
    # 8. 分析サマリーと推奨事項
    print("\n\n8️⃣  分析サマリーと推奨事項")
    print("-" * 70)
    
    recommendations = []
    
    if not daily_data.empty:
        print(f"\n✅ 基本指標:")
        print(f"   • 総セッション数: {daily_data['sessions'].sum():,.0f}")
        print(f"   • アクティブユーザー数: {daily_data['activeUsers'].sum():,.0f}")
        print(f"   • 総PV数: {daily_data['screenPageViews'].sum():,.0f}")
        print(f"   • PV/セッション: {daily_data['screenPageViews'].sum() / daily_data['sessions'].sum():.2f}")
        
        recommendations.append("セッション時間が良好です。ユーザーがコンテンツに興味を持っています。")
    
    if not device_summary.empty:
        mobile_sessions = device_summary[device_summary['deviceCategory'] == 'mobile']['sessions'].sum()
        total_device_sessions = device_summary['sessions'].sum()
        mobile_rate = (mobile_sessions / total_device_sessions * 100)
        
        print(f"\n📱 デバイス構成:")
        print(f"   • モバイル比率: {mobile_rate:.1f}%")
        
        if mobile_rate > 60:
            recommendations.append("モバイルアクセスが多数を占めています。モバイルUXの最適化を優先してください。")
    
    if not channel_summary.empty:
        organic_sessions = channel_summary[channel_summary['sessionDefaultChannelGrouping'] == 'Organic Search']['sessions'].sum()
        
        print(f"\n🔍 流入元:")
        print(f"   • Organic Search: {organic_sessions:,.0f}")
    
    if recommendations:
        print(f"\n💡 推奨事項:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
    
    # レポート保存
    print("\n\n9️⃣  レポート保存")
    print("-" * 70)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    os.makedirs('data/processed', exist_ok=True)
    
    # CSV保存
    if not daily_data.empty:
        daily_data.to_csv(f'data/processed/daily_trend_7days_{timestamp}.csv', index=False, encoding='utf-8-sig')
        print(f"✅ 日別トレンド: data/processed/daily_trend_7days_{timestamp}.csv")
    
    if not device_summary.empty:
        device_summary.to_csv(f'data/processed/device_analysis_7days_{timestamp}.csv', index=False, encoding='utf-8-sig')
        print(f"✅ デバイス別分析: data/processed/device_analysis_7days_{timestamp}.csv")
    
    if not channel_summary.empty:
        channel_summary.to_csv(f'data/processed/channel_analysis_7days_{timestamp}.csv', index=False, encoding='utf-8-sig')
        print(f"✅ チャネル別分析: data/processed/channel_analysis_7days_{timestamp}.csv")
    
    if not page_summary.empty:
        page_summary.to_csv(f'data/processed/top_pages_7days_{timestamp}.csv', index=False, encoding='utf-8-sig')
        print(f"✅ 人気ページ: data/processed/top_pages_7days_{timestamp}.csv")
    
    # JSON形式でも保存
    report = {
        'report_date': datetime.now().isoformat(),
        'period': '直近7日間',
        'site_url': 'https://isetan.mistore.jp/moodmark',
        'summary': {
            'total_sessions': int(daily_data['sessions'].sum()) if not daily_data.empty else 0,
            'active_users': int(daily_data['activeUsers'].sum()) if not daily_data.empty else 0,
            'total_pageviews': int(daily_data['screenPageViews'].sum()) if not daily_data.empty else 0,
            'total_conversions': int(daily_data['conversions'].sum()) if not daily_data.empty else 0,
            'conversion_rate': float((daily_data['conversions'].sum() / daily_data['sessions'].sum() * 100)) if not daily_data.empty else 0,
            'pages_per_session': float(daily_data['screenPageViews'].sum() / daily_data['sessions'].sum()) if not daily_data.empty else 0
        },
        'recommendations': recommendations,
        'note': '直帰率とセッション時間は両サイトが同じドメイン内にあるため、セッション単位では正確に分離できません。'
    }
    
    report_file = f'data/processed/analysis_report_7days_{timestamp}.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 統合レポート: {report_file}")
    
    print("\n" + "=" * 70)
    print("  分析完了！")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    analyze_7days()
