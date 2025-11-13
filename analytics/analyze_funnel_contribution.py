#!/usr/bin/env python3
"""
MOO-D MARK GIFT → MOO-D MARK ファネル貢献度分析
SEOメディアからECサイトへの送客・コンバージョン貢献を測定
"""

import sys
import os
import json
import pandas as pd
from datetime import datetime, timedelta
from oauth_google_apis import OAuthGoogleAPIsIntegration

def analyze_funnel_contribution():
    """ファネル貢献度の詳細分析"""
    
    print("\n" + "=" * 80)
    print("  MOO-D MARK GIFT → MOO-D MARK ファネル貢献度分析")
    print("  SEOメディアからECサイトへの送客・コンバージョン分析")
    print("=" * 80)
    
    # API初期化
    api = OAuthGoogleAPIsIntegration()
    
    if not api.credentials:
        print("\n❌ 認証に失敗しました")
        return
    
    print("\n📊 データ取得中...\n")
    property_id = "316302380"
    
    # ===================================================================
    # 1. SEOメディア訪問後のECサイト訪問分析
    # ===================================================================
    print("1️⃣  SEOメディア→ECサイト 遷移分析")
    print("-" * 80)
    
    # ユーザーのページ遷移パターンを取得
    user_journey = api.get_ga4_data(
        date_range_days=7,
        metrics=['sessions', 'totalUsers', 'screenPageViews', 'conversions'],
        dimensions=['pagePath', 'sessionSourceMedium'],
        property_id=property_id
    )
    
    if not user_journey.empty:
        # moodmarkgift訪問ユーザーを特定
        gift_users = user_journey[user_journey['pagePath'].str.contains('/moodmarkgift/', na=False)]
        
        # その後のmoodmark訪問を確認
        ec_users = user_journey[
            (user_journey['pagePath'].str.contains('/moodmark/', na=False)) & 
            (~user_journey['pagePath'].str.contains('/moodmarkgift/', na=False))
        ]
        
        print(f"📖 SEOメディア訪問セッション: {gift_users['sessions'].sum():,.0f}")
        print(f"🛒 ECサイト訪問セッション: {ec_users['sessions'].sum():,.0f}")
        
        # リファラルを確認
        referral_from_gift = ec_users[ec_users['sessionSourceMedium'].str.contains('referral', na=False, case=False)]
        if not referral_from_gift.empty:
            print(f"🔗 SEOメディアからのリファラル: {referral_from_gift['sessions'].sum():,.0f}")
    
    # ===================================================================
    # 2. 流入元別のコンバージョン分析
    # ===================================================================
    print("\n\n2️⃣  流入元別コンバージョン分析")
    print("-" * 80)
    
    source_conversion = api.get_ga4_data(
        date_range_days=7,
        metrics=['sessions', 'conversions', 'totalUsers'],
        dimensions=['sessionSource', 'sessionMedium', 'pagePath'],
        property_id=property_id
    )
    
    if not source_conversion.empty:
        # ECサイトのコンバージョンのみ
        ec_conversions = source_conversion[
            (source_conversion['pagePath'].str.contains('/moodmark/', na=False)) & 
            (~source_conversion['pagePath'].str.contains('/moodmarkgift/', na=False))
        ]
        
        if not ec_conversions.empty:
            source_summary = ec_conversions.groupby(['sessionSource', 'sessionMedium']).agg({
                'sessions': 'sum',
                'conversions': 'sum',
                'totalUsers': 'sum'
            }).reset_index()
            
            source_summary['cvr'] = (source_summary['conversions'] / source_summary['sessions'] * 100).round(2)
            source_summary = source_summary.sort_values('conversions', ascending=False).head(10)
            
            print("\nECサイトでのコンバージョン上位流入元:")
            print(source_summary.to_string(index=False))
    
    # ===================================================================
    # 3. ランディングページ別の購買貢献度
    # ===================================================================
    print("\n\n3️⃣  ランディングページ別の購買貢献度")
    print("-" * 80)
    
    landing_conversion = api.get_ga4_data(
        date_range_days=7,
        metrics=['sessions', 'conversions', 'bounceRate'],
        dimensions=['landingPage', 'firstUserSource'],
        property_id=property_id
    )
    
    if not landing_conversion.empty:
        # SEOメディアがランディングページのセッション
        gift_landing = landing_conversion[
            landing_conversion['landingPage'].str.contains('/moodmarkgift/', na=False)
        ]
        
        if not gift_landing.empty:
            landing_summary = gift_landing.groupby('landingPage').agg({
                'sessions': 'sum',
                'conversions': 'sum',
                'bounceRate': 'mean'
            }).reset_index()
            
            landing_summary['cvr'] = (landing_summary['conversions'] / landing_summary['sessions'] * 100).round(2)
            landing_summary = landing_summary.sort_values('sessions', ascending=False).head(15)
            
            print("\nSEOメディア記事別の送客パフォーマンス:")
            for idx, row in landing_summary.iterrows():
                article_name = row['landingPage'].split('/')[-1] if row['landingPage'] else 'トップ'
                print(f"\n記事ID: {article_name}")
                print(f"  セッション: {row['sessions']:,.0f} | CV: {row['conversions']:,.0f} | CVR: {row['cvr']:.2f}% | 直帰率: {row['bounceRate']:.1%}")
    
    # ===================================================================
    # 4. 初回流入元別の長期的貢献分析
    # ===================================================================
    print("\n\n4️⃣  初回流入元別の長期的貢献度")
    print("-" * 80)
    
    first_user_analysis = api.get_ga4_data(
        date_range_days=7,
        metrics=['totalUsers', 'newUsers', 'conversions', 'sessions'],
        dimensions=['firstUserSource', 'firstUserMedium'],
        property_id=property_id
    )
    
    if not first_user_analysis.empty:
        first_user_summary = first_user_analysis.groupby(['firstUserSource', 'firstUserMedium']).agg({
            'totalUsers': 'sum',
            'newUsers': 'sum',
            'conversions': 'sum',
            'sessions': 'sum'
        }).reset_index()
        
        first_user_summary['conversion_per_user'] = (
            first_user_summary['conversions'] / first_user_summary['totalUsers']
        ).round(2)
        first_user_summary = first_user_summary.sort_values('conversions', ascending=False).head(10)
        
        print("\n初回流入元別のユーザー価値:")
        print(first_user_summary.to_string(index=False))
    
    # ===================================================================
    # 5. SEOメディア記事のEC送客力ランキング
    # ===================================================================
    print("\n\n5️⃣  SEOメディア記事のEC送客力ランキング")
    print("-" * 80)
    
    # ページパスでECサイトとSEOメディアの遷移を追跡
    page_transitions = api.get_ga4_data(
        date_range_days=7,
        metrics=['sessions', 'screenPageViews', 'conversions'],
        dimensions=['pagePath', 'pageTitle'],
        property_id=property_id
    )
    
    if not page_transitions.empty:
        # SEOメディアのページのみ
        gift_pages = page_transitions[
            page_transitions['pagePath'].str.contains('/moodmarkgift/', na=False)
        ]
        
        if not gift_pages.empty:
            gift_page_summary = gift_pages.groupby(['pagePath', 'pageTitle']).agg({
                'sessions': 'sum',
                'screenPageViews': 'sum',
                'conversions': 'sum'
            }).reset_index()
            
            gift_page_summary['conversion_rate'] = (
                gift_page_summary['conversions'] / gift_page_summary['sessions'] * 100
            ).round(2)
            
            # EC送客力が高い順にソート（コンバージョン数）
            gift_page_summary = gift_page_summary.sort_values('conversions', ascending=False).head(20)
            
            print("\nEC送客力が高いSEOメディア記事 TOP20:")
            print("（コンバージョン数でランキング）\n")
            
            for idx, row in gift_page_summary.iterrows():
                print(f"{idx+1}. {row['pageTitle']}")
                print(f"   セッション: {row['sessions']:,.0f} | PV: {row['screenPageViews']:,.0f}")
                print(f"   コンバージョン: {row['conversions']:,.0f} | CVR: {row['conversion_rate']:.2f}%")
                print()
    
    # ===================================================================
    # 6. カスタマージャーニー分析
    # ===================================================================
    print("\n\n6️⃣  カスタマージャーニーパターン分析")
    print("-" * 80)
    
    # セッション内のページ遷移を分析
    journey_data = api.get_ga4_data(
        date_range_days=7,
        metrics=['sessions', 'conversions', 'engagementRate'],
        dimensions=['pagePath', 'sessionDefaultChannelGrouping'],
        property_id=property_id
    )
    
    if not journey_data.empty:
        # パターン1: SEOメディアから始まるジャーニー
        seo_journey = journey_data[
            journey_data['sessionDefaultChannelGrouping'] == 'Organic Search'
        ]
        
        gift_seo = seo_journey[seo_journey['pagePath'].str.contains('/moodmarkgift/', na=False)]
        ec_seo = seo_journey[
            (seo_journey['pagePath'].str.contains('/moodmark/', na=False)) &
            (~seo_journey['pagePath'].str.contains('/moodmarkgift/', na=False))
        ]
        
        print("\n自然検索経由のジャーニー:")
        print(f"  SEOメディア訪問: {gift_seo['sessions'].sum():,.0f} セッション")
        print(f"  ECサイト訪問: {ec_seo['sessions'].sum():,.0f} セッション")
        print(f"  SEOメディアCV: {gift_seo['conversions'].sum():,.0f}")
        print(f"  ECサイトCV: {ec_seo['conversions'].sum():,.0f}")
    
    # ===================================================================
    # 7. SEOメディアの貢献度サマリー
    # ===================================================================
    print("\n\n7️⃣  SEOメディアの貢献度サマリー")
    print("-" * 80)
    
    # 全体のデータから計算
    all_data = api.get_ga4_data(
        date_range_days=7,
        metrics=['sessions', 'totalUsers', 'conversions', 'screenPageViews'],
        dimensions=['pagePath'],
        property_id=property_id
    )
    
    if not all_data.empty:
        # SEOメディアのデータ
        gift_data = all_data[all_data['pagePath'].str.contains('/moodmarkgift/', na=False)]
        
        # ECサイトのデータ
        ec_data = all_data[
            (all_data['pagePath'].str.contains('/moodmark/', na=False)) &
            (~all_data['pagePath'].str.contains('/moodmarkgift/', na=False))
        ]
        
        # 全体
        total_sessions = all_data['sessions'].sum()
        total_conversions = all_data['conversions'].sum()
        
        # SEOメディア
        gift_sessions = gift_data['sessions'].sum()
        gift_conversions = gift_data['conversions'].sum()
        gift_users = gift_data['totalUsers'].sum()
        
        # ECサイト
        ec_sessions = ec_data['sessions'].sum()
        ec_conversions = ec_data['conversions'].sum()
        ec_users = ec_data['totalUsers'].sum()
        
        print("\n📊 全体サマリー:")
        print(f"  総セッション数: {total_sessions:,.0f}")
        print(f"  総コンバージョン数: {total_conversions:,.0f}")
        
        print("\n📖 SEOメディア（GIFT）:")
        print(f"  セッション数: {gift_sessions:,.0f} ({gift_sessions/total_sessions*100:.1f}%)")
        print(f"  ユーザー数: {gift_users:,.0f}")
        print(f"  コンバージョン数: {gift_conversions:,.0f} ({gift_conversions/total_conversions*100:.1f}%)")
        print(f"  CVR: {(gift_conversions/gift_sessions*100):.2f}%")
        
        print("\n🛒 ECサイト（MARK）:")
        print(f"  セッション数: {ec_sessions:,.0f} ({ec_sessions/total_sessions*100:.1f}%)")
        print(f"  ユーザー数: {ec_users:,.0f}")
        print(f"  コンバージョン数: {ec_conversions:,.0f} ({ec_conversions/total_conversions*100:.1f}%)")
        print(f"  CVR: {(ec_conversions/ec_sessions*100):.2f}%")
        
        # ファネル効率
        print("\n🎯 ファネル分析:")
        if gift_sessions > 0:
            potential_ec_visits = gift_sessions * 0.1  # 仮定: 10%が遷移すると仮定
            print(f"  SEOメディア訪問者のEC遷移率（推定）: 10%")
            print(f"  潜在的EC訪問数: {potential_ec_visits:,.0f}")
            print(f"  → 改善機会: SEOメディアからECへの導線強化で売上増加可能")
    
    # ===================================================================
    # 8. 改善推奨事項
    # ===================================================================
    print("\n\n8️⃣  ファネル改善のための推奨事項")
    print("-" * 80)
    
    recommendations = []
    
    if gift_sessions > 0 and ec_sessions > 0:
        gift_ratio = gift_sessions / total_sessions
        gift_cv_ratio = gift_conversions / total_conversions if total_conversions > 0 else 0
        
        print("\n💡 分析結果に基づく推奨事項:\n")
        
        # 1. SEOメディアの直接コンバージョンが低い場合
        if gift_cv_ratio < 0.1:
            rec = "SEOメディア記事内にEC商品リンクを明確に配置し、直接購入への導線を強化"
            recommendations.append(rec)
            print(f"1. {rec}")
        
        # 2. セッション数は多いがCVが少ない
        if gift_sessions > ec_sessions * 0.3 and gift_cv_ratio < 0.2:
            rec = "記事末尾に「この記事で紹介した商品はこちら」セクションを追加"
            recommendations.append(rec)
            print(f"2. {rec}")
        
        # 3. 遷移率改善
        rec = "SEOメディアトップページからECサイトへの導線を強化"
        recommendations.append(rec)
        print(f"3. {rec}")
        
        # 4. トラッキング強化
        rec = "クロスドメイントラッキングを実装し、正確なファネル測定を実現"
        recommendations.append(rec)
        print(f"4. {rec}")
        
        # 5. コンテンツ戦略
        rec = "EC売上データと連携し、売れ筋商品をSEOメディアで特集"
        recommendations.append(rec)
        print(f"5. {rec}")
        
        # 6. リターゲティング
        rec = "SEOメディア訪問者へのリターゲティング広告でEC送客を促進"
        recommendations.append(rec)
        print(f"6. {rec}")
    
    # ===================================================================
    # 9. レポート保存
    # ===================================================================
    print("\n\n9️⃣  ファネル分析レポート保存")
    print("-" * 80)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    os.makedirs('data/processed', exist_ok=True)
    
    # JSONレポート作成
    funnel_report = {
        'report_date': datetime.now().isoformat(),
        'period': '直近7日間',
        'analysis_type': 'ファネル貢献度分析',
        'summary': {
            'total_sessions': int(total_sessions) if 'total_sessions' in locals() else 0,
            'gift_sessions': int(gift_sessions) if 'gift_sessions' in locals() else 0,
            'ec_sessions': int(ec_sessions) if 'ec_sessions' in locals() else 0,
            'gift_conversions': int(gift_conversions) if 'gift_conversions' in locals() else 0,
            'ec_conversions': int(ec_conversions) if 'ec_conversions' in locals() else 0,
            'gift_session_share': float(gift_sessions/total_sessions*100) if 'gift_sessions' in locals() and total_sessions > 0 else 0,
            'gift_conversion_share': float(gift_conversions/total_conversions*100) if 'gift_conversions' in locals() and total_conversions > 0 else 0
        },
        'recommendations': recommendations
    }
    
    report_file = f'data/processed/funnel_analysis_report_{timestamp}.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(funnel_report, f, ensure_ascii=False, indent=2)
    
    print(f"✅ ファネル分析レポート: {report_file}")
    
    # CSVデータも保存
    if not gift_page_summary.empty:
        gift_page_summary.to_csv(
            f'data/processed/gift_article_performance_{timestamp}.csv',
            index=False,
            encoding='utf-8-sig'
        )
        print(f"✅ 記事別パフォーマンス: data/processed/gift_article_performance_{timestamp}.csv")
    
    print("\n" + "=" * 80)
    print("  ファネル貢献度分析完了！")
    print("=" * 80 + "\n")
    
    return funnel_report

if __name__ == "__main__":
    analyze_funnel_contribution()


