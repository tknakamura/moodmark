#!/usr/bin/env python3
"""
MOO:D MARK GIFT（コンテンツSEOメディア）の直近7日間分析レポート生成スクリプト
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

def analyze_moodmarkgift_7days():
    """moodmarkgiftサイトの直近7日間の詳細分析を実行"""
    
    print("\n" + "=" * 70)
    print("  MOO:D MARK GIFT サイト分析レポート - 直近7日間")
    print("  https://isetan.mistore.jp/moodmarkgift/")
    print("  コンテンツSEOメディア")
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
        metrics=['sessions', 'activeUsers', 'engagementRate', 'newUsers'],
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
        # SEOメディアでランディングしたセッション
        gift_session_data = session_data[
            session_data['landingPage'].str.contains('/moodmarkgift/', na=False)
        ]
        
        # SEOメディアのPV
        gift_pv_data = pv_data[
            pv_data['pagePath'].str.contains('/moodmarkgift/', na=False)
        ]
        
        if not gift_session_data.empty and not gift_pv_data.empty:
            # セッション・ユーザー集計
            session_summary = gift_session_data.groupby('date').agg({
                'sessions': 'sum',
                'activeUsers': 'sum',
                'engagementRate': 'mean',
                'newUsers': 'sum'
            }).reset_index()
            
            # PV集計
            pv_summary = gift_pv_data.groupby('date').agg({
                'screenPageViews': 'sum'
            }).reset_index()
            
            # マージ
            daily_summary = session_summary.merge(pv_summary, on='date', how='left')
            daily_summary['screenPageViews'] = daily_summary['screenPageViews'].fillna(0)
            daily_summary = daily_summary.sort_values('date')
            
            print(daily_summary.to_string(index=False))
            
            # 合計値
            print("\n📈 7日間の合計:")
            print(f"   総セッション数: {daily_summary['sessions'].sum():,.0f}")
            print(f"   アクティブユーザー数: {daily_summary['activeUsers'].sum():,.0f}")
            print(f"   総ページビュー数: {daily_summary['screenPageViews'].sum():,.0f}")
            print(f"   新規ユーザー数: {daily_summary['newUsers'].sum():,.0f}")
            
            # 平均値
            print(f"\n📊 7日間の平均:")
            print(f"   平均エンゲージメント率: {daily_summary['engagementRate'].mean():.1%}")
            print(f"   新規ユーザー比率: {(daily_summary['newUsers'].sum() / daily_summary['activeUsers'].sum() * 100):.1f}%")
            print(f"   PV/セッション: {daily_summary['screenPageViews'].sum() / daily_summary['sessions'].sum():.2f}")
        else:
            print("⚠️ moodmarkgiftのデータが見つかりませんでした")
            daily_summary = pd.DataFrame()
    else:
        daily_summary = pd.DataFrame()
    
    # 2. デバイス別分析
    print("\n\n2️⃣  デバイス別分析")
    print("-" * 70)
    
    device_session_data = api.get_ga4_data(
        date_range_days=7,
        metrics=['sessions', 'activeUsers', 'engagementRate'],
        dimensions=['deviceCategory', 'landingPage'],
        property_id=property_id
    )
    
    if not device_session_data.empty:
        gift_device_session = device_session_data[
            device_session_data['landingPage'].str.contains('/moodmarkgift/', na=False)
        ]
        
        if not gift_device_session.empty:
            device_summary = gift_device_session.groupby('deviceCategory').agg({
                'sessions': 'sum',
                'activeUsers': 'sum',
                'engagementRate': 'mean'
            }).reset_index()
            
            device_summary['session_share'] = (device_summary['sessions'] / device_summary['sessions'].sum() * 100).round(1)
            device_summary = device_summary.sort_values('sessions', ascending=False)
            
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
        metrics=['sessions', 'activeUsers', 'engagementRate', 'newUsers'],
        dimensions=['sessionDefaultChannelGrouping', 'landingPage'],
        property_id=property_id
    )
    
    if not channel_data.empty:
        gift_channel_data = channel_data[
            channel_data['landingPage'].str.contains('/moodmarkgift/', na=False)
        ]
        
        if not gift_channel_data.empty:
            channel_summary = gift_channel_data.groupby('sessionDefaultChannelGrouping').agg({
                'sessions': 'sum',
                'activeUsers': 'sum',
                'engagementRate': 'mean',
                'newUsers': 'sum'
            }).reset_index()
            
            channel_summary['session_share'] = (channel_summary['sessions'] / channel_summary['sessions'].sum() * 100).round(1)
            channel_summary = channel_summary.sort_values('sessions', ascending=False)
            
            print(channel_summary.to_string(index=False))
        else:
            channel_summary = pd.DataFrame()
    else:
        channel_summary = pd.DataFrame()
    
    # 4. 人気コンテンツ分析（pagePathベース）
    print("\n\n4️⃣  人気コンテンツ TOP20（記事・ページ）")
    print("-" * 70)
    
    page_data = api.get_ga4_data(
        date_range_days=7,
        metrics=['screenPageViews', 'sessions'],
        dimensions=['pagePath', 'pageTitle'],
        property_id=property_id
    )
    
    if not page_data.empty:
        gift_page_data = page_data[
            page_data['pagePath'].str.contains('/moodmarkgift/', na=False)
        ]
        
        if not gift_page_data.empty:
            page_summary = gift_page_data.groupby(['pagePath', 'pageTitle']).agg({
                'screenPageViews': 'sum',
                'sessions': 'sum'
            }).reset_index()
            
            page_summary = page_summary.sort_values('screenPageViews', ascending=False).head(20)
            
            for idx, row in page_summary.iterrows():
                print(f"\n{idx+1}. {row['pageTitle']}")
                print(f"   URL: {row['pagePath']}")
                print(f"   PV: {row['screenPageViews']:,.0f} | セッション: {row['sessions']:,.0f}")
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
        gift_hourly_data = hourly_data[
            hourly_data['landingPage'].str.contains('/moodmarkgift/', na=False)
        ].copy()
        
        if not gift_hourly_data.empty:
            gift_hourly_data['hour'] = gift_hourly_data['dateHour'].astype(str).str[-2:].astype(int)
            
            hourly_summary = gift_hourly_data.groupby('hour').agg({
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
    
    # 6. 全サイト共通指標
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
    
    # 7. SEOメディアとしての評価
    print("\n\n7️⃣  SEOメディアとしてのパフォーマンス評価")
    print("-" * 70)
    
    recommendations = []
    
    if not daily_summary.empty:
        total_sessions = daily_summary['sessions'].sum()
        new_users = daily_summary['newUsers'].sum()
        active_users = daily_summary['activeUsers'].sum()
        new_user_rate = (new_users / active_users * 100)
        
        print(f"\n📊 基本指標:")
        print(f"   • 総セッション数: {total_sessions:,.0f}")
        print(f"   • 新規ユーザー率: {new_user_rate:.1f}%")
        
        if new_user_rate > 70:
            print(f"\n✅ 新規ユーザー獲得が良好です（{new_user_rate:.1f}%）")
            recommendations.append("新規ユーザー獲得が順調です。既存ユーザーのリピート施策も検討しましょう。")
    
    if not channel_summary.empty:
        organic_sessions = channel_summary[channel_summary['sessionDefaultChannelGrouping'] == 'Organic Search']['sessions'].sum()
        total_channel_sessions = channel_summary['sessions'].sum()
        organic_rate = (organic_sessions / total_channel_sessions * 100)
        
        print(f"\n🔍 流入元分析:")
        print(f"   • 自然検索比率: {organic_rate:.1f}%")
        
        if organic_rate > 70:
            print(f"✅ SEOメディアとして優秀です（自然検索{organic_rate:.1f}%）")
            recommendations.append("SEO対策が効果的です。引き続き質の高いコンテンツ作成を継続してください。")
    
    if not device_summary.empty:
        mobile_sessions = device_summary[device_summary['deviceCategory'] == 'mobile']['sessions'].sum()
        total_device_sessions = device_summary['sessions'].sum()
        mobile_rate = (mobile_sessions / total_device_sessions * 100)
        
        print(f"\n📱 デバイス構成:")
        print(f"   • モバイル比率: {mobile_rate:.1f}%")
        
        if mobile_rate > 70:
            recommendations.append("モバイル読者が多いため、モバイルファーストのコンテンツ設計を継続してください。")
    
    if recommendations:
        print(f"\n\n💡 推奨事項:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
    
    # レポート保存
    print("\n\n8️⃣  レポート保存")
    print("-" * 70)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    os.makedirs('data/processed', exist_ok=True)
    
    if not daily_summary.empty:
        daily_summary.to_csv(f'data/processed/moodmarkgift_daily_trend_7days_{timestamp}.csv', index=False, encoding='utf-8-sig')
        print(f"✅ 日別トレンド: data/processed/moodmarkgift_daily_trend_7days_{timestamp}.csv")
    
    if not device_summary.empty:
        device_summary.to_csv(f'data/processed/moodmarkgift_device_analysis_7days_{timestamp}.csv', index=False, encoding='utf-8-sig')
        print(f"✅ デバイス別分析: data/processed/moodmarkgift_device_analysis_7days_{timestamp}.csv")
    
    if not channel_summary.empty:
        channel_summary.to_csv(f'data/processed/moodmarkgift_channel_analysis_7days_{timestamp}.csv', index=False, encoding='utf-8-sig')
        print(f"✅ チャネル別分析: data/processed/moodmarkgift_channel_analysis_7days_{timestamp}.csv")
    
    if not page_summary.empty:
        page_summary.to_csv(f'data/processed/moodmarkgift_top_pages_7days_{timestamp}.csv', index=False, encoding='utf-8-sig')
        print(f"✅ 人気コンテンツ: data/processed/moodmarkgift_top_pages_7days_{timestamp}.csv")
    
    # JSON形式でも保存
    report = {
        'report_date': datetime.now().isoformat(),
        'period': '直近7日間',
        'site_url': 'https://isetan.mistore.jp/moodmarkgift/',
        'site_type': 'コンテンツSEOメディア',
        'summary': {
            'total_sessions': int(daily_summary['sessions'].sum()) if not daily_summary.empty else 0,
            'active_users': int(daily_summary['activeUsers'].sum()) if not daily_summary.empty else 0,
            'total_pageviews': int(daily_summary['screenPageViews'].sum()) if not daily_summary.empty else 0,
            'new_users': int(daily_summary['newUsers'].sum()) if not daily_summary.empty else 0,
            'avg_engagement_rate': float(daily_summary['engagementRate'].mean()) if not daily_summary.empty else 0,
            'new_user_rate': float((daily_summary['newUsers'].sum() / daily_summary['activeUsers'].sum() * 100)) if not daily_summary.empty else 0,
            'pages_per_session': float(daily_summary['screenPageViews'].sum() / daily_summary['sessions'].sum()) if not daily_summary.empty else 0
        },
        'recommendations': recommendations,
        'note': '直帰率とセッション時間は両サイトが同じドメイン内にあるため、セッション単位では正確に分離できません。'
    }
    
    report_file = f'data/processed/moodmarkgift_analysis_report_7days_{timestamp}.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 統合レポート: {report_file}")
    
    print("\n" + "=" * 70)
    print("  分析完了！")
    print("=" * 70 + "\n")
    
    return report

if __name__ == "__main__":
    analyze_moodmarkgift_7days()
