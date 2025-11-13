#!/usr/bin/env python3
"""
直近7日間のサイト分析レポート生成スクリプト（購入完了のみ）
コンバージョン = 商品の注文（購入）完了
"""

import sys
import os
import json
import pandas as pd
from datetime import datetime, timedelta
from oauth_google_apis import OAuthGoogleAPIsIntegration

def analyze_7days_purchase_only():
    """直近7日間の詳細分析を実行（購入完了のみ）"""
    
    print("\n" + "=" * 70)
    print("  MOO-D MARK サイト分析レポート - 直近7日間")
    print("  https://isetan.mistore.jp/moodmark")
    print("  コンバージョン = 商品購入完了のみ")
    print("=" * 70)
    
    # API初期化
    api = OAuthGoogleAPIsIntegration()
    
    if not api.credentials:
        print("\n❌ 認証に失敗しました")
        return
    
    print("\n📊 データ取得中...\n")
    
    # 1. 日別トレンドデータ（購入完了のみ）
    print("1️⃣  日別トレンド分析（購入完了）")
    print("-" * 70)
    
    property_id = "316302380"
    
    daily_data = api.get_ga4_data(
        date_range_days=7,
        metrics=['sessions', 'activeUsers', 'screenPageViews', 'bounceRate', 
                'averageSessionDuration', 'ecommercePurchases', 'purchaseRevenue'],
        dimensions=['date', 'landingPage'],
        property_id=property_id
    )
    
    if not daily_data.empty:
        # moodmarkでランディングしたセッションのみ（moodmarkgiftを除外）
        moodmark_data = daily_data[
            (daily_data['landingPage'].str.contains('/moodmark', na=False)) & 
            (~daily_data['landingPage'].str.contains('/moodmarkgift/', na=False))
        ]
        
        if not moodmark_data.empty:
            daily_data = moodmark_data.groupby('date').agg({
                'sessions': 'sum',
                'activeUsers': 'sum',
                'screenPageViews': 'sum',
                'bounceRate': 'mean',
                'averageSessionDuration': 'mean',
                'ecommercePurchases': 'sum',
                'purchaseRevenue': 'sum'
            }).reset_index()
            
            daily_data = daily_data.sort_values('date')
            
            # 購入完了率（CVR）を計算
            daily_data['purchase_cvr'] = (daily_data['ecommercePurchases'] / daily_data['sessions'] * 100).round(2)
        else:
            print("⚠️ moodmarkのデータが見つかりませんでした")
            daily_data = pd.DataFrame()
    else:
        daily_data = pd.DataFrame()
    
    if not daily_data.empty:
        print(daily_data.to_string(index=False))
        
        # 合計値
        print("\n📈 7日間の合計:")
        print(f"   総セッション数: {daily_data['sessions'].sum():,.0f}")
        print(f"   アクティブユーザー数: {daily_data['activeUsers'].sum():,.0f}")
        print(f"   総ページビュー数: {daily_data['screenPageViews'].sum():,.0f}")
        print(f"   **総購入数（注文完了）: {daily_data['ecommercePurchases'].sum():,.0f}**")
        print(f"   **総購入額: ¥{daily_data['purchaseRevenue'].sum():,.0f}**")
        
        # 平均値
        print(f"\n📊 7日間の平均:")
        print(f"   平均直帰率: {daily_data['bounceRate'].mean():.1%}")
        print(f"   平均セッション時間: {daily_data['averageSessionDuration'].mean():.0f}秒")
        print(f"   **購入完了率（CVR）: {daily_data['purchase_cvr'].mean():.2f}%**")
        print(f"   **平均注文単価: ¥{(daily_data['purchaseRevenue'].sum() / daily_data['ecommercePurchases'].sum()):,.0f}**")
    
    # 2. デバイス別分析（購入完了）
    print("\n\n2️⃣  デバイス別分析（購入完了）")
    print("-" * 70)
    
    device_data = api.get_ga4_data(
        date_range_days=7,
        metrics=['sessions', 'activeUsers', 'bounceRate', 'ecommercePurchases', 'purchaseRevenue'],
        dimensions=['deviceCategory', 'landingPage'],
        property_id=property_id
    )
    
    if not device_data.empty:
        # moodmarkでランディングしたセッションのみ
        moodmark_device_data = device_data[
            (device_data['landingPage'].str.contains('/moodmark', na=False)) & 
            (~device_data['landingPage'].str.contains('/moodmarkgift/', na=False))
        ]
        
        if not moodmark_device_data.empty:
            device_summary = moodmark_device_data.groupby('deviceCategory').agg({
                'sessions': 'sum',
                'activeUsers': 'sum',
                'bounceRate': 'mean',
                'ecommercePurchases': 'sum',
                'purchaseRevenue': 'sum'
            }).reset_index()
        
        device_summary['purchase_cvr'] = (device_summary['ecommercePurchases'] / device_summary['sessions'] * 100).round(2)
        device_summary['session_share'] = (device_summary['sessions'] / device_summary['sessions'].sum() * 100).round(1)
        device_summary['avg_order_value'] = (device_summary['purchaseRevenue'] / device_summary['ecommercePurchases']).round(0)
        
        print(device_summary.to_string(index=False))
        
        print("\n💡 デバイス別インサイト:")
        for _, row in device_summary.iterrows():
            print(f"\n{row['deviceCategory']}:")
            print(f"  購入完了数: {row['ecommercePurchases']:,.0f}")
            print(f"  購入完了率: {row['purchase_cvr']:.2f}%")
            print(f"  平均注文単価: ¥{row['avg_order_value']:,.0f}")
    
    # 3. チャネル別分析（購入完了）
    print("\n\n3️⃣  チャネル別分析（購入完了）")
    print("-" * 70)
    
    channel_data = api.get_ga4_data(
        date_range_days=7,
        metrics=['sessions', 'activeUsers', 'ecommercePurchases', 'purchaseRevenue'],
        dimensions=['sessionDefaultChannelGrouping', 'landingPage'],
        property_id=property_id
    )
    
    if not channel_data.empty:
        # moodmarkでランディングしたセッションのみ
        moodmark_channel_data = channel_data[
            (channel_data['landingPage'].str.contains('/moodmark', na=False)) & 
            (~channel_data['landingPage'].str.contains('/moodmarkgift/', na=False))
        ]
        
        if not moodmark_channel_data.empty:
            channel_summary = moodmark_channel_data.groupby('sessionDefaultChannelGrouping').agg({
                'sessions': 'sum',
                'activeUsers': 'sum',
                'ecommercePurchases': 'sum',
                'purchaseRevenue': 'sum'
            }).reset_index()
        
        channel_summary['purchase_cvr'] = (channel_summary['ecommercePurchases'] / channel_summary['sessions'] * 100).round(2)
        channel_summary['avg_order_value'] = (channel_summary['purchaseRevenue'] / channel_summary['ecommercePurchases']).round(0)
        channel_summary = channel_summary.sort_values('ecommercePurchases', ascending=False)
        
        print(channel_summary.to_string(index=False))
        
        print("\n💡 チャネル別パフォーマンス:")
        for idx, row in channel_summary.head(5).iterrows():
            print(f"\n{row['sessionDefaultChannelGrouping']}:")
            print(f"  購入数: {row['ecommercePurchases']:,.0f}")
            print(f"  購入完了率: {row['purchase_cvr']:.2f}%")
            print(f"  購入額: ¥{row['purchaseRevenue']:,.0f}")
    
    # 4. 人気ページ分析
    print("\n\n4️⃣  人気ページ TOP10")
    print("-" * 70)
    
    page_data = api.get_ga4_data(
        date_range_days=7,
        metrics=['screenPageViews', 'sessions', 'bounceRate'],
        dimensions=['pagePath']
    )
    
    if not page_data.empty:
        page_summary = page_data.groupby('pagePath').agg({
            'screenPageViews': 'sum',
            'sessions': 'sum',
            'bounceRate': 'mean'
        }).reset_index()
        
        page_summary = page_summary.sort_values('screenPageViews', ascending=False).head(10)
        page_summary['bounceRate'] = page_summary['bounceRate'].apply(lambda x: f"{x:.1%}")
        
        print(page_summary.to_string(index=False))
    
    # 5. 時間帯別アクセス・購入分析
    print("\n\n5️⃣  時間帯別アクセス・購入分析")
    print("-" * 70)
    
    hourly_data = api.get_ga4_data(
        date_range_days=7,
        metrics=['sessions', 'totalUsers', 'ecommercePurchases'],
        dimensions=['dateHour']
    )
    
    if not hourly_data.empty:
        # 時間を抽出
        hourly_data['hour'] = hourly_data['dateHour'].astype(str).str[-2:].astype(int)
        
        hourly_summary = hourly_data.groupby('hour').agg({
            'sessions': 'sum',
            'totalUsers': 'sum',
            'ecommercePurchases': 'sum'
        }).reset_index()
        
        hourly_summary['purchase_cvr'] = (hourly_summary['ecommercePurchases'] / hourly_summary['sessions'] * 100).round(2)
        hourly_summary = hourly_summary.sort_values('ecommercePurchases', ascending=False).head(10)
        
        print("購入が多い時間帯 TOP10:")
        print(hourly_summary.to_string(index=False))
    
    # 6. 購入分析詳細
    print("\n\n6️⃣  購入分析詳細")
    print("-" * 70)
    
    if not daily_data.empty:
        total_sessions = daily_data['sessions'].sum()
        total_purchases = daily_data['ecommercePurchases'].sum()
        total_revenue = daily_data['purchaseRevenue'].sum()
        purchase_cvr = (total_purchases / total_sessions * 100)
        avg_order_value = total_revenue / total_purchases if total_purchases > 0 else 0
        
        print(f"📊 購入完了の全体サマリー:")
        print(f"  総セッション数: {total_sessions:,.0f}")
        print(f"  総購入完了数: {total_purchases:,.0f}")
        print(f"  **購入完了率（CVR）: {purchase_cvr:.2f}%**")
        print(f"  総購入額: ¥{total_revenue:,.0f}")
        print(f"  平均注文単価（AOV）: ¥{avg_order_value:,.0f}")
        
        # デバイス別購入完了率
        if not device_data.empty:
            print("\n📱 デバイス別購入完了率:")
            device_conv = device_data.groupby('deviceCategory').agg({
                'sessions': 'sum',
                'ecommercePurchases': 'sum'
            }).reset_index()
            device_conv['cvr'] = (device_conv['ecommercePurchases'] / device_conv['sessions'] * 100).round(2)
            print(device_conv[['deviceCategory', 'ecommercePurchases', 'cvr']].to_string(index=False))
        
        # チャネル別購入完了率
        if not channel_data.empty:
            print("\n🔍 チャネル別購入完了率 TOP5:")
            channel_conv = channel_data.groupby('sessionDefaultChannelGrouping').agg({
                'sessions': 'sum',
                'ecommercePurchases': 'sum'
            }).reset_index()
            channel_conv['cvr'] = (channel_conv['ecommercePurchases'] / channel_conv['sessions'] * 100).round(2)
            channel_conv = channel_conv.sort_values('ecommercePurchases', ascending=False).head(5)
            print(channel_conv[['sessionDefaultChannelGrouping', 'ecommercePurchases', 'cvr']].to_string(index=False))
    
    # 7. 分析サマリーと推奨事項
    print("\n\n7️⃣  分析サマリーと推奨事項")
    print("-" * 70)
    
    recommendations = []
    
    if not daily_data.empty:
        avg_purchase_cvr = daily_data['purchase_cvr'].mean()
        avg_order_value = daily_data['purchaseRevenue'].sum() / daily_data['ecommercePurchases'].sum()
        
        print(f"\n✅ 購入パフォーマンス:")
        print(f"   • 購入完了率（CVR）: {avg_purchase_cvr:.2f}%")
        print(f"   • 平均注文単価（AOV）: ¥{avg_order_value:,.0f}")
        
        if avg_purchase_cvr > 5:
            recommendations.append("購入完了率が5%以上と優秀です。現在の施策を継続してください。")
        elif avg_purchase_cvr > 2:
            recommendations.append("購入完了率は標準的です。カート離脱率の改善を検討してください。")
        else:
            recommendations.append("購入完了率が低いです。購入フロー全体の見直しが必要です。")
        
        if avg_order_value > 8000:
            recommendations.append("平均注文単価が高いです。アップセル・クロスセル施策が効果的に機能しています。")
        elif avg_order_value > 5000:
            recommendations.append("平均注文単価は標準的です。関連商品レコメンドの強化を検討してください。")
        else:
            recommendations.append("平均注文単価が低めです。セット商品やまとめ買い促進施策を強化してください。")
    
    if not device_data.empty:
        mobile_purchases = device_summary[device_summary['deviceCategory'] == 'mobile']['ecommercePurchases'].sum()
        desktop_purchases = device_summary[device_summary['deviceCategory'] == 'desktop']['ecommercePurchases'].sum()
        
        mobile_cvr = device_summary[device_summary['deviceCategory'] == 'mobile']['purchase_cvr'].values[0] if len(device_summary[device_summary['deviceCategory'] == 'mobile']) > 0 else 0
        desktop_cvr = device_summary[device_summary['deviceCategory'] == 'desktop']['purchase_cvr'].values[0] if len(device_summary[device_summary['deviceCategory'] == 'desktop']) > 0 else 0
        
        print(f"\n📱 デバイス別購入:")
        print(f"   • モバイル購入完了率: {mobile_cvr:.2f}%")
        print(f"   • デスクトップ購入完了率: {desktop_cvr:.2f}%")
        
        if desktop_cvr > mobile_cvr * 1.5:
            recommendations.append("デスクトップの購入完了率が高いです。モバイルの購入フロー最適化で売上増加が期待できます。")
        
        if mobile_purchases > desktop_purchases * 5:
            recommendations.append("モバイル購入が大多数を占めています。モバイル決済オプションの充実を優先してください。")
    
    if recommendations:
        print(f"\n💡 推奨事項:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
    
    # レポート保存
    print("\n\n8️⃣  レポート保存")
    print("-" * 70)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # CSV保存
    os.makedirs('data/processed', exist_ok=True)
    
    if not daily_data.empty:
        daily_data.to_csv(f'data/processed/daily_trend_purchase_7days_{timestamp}.csv', index=False, encoding='utf-8-sig')
        print(f"✅ 日別トレンド: data/processed/daily_trend_purchase_7days_{timestamp}.csv")
    
    if not device_data.empty:
        device_summary.to_csv(f'data/processed/device_analysis_purchase_7days_{timestamp}.csv', index=False, encoding='utf-8-sig')
        print(f"✅ デバイス別分析: data/processed/device_analysis_purchase_7days_{timestamp}.csv")
    
    if not channel_data.empty:
        channel_summary.to_csv(f'data/processed/channel_analysis_purchase_7days_{timestamp}.csv', index=False, encoding='utf-8-sig')
        print(f"✅ チャネル別分析: data/processed/channel_analysis_purchase_7days_{timestamp}.csv")
    
    # JSON形式でも保存
    report = {
        'report_date': datetime.now().isoformat(),
        'period': '直近7日間',
        'conversion_definition': '商品の注文（購入）完了のみ',
        'site_url': 'https://isetan.mistore.jp/moodmark',
        'summary': {
            'total_sessions': int(daily_data['sessions'].sum()) if not daily_data.empty else 0,
            'total_users': int(daily_data['totalUsers'].sum()) if not daily_data.empty else 0,
            'total_pageviews': int(daily_data['screenPageViews'].sum()) if not daily_data.empty else 0,
            'total_purchases': int(daily_data['ecommercePurchases'].sum()) if not daily_data.empty else 0,
            'total_revenue': float(daily_data['purchaseRevenue'].sum()) if not daily_data.empty else 0,
            'avg_bounce_rate': float(daily_data['bounceRate'].mean()) if not daily_data.empty else 0,
            'avg_session_duration': float(daily_data['averageSessionDuration'].mean()) if not daily_data.empty else 0,
            'purchase_cvr': float((daily_data['ecommercePurchases'].sum() / daily_data['sessions'].sum() * 100)) if not daily_data.empty else 0,
            'avg_order_value': float(daily_data['purchaseRevenue'].sum() / daily_data['ecommercePurchases'].sum()) if not daily_data.empty and daily_data['ecommercePurchases'].sum() > 0 else 0
        },
        'recommendations': recommendations
    }
    
    report_file = f'data/processed/analysis_report_purchase_7days_{timestamp}.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 統合レポート: {report_file}")
    
    print("\n" + "=" * 70)
    print("  分析完了！")
    print("=" * 70 + "\n")
    
    return report

if __name__ == "__main__":
    analyze_7days_purchase_only()

