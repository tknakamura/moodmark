#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV to HTML Converter Dashboard
結婚祝いお菓子記事のCSVをHTMLに変換するダッシュボード
"""

import streamlit as st
import pandas as pd
import re
from datetime import datetime
import base64
from io import StringIO

class CSVToHTMLConverter:
    def __init__(self):
        self.html_template = self._load_html_template()
    
    def _load_html_template(self):
        """HTMLテンプレートを読み込み"""
        return """
<link rel="stylesheet" type="text/css" href="assets/css/c_article.css?$staticlink$">

<script src="assets/js/jquery.min.js?$staticlink$"></script>
<div class="breadcrumb">
  <ol>
    <li><a href="$url('Home-Show')$">HOME</a></li>
    <li><a href="$url('Search-Show','cgid','S010100')$">結婚祝い特集</a></li>
    <li>結婚祝いに人気のお菓子・スイーツ</li>
  </ol>
</div>
<div class="recommended">
  <a href="" class="item non-active">おすすめ商品特集を読む</a>
  <a href="$url('Search-Show','cgid','I0101')$" class="item ">おすすめ商品一覧を見る</a>
</div>
<section class="article_c article">

  <!-- メインエリア ここから -->
  <br><br>
  <!-- メインエリア-タイトル ここから -->
  <div class="article_title">
    <h1 class="article_title_txt">{title}
<br class="pc">{title_part2}</h1>
  </div>
  <!-- メインエリア-タイトル ここまで -->

  <div class="article_container">
    <div class="article_container_box">

      <!-- メインエリア-メインビジュアル ここから -->
      <div class="article_container_box_img mv">
        <img src="assets/images/top/img_dummy.gif?$staticlink$"
          data-echo="assets/images/s_article/S010117_main.jpg?$staticlink$"
          alt="結婚祝いに人気のお菓子ランキング＆高級かつおしゃれなおすすめスイーツギフト特集">
      </div>
      <!-- メインエリア-メインビジュアル ここまで -->

      <!-- メインエリア-日付 ここから -->
      <div class="day">
        <p class="text">
          <time datetime="{date}">{date_display}</time>
        </p>
      </div>
      <!-- メインエリア-日付 ここまで -->

      <!-- メインエリア-記事テキスト ここから -->
      <p class="article_container_box_txt mv">
        {description}
      </p>
      <!-- メインエリア-記事テキスト ここまで -->

      <!-- メインエリア-索引 ここから -->
      <div class="article_container_box_index">
        <p class="article_container_box_index_title">INDEX</p>
        <ul class="article_container_box_index_list">
          {index_list}
        </ul>
        <div class="article_container_box_index_btn btn transparent-red">
          <a href="https://isetan.mistore.jp/moodmark/wedding/" class="btn_link">結婚祝い特集を見る</a>
        </div>
      </div>
      <!-- メインエリア-索引 ここまで -->
    </div>
  </div>
  <!-- メインエリア ここまで -->

  {content}

    <!-- グレー線 ここから -->
    <hr class="gray s_article">
    <!-- グレー線 ここまで -->
    <!-- スライダーコンテナ ここから -->
    <div class="slider-container">
        <p class="slider-title">
            <span class="main">
                <span class="text">ARTICLES</span>
            </span>
        </p>

        <div class="box-slider">
            <ul class="slider slider-type11">
                <!-- アイテムここから -->
                <li class="slide">
                    <a href="$url('Search-Show','cgid','S010100')$">
                        <div class="img"><img src="assets/images/top/img_dummy.gif?$staticlink$"
                                data-echo="assets/images/s_article/img-slider-wedding-lp.jpg?$staticlink$"
                                alt="結婚祝いに喜ばれる相場や相手別で探すおすすめアイテム＆人気ランキング">
                        </div>
                        <div class="texts">
                            <h3 class="title">相場や相手別で探す人気ランキング</h3>
                        </div>
                    </a>
                </li>
                <!-- アイテムここまで -->

                <!-- アイテムここから -->
                <li class="slide">
                    <a href="$url('Search-Show','cgid','S010122')$">
                       <div class="img"><img src="assets/images/top/img_dummy.gif?$staticlink$"
                               data-echo="assets/images/top/S010122-slider-banner.jpg?$staticlink$"
                               alt="結婚式あり・なしべつ相場＆マナー">
                       </div>
                       <div class="texts">
                           <h3 class="title">結婚式あり・なしべつ相場＆マナー</h3>
                       </div>
                   </a>
               </li>
               <!-- アイテムここまで -->
               <!-- アイテムここから -->
               <li class="slide">
                    <a href="$url('Search-Show','cgid','S010120')$">
                       <div class="img"><img src="assets/images/top/img_dummy.gif?$staticlink$"
                               data-echo="assets/images/top/J010534_season.jpg?$staticlink$"
                               alt="職場からの結婚祝いのお返し＆マナー徹底解説！">
                       </div>
                       <div class="texts">
                           <h3 class="title">職場からの結婚祝いのお返し＆マナー徹底解説！</h3>
                       </div>
                   </a>
               </li>
               <!-- アイテムここまで -->
               <!-- アイテムここから -->
               <li class="slide">
                    <a href="$url('Search-Show','cgid','S010121')$">
                       <div class="img"><img src="assets/images/top/img_dummy.gif?$staticlink$"
                               data-echo="assets/images/article/img-slider-wedding-01.jpg?$staticlink$"
                               alt="結婚祝いにハイセンスなプレゼントを！伊勢丹バイヤーが厳選する人気ブランド">
                       </div>
                       <div class="texts">
                           <h3 class="title">結婚祝いにハイセンスなプレゼントを！伊勢丹バイヤーが厳選する人気ブランド</h3>
                       </div>
                   </a>
               </li>
               <!-- アイテムここまで -->

                <!-- アイテムここから -->
                <li class="slide">
                    <a href="$url('Search-Show','cgid','S010104')$">
                        <div class="img"><img src="assets/images/top/img_dummy.gif?$staticlink$"
                                data-echo="assets/images/s_article/img-slider-wedding-03.jpg?$staticlink$"
                                alt="新婚生活に実用的なキッチン家電を">
                        </div>
                        <div class="texts">
                            <p class="title">新婚生活に実用的なキッチン家電を</p>
                        </div>
                    </a>
                </li>
                <!-- アイテムここまで -->
                <!-- アイテムここから -->
                <li class="slide">
                   <a href="$url('Search-Show','cgid','S010118')$">
                        <div class="img"><img src="assets/images/top/img_dummy.gif?$staticlink$"
                                data-echo="assets/images/s_article/J011811_smainlg.jpg?$staticlink$"
                                alt="何枚あっても嬉しいタオルギフト">
                        </div>
                        <div class="texts">
                            <h3 class="title">新居に何枚あっても嬉しいタオルギフト</h3>
                        </div>
                    </a>
                </li>
                <!-- アイテムここまで -->
                <!-- アイテムここから -->
                <li class="slide">
                     <a href="$url('Search-Show','cgid','S010116')$">
                        <div class="img"><img src="assets/images/top/img_dummy.gif?$staticlink$"
                                data-echo="assets/images/s_article/AI0601_main_banner.jpg?$staticlink$"
                                alt="結婚祝いのカタログギフトは「おしゃれ」が人気">
                        </div>
                        <div class="texts">
                            <h3 class="title">カタログギフトは「おしゃれ」が人気</h3>
                        </div>
                    </a>
                </li>
                <!-- アイテムここまで -->
                <!-- アイテムここから -->
                <li class="slide">
                     <a href="$url('Search-Show','cgid','S010119')$">
                        <div class="img"><img src="assets/images/top/img_dummy.gif?$staticlink$"
                                data-echo="assets/images/s_article/J015103_smain_banner.jpg?$staticlink$"
                                alt="結婚祝いに食器はあり？ブランド・形で選ぶ喜ばれ日常使いギフト35選">
                        </div>
                        <div class="texts">
                            <h3 class="title">結婚祝いに食器はあり？ブランド・形で選ぶ喜ばれ日常使いギフト35選</h3>
                        </div>
                    </a>
                </li>
                <!-- アイテムここまで -->
                <!-- アイテムここから -->
                <li class="slide">
                     <a href="$url('Search-Show','cgid','S010116')$">
                        <div class="img"><img src="assets/images/top/img_dummy.gif?$staticlink$"
                                data-echo="assets/images/s_article/img-slider-wedding-06.jpg?$staticlink$"
                                alt="大切な日に贈りたい日用品">
                        </div>
                        <div class="texts">
                            <h3 class="title">もらって嬉しい日用品プレゼント</h3>
                        </div>
                    </a>
                </li>
                <!-- アイテムここまで -->


            </ul>
            <div class="slider-dots gray"></div>
        </div>
    </div>
    <!-- スライダーコンテナ ここまで -->
  <!-- グレー線 ここから -->
  <hr class="gray s_article">
  <!-- グレー線 ここまで -->


  <!-- 記事エリア ここまで -->
</section>

<script>
  $('a[href^="#"]').click(function () {
    var speed = 400;
    var href = $(this).attr("href");
    var target = $(href == "#" || href == "" ? 'html' : href);
    var position
    var header_size
    var header = $('.header-top').height();;
    var global_nav = $('#globalMenu').height();;
    var coupon = $('.header-coupon-area').height();;
    if (coupon = null) {
      header_size = header + global_nav
      position = target.offset().top - header_size
    } else {
      header_size = header + global_nav + coupon
      position = target.offset().top - header_size
    }
    $('body,html').animate({
      scrollTop: position
    }, speed, 'swing');
    return false;
  });

  $(".is-open").each(function (index, element) {
    $(this).click(function () {
      var links = $(this).children('.open-link');
      links.toggleClass("open")
      $(this).toggleClass("is-opened")
    })
  });

  $(window).on("resize", function () {
    if ($(".breadcrumb").width() < $(".breadcrumb ol").width()) {
      $(".breadcrumb").addClass("text-overflow");
    } else {
      $(".breadcrumb").removeClass("text-overflow");
    }
  });

  $(function () {
    if ($(".breadcrumb").width() < $(".breadcrumb ol").width()) {
      $(".breadcrumb").addClass("text-overflow");
    } else {
      $(".breadcrumb").removeClass("text-overflow");
    }
  });
  if ($('.section-item-list').length > 0) {
    $('#content-wrap').addClass('page-product-list')
  }
</script>
"""
    
    def parse_csv(self, csv_content):
        """CSVを解析して構造化データに変換"""
        try:
            # CSVを読み込み
            df = pd.read_csv(StringIO(csv_content))
            
            # データを整理
            parsed_data = {
                'title': '',
                'description': '',
                'sections': [],
                'index_items': []
            }
            
            current_section = None
            current_h3 = None
            
            for index, row in df.iterrows():
                tag = str(row['タグ']).strip()
                title_text = str(row['title or description or heedline']).strip()
                description_text = str(row['見出し下に＜p＞タグを入れる場合のテキスト']).strip()
                
                if tag == 'title':
                    parsed_data['title'] = title_text
                elif tag == 'description':
                    parsed_data['description'] = title_text
                elif tag == 'H2':
                    # 新しいセクション開始
                    if current_section:
                        parsed_data['sections'].append(current_section)
                    
                    current_section = {
                        'title': title_text,
                        'description': description_text,
                        'h3_items': [],
                        'id': f"article_{len(parsed_data['sections']) + 1:02d}"
                    }
                    
                    # インデックスに追加
                    parsed_data['index_items'].append({
                        'title': title_text,
                        'id': current_section['id']
                    })
                    
                elif tag == 'H3':
                    if current_section:
                        # ランキングH3かどうかを判定（【数字位】で始まる）
                        is_ranking = title_text.startswith('【') and '位】' in title_text
                        
                        current_h3 = {
                            'title': title_text,
                            'description': description_text,
                            'h4_items': [],
                            'is_ranking': is_ranking,
                            'ranking_data': None
                        }
                        
                        # ランキングの場合、商品情報を取得
                        if is_ranking:
                            url1 = str(row['URL（商品・リンク）①']).strip()
                            alt1 = str(row['alt（商品名）①']).strip()
                            span1 = str(row['span（商品名）①']).strip()
                            
                            if url1 and url1 != 'nan':
                                current_h3['ranking_data'] = {
                                    'url': url1,
                                    'alt': alt1,
                                    'span': span1 if span1 != 'nan' else alt1
                                }
                        
                        current_section['h3_items'].append(current_h3)
                
                elif tag == 'H4':
                    if current_h3:
                        # 商品情報を取得
                        url1 = str(row['URL（商品・リンク）①']).strip()
                        alt1 = str(row['alt（商品名）①']).strip()
                        span1 = str(row['span（商品名）①']).strip()
                        url2 = str(row['URL（商品・リンク）②']).strip()
                        span2 = str(row['span（商品名）②']).strip()
                        
                        h4_item = {
                            'title': title_text,
                            'description': description_text,
                            'products': []
                        }
                        
                        # 商品1
                        if url1 and url1 != 'nan':
                            h4_item['products'].append({
                                'url': url1,
                                'alt': alt1,
                                'span': span1 if span1 != 'nan' else alt1
                            })
                        
                        # 商品2
                        if url2 and url2 != 'nan':
                            h4_item['products'].append({
                                'url': url2,
                                'alt': alt1,  # altは共通
                                'span': span2 if span2 != 'nan' else alt1
                            })
                        
                        current_h3['h4_items'].append(h4_item)
            
            # 最後のセクションを追加
            if current_section:
                parsed_data['sections'].append(current_section)
            
            return parsed_data
            
        except Exception as e:
            st.error(f"CSV解析エラー: {str(e)}")
            return None
    
    def generate_html(self, parsed_data):
        """解析済みデータからHTMLを生成"""
        try:
            # インデックスリスト生成（元のHTMLと同じ形式）
            index_list = ""
            for item in parsed_data['index_items']:
                index_list += f'''          <li>
            <a href="#{item["id"]}">{item["title"]}</a>
          </li>
'''
            
            # コンテンツ生成
            content = ""
            for section in parsed_data['sections']:
                # セクション番号を取得
                section_num = parsed_data['sections'].index(section) + 1
                content += f'''
  <!-- セクション{section_num} ここから -->
  <!-- h2 ここから -->
  <h2 class="section-title" id="{section['id']}">{section['title']}</h2>
  <!-- h2 ここまで -->
  <p class="text">
    {section['description']}
  </p>
  <!-- セクション{section_num} ここまで -->
'''
                
                # ランキングスライダーかどうかを判定
                has_ranking = any(h3.get('is_ranking', False) for h3 in section['h3_items'])
                
                if has_ranking:
                    # ランキングスライダーを生成
                    content += '''
    <!-- スライダーコンテナ ここから -->  
  <div class="slider-container">
        <h3 class="slider-title">
            <span class="sub"></span>
            <span class="main">
                <span class="text">RANKING</span>
            </span>
        </h3>
        <div class="box-slider">
            <ul class="slider slider-type11">
'''
                    
                    # ランキングアイテムを生成
                    for h3_item in section['h3_items']:
                        if h3_item.get('is_ranking', False) and h3_item.get('ranking_data'):
                            ranking_data = h3_item['ranking_data']
                            product_id = self._extract_product_id(ranking_data['url'])
                            
                            content += f'''
                <!-- アイテムここから -->
                <li class="slide">
                    <a href="{ranking_data['url']}?cgid=J011403">
                        <div class="img">
                            <img alt="{ranking_data['alt']}" data-echo="assets/images/s_article/{product_id}.jpg?$staticlink$"
                                src="assets/images/top/img_dummy.gif?$staticlink$">
                        </div>
                        <div class="texts">
                            <p class="title">{h3_item['title']}</p>
                            <p class="price">
                                $include('Product-GetIncTaxPrice', 'pid', '{product_id}')$
                            </p>
                            <div class="tags">
                                $include('Product-GetProductTags', 'pid', '{product_id}')$
                            </div>
                        </div>
                    </a>
                </li>
                <!-- アイテムここまで -->
'''
                    
                    content += '''
            </ul>
            <div class="slider-dots gray"></div>
        </div>
    </div><br><br><br>
    <!-- スライダーコンテナ ここまで -->
'''
                else:
                    # 通常のH3アイテムを生成
                    for h3_item in section['h3_items']:
                        content += f'''
  <h3 class="section-subtitle">{h3_item['title']}</h3><br>
  <p class="text">{h3_item['description']}</p>
'''
                        
                        # H4アイテムを処理
                        for h4_item in h3_item['h4_items']:
                            if h4_item['products']:
                                # 商品ボックス生成
                                content += f'''
  <!-- アイテム ここから -->
  <div class="item-box">
    <div class="box">
      <h4 class="item-box-subtitle">{h4_item['title']}</h4>
      <p class="text">{h4_item['description']}</p>
      <div class="img-box">
        <img src="assets/images/top/img_dummy.gif?$staticlink$"
          data-echo="assets/images/s_article/{self._extract_product_id(h4_item['products'][0]['url'])}.jpg?$staticlink$" 
          alt="{h4_item['products'][0]['alt']}" class="img">
      </div>
      <div class="link">
'''
                                
                                # 商品リンク生成
                                for i, product in enumerate(h4_item['products']):
                                    if i > 0:
                                        content += '<br>'
                                    content += f'''
      <a href="{product['url']}?cgid=S010117" class="item">
        <span class="text">{product['span']}</span>
        <img src="assets/images/s_article/ico_circle_arrow.svg?$staticlink$" alt="詳しくはこちら" class="img">
      </a>
      <p class="price">
        $include('Product-GetIncTaxPrice', 'pid', '{self._extract_product_id(product['url'])}')$
      </p>
      <div class="tags">
        $include('Product-GetProductTags', 'pid', '{self._extract_product_id(product['url'])}')$
      </div>
'''
                                
                                content += '''
    </div>
    </div>
    <div class="box img-box">
      <img src="assets/images/top/img_dummy.gif?$staticlink$"
        data-echo="assets/images/s_article/''' + self._extract_product_id(h4_item['products'][0]['url']) + '''.jpg?$staticlink$" 
        alt="''' + h4_item['products'][0]['alt'] + '''" class="img">
    </div>
  </div>
  <!-- アイテム ここまで -->
'''
                            else:
                                # 商品なしのH4
                                content += f'''
  <h4 class="item-box-subtitle">{h4_item['title']}</h4>
  <p class="text">{h4_item['description']}</p>
'''
                
                content += '''
  <!-- グレー線 ここから -->
  <hr class="gray s_article">
  <!-- グレー線 ここまで -->
'''
            
            # 固定日付（元のHTMLと同じ）
            date_str = "2025-9-271T10:00"
            date_display = "2025年9月27日 更新"
            
            # タイトルを分割（元のHTMLと同じ形式）
            full_title = parsed_data['title']
            if '人気のお菓子ランキング＆おすすめスイーツギフト特集' in full_title:
                title_part1 = full_title.replace('人気のお菓子ランキング＆おすすめスイーツギフト特集', '').strip()
                title_part2 = '人気のお菓子ランキング＆おすすめスイーツギフト特集'
            else:
                title_part1 = full_title
                title_part2 = ''
            
            # HTMLテンプレートに値を挿入（文字列置換を使用）
            html_output = self.html_template
            html_output = html_output.replace('{title}', title_part1)
            html_output = html_output.replace('{title_part2}', title_part2)
            html_output = html_output.replace('{description}', parsed_data['description'])
            html_output = html_output.replace('{index_list}', index_list)
            html_output = html_output.replace('{content}', content)
            html_output = html_output.replace('{date}', date_str)
            html_output = html_output.replace('{date_display}', date_display)
            
            return html_output
            
        except Exception as e:
            st.error(f"HTML生成エラー: {str(e)}")
            return None
    
    def _extract_product_id(self, url):
        """URLから商品IDを抽出"""
        if not url or url == 'nan':
            return 'dummy'
        
        # URLから商品IDを抽出（例: MM-0410771005508）
        match = re.search(r'MM-[\w-]+', url)
        if match:
            return match.group(0)
        return 'dummy'

def main():
    st.set_page_config(
        page_title="MOO:D MARK CSV to HTML Converter",
        page_icon="📄",
        layout="wide"
    )
    
    st.title("MOO:D MARK｜CSV to HTML コンバーター")
    st.markdown("---")
    
    # サイドバー
    with st.sidebar:
        st.header("📋 使用方法")
        st.markdown("""
        1. CSVファイルをアップロード
        2. プレビューで内容を確認
        3. HTMLをダウンロード
        
        **CSV形式:**
        - タグ列: title, description, H2, H3, H4
        - 見出し列: タイトルテキスト
        - 説明列: 説明文
        - URL列: 商品リンク
        """)
        
        st.header("📁 サンプルファイル")
        with open("csv/MOODMARK｜結婚祝い お菓子 - to中村さん結婚祝い お菓子｜改善案 コピー.csv", "r", encoding="utf-8") as f:
            csv_content = f.read()
        
        st.download_button(
            label="📥 実際のCSVファイルをダウンロード",
            data=csv_content,
            file_name="MOODMARK_結婚祝いお菓子_改善案.csv",
            mime="text/csv"
        )
    
    # メインエリア
    converter = CSVToHTMLConverter()
    
    # ファイルアップロード
    uploaded_file = st.file_uploader(
        "CSVファイルをアップロードしてください",
        type=['csv'],
        help="結婚祝いお菓子記事のCSVファイルを選択してください"
    )
    
    if uploaded_file is not None:
        try:
            # CSV読み込み
            csv_content = uploaded_file.read().decode('utf-8')
            
            # データ解析
            with st.spinner("CSVを解析中..."):
                parsed_data = converter.parse_csv(csv_content)
            
            if parsed_data:
                st.success("✅ CSV解析が完了しました！")
                
                # プレビュー
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.subheader("📊 解析結果プレビュー")
                    
                    # 基本情報
                    st.info(f"**タイトル:** {parsed_data['title']}")
                    st.info(f"**説明:** {parsed_data['description'][:100]}...")
                    st.info(f"**セクション数:** {len(parsed_data['sections'])}")
                    
                    # セクション一覧
                    st.subheader("📑 セクション一覧")
                    for i, section in enumerate(parsed_data['sections'], 1):
                        with st.expander(f"セクション {i}: {section['title']}"):
                            st.write(f"**説明:** {section['description']}")
                            st.write(f"**H3項目数:** {len(section['h3_items'])}")
                            
                            for j, h3 in enumerate(section['h3_items'], 1):
                                st.write(f"  - H3-{j}: {h3['title']}")
                                for k, h4 in enumerate(h3['h4_items'], 1):
                                    st.write(f"    - H4-{k}: {h4['title']} (商品数: {len(h4['products'])})")
                
                with col2:
                    st.subheader("🔧 HTML生成")
                    
                    if st.button("🚀 HTMLを生成", type="primary"):
                        with st.spinner("HTMLを生成中..."):
                            html_output = converter.generate_html(parsed_data)
                        
                        if html_output:
                            st.success("✅ HTML生成が完了しました！")
                            
                            # プレビュー表示の選択（radio buttonでバグ回避）
                            preview_option = st.radio(
                                "プレビュー表示オプション:",
                                ["最初の1000文字", "最初の2000文字", "最初の5000文字", "完全表示"],
                                index=3,  # デフォルトで完全表示を選択
                                horizontal=True
                            )
                            
                            # HTMLプレビュー
                            st.subheader("👀 HTMLプレビュー")
                            html_lines = len(html_output.splitlines())
                            st.info(f"📊 HTMLサイズ: {len(html_output):,} 文字, {html_lines:,} 行")
                            
                            # プレビュー範囲の情報表示
                            if preview_option == "完全表示":
                                st.success(f"✅ 完全表示: {html_lines:,} 行すべてを表示")
                            else:
                                preview_chars = int(preview_option.split("文字")[0].split("の")[1])
                                preview_lines = len(html_output[:preview_chars].splitlines())
                                percentage = (preview_lines / html_lines) * 100
                                st.info(f"📄 プレビュー: {preview_lines:,} 行 ({preview_chars:,} 文字) / 全体 {html_lines:,} 行 ({percentage:.1f}%)")
                                
                            # 行数の詳細説明
                            with st.expander("📊 行数の詳細説明"):
                                st.markdown("""
                                **行数の意味:**
                                - **HTML行数**: 生成されたHTMLファイルの総行数
                                - **プレビュー行数**: 現在表示している範囲の行数
                                - **割合**: プレビュー範囲が全体の何%かを表示
                                
                                **参考情報:**
                                - 元のHTMLファイル: 1,759行
                                - 生成HTMLファイル: 約1,820行
                                - 差分: 約61行（セクションコメントの追加など）
                                """)
                                
                            # 元のHTMLファイルとの比較
                            try:
                                with open('【サンプル】結婚祝いお菓子.html', 'r', encoding='utf-8') as f:
                                    original_html = f.read()
                                original_lines = len(original_html.splitlines())
                                original_size = len(original_html)
                                
                                st.subheader("📈 元のHTMLファイルとの比較")
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    st.metric(
                                        label="行数",
                                        value=f"{html_lines:,}",
                                        delta=f"{html_lines - original_lines:+d}",
                                        help=f"元のHTML: {original_lines:,} 行"
                                    )
                                
                                with col2:
                                    st.metric(
                                        label="文字数",
                                        value=f"{len(html_output):,}",
                                        delta=f"{len(html_output) - original_size:+d}",
                                        help=f"元のHTML: {original_size:,} 文字"
                                    )
                                
                                with col3:
                                    match_rate = (1 - abs(len(html_output) - original_size) / original_size) * 100
                                    st.metric(
                                        label="一致率",
                                        value=f"{match_rate:.1f}%",
                                        delta=f"{match_rate - 100:.1f}%",
                                        help="元のHTMLファイルとの一致率"
                                    )
                                    
                            except FileNotFoundError:
                                st.warning("⚠️ 元のHTMLファイルが見つかりません。比較情報を表示できません。")
                            
                            if preview_option == "最初の1000文字":
                                preview_text = html_output[:1000] + "..." if len(html_output) > 1000 else html_output
                            elif preview_option == "最初の2000文字":
                                preview_text = html_output[:2000] + "..." if len(html_output) > 2000 else html_output
                            elif preview_option == "最初の5000文字":
                                preview_text = html_output[:5000] + "..." if len(html_output) > 5000 else html_output
                            else:
                                preview_text = html_output
                            
                            st.code(preview_text, language="html")
                            
                            # HTML構造検証
                            st.subheader("🔍 HTML構造検証")
                            import re
                            
                            # タグの整合性チェック
                            opening_tags = re.findall(r'<[^/][^>]*>', html_output)
                            closing_tags = re.findall(r'</[^>]*>', html_output)
                            
                            # 自己終了タグ
                            self_closing_tags = ['br', 'hr', 'img', 'input', 'meta', 'link', 'area', 'base', 'col', 'embed', 'param', 'source', 'track', 'wbr']
                            
                            # タグのカウント
                            tag_counts = {}
                            for tag in opening_tags:
                                tag_name = re.match(r'<([a-zA-Z][a-zA-Z0-9]*)', tag)
                                if tag_name and tag_name.group(1).lower() not in self_closing_tags:
                                    tag_name = tag_name.group(1)
                                    tag_counts[tag_name] = tag_counts.get(tag_name, 0) + 1
                            
                            for tag in closing_tags:
                                tag_name = re.match(r'</([a-zA-Z][a-zA-Z0-9]*)', tag)
                                if tag_name:
                                    tag_name = tag_name.group(1)
                                    if tag_name in tag_counts:
                                        tag_counts[tag_name] = tag_counts.get(tag_name, 0) - 1
                            
                            unclosed_tags = [(tag, count) for tag, count in tag_counts.items() if count > 0]
                            
                            if not unclosed_tags:
                                st.success("✅ HTMLタグの構造は正常です")
                            else:
                                st.error(f"❌ {sum(count for _, count in unclosed_tags)} 個のタグが閉じられていません")
                                for tag, count in unclosed_tags:
                                    st.write(f"   - {tag}: {count}個")
                            
                            # ダウンロードボタン
                            st.download_button(
                                label="📥 HTMLファイルをダウンロード",
                                data=html_output,
                                file_name=f"wedding_sweets_article_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                                mime="text/html"
                            )
                            
                            # 統計情報
                            st.subheader("📈 生成統計")
                            col_a, col_b, col_c = st.columns(3)
                            with col_a:
                                st.metric("セクション数", len(parsed_data['sections']))
                            with col_b:
                                total_products = sum(
                                    len(h4['products']) 
                                    for section in parsed_data['sections'] 
                                    for h3 in section['h3_items'] 
                                    for h4 in h3['h4_items']
                                )
                                st.metric("商品数", total_products)
                            with col_c:
                                st.metric("HTMLサイズ", f"{len(html_output):,} 文字")
        
        except Exception as e:
            st.error(f"❌ エラーが発生しました: {str(e)}")
    
    else:
        # デモ表示
        st.subheader("🎯 デモ: サンプルCSVでHTML生成")
        
        if st.button("📝 サンプルCSVでデモ実行", type="secondary"):
            try:
                # サンプルCSV読み込み
                with open("csv/MOODMARK｜結婚祝い お菓子 - to中村さん結婚祝い お菓子｜改善案 コピー.csv", "r", encoding="utf-8") as f:
                    csv_content = f.read()
                
                # データ解析
                with st.spinner("サンプルCSVを解析中..."):
                    parsed_data = converter.parse_csv(csv_content)
                
                if parsed_data:
                    st.success("✅ サンプルCSV解析が完了しました！")
                    
                    # HTML生成
                    with st.spinner("HTMLを生成中..."):
                        html_output = converter.generate_html(parsed_data)
                    
                    if html_output:
                        st.success("✅ HTML生成が完了しました！")
                        
                        # ダウンロードボタン
                        st.download_button(
                            label="📥 生成されたHTMLをダウンロード",
                            data=html_output,
                            file_name="sample_wedding_sweets_article.html",
                            mime="text/html"
                        )
                        
                        # プレビュー表示の選択（radio buttonでバグ回避）
                        preview_option = st.radio(
                            "プレビュー表示オプション:",
                            ["最初の1000文字", "最初の2000文字", "最初の5000文字", "完全表示"],
                            index=3,  # デフォルトで完全表示を選択
                            horizontal=True,
                            key="demo_preview_radio"
                        )
                        
                        # プレビュー
                        st.subheader("👀 生成されたHTMLプレビュー")
                        html_lines = len(html_output.splitlines())
                        st.info(f"📊 HTMLサイズ: {len(html_output):,} 文字, {html_lines:,} 行")
                        
                        # プレビュー範囲の情報表示
                        if preview_option == "完全表示":
                            st.success(f"✅ 完全表示: {html_lines:,} 行すべてを表示")
                        else:
                            preview_chars = int(preview_option.split("文字")[0].split("の")[1])
                            preview_lines = len(html_output[:preview_chars].splitlines())
                            percentage = (preview_lines / html_lines) * 100
                            st.info(f"📄 プレビュー: {preview_lines:,} 行 ({preview_chars:,} 文字) / 全体 {html_lines:,} 行 ({percentage:.1f}%)")
                            
                        # 行数の詳細説明
                        with st.expander("📊 行数の詳細説明"):
                            st.markdown("""
                            **行数の意味:**
                            - **HTML行数**: 生成されたHTMLファイルの総行数
                            - **プレビュー行数**: 現在表示している範囲の行数
                            - **割合**: プレビュー範囲が全体の何%かを表示
                            
                            **参考情報:**
                            - 元のHTMLファイル: 1,759行
                            - 生成HTMLファイル: 約1,820行
                            - 差分: 約61行（セクションコメントの追加など）
                            """)
                        
                        if preview_option == "最初の1000文字":
                            preview_text = html_output[:1000] + "..." if len(html_output) > 1000 else html_output
                        elif preview_option == "最初の2000文字":
                            preview_text = html_output[:2000] + "..." if len(html_output) > 2000 else html_output
                        elif preview_option == "最初の5000文字":
                            preview_text = html_output[:5000] + "..." if len(html_output) > 5000 else html_output
                        else:
                            preview_text = html_output
                        
                        st.code(preview_text, language="html")
            
            except Exception as e:
                st.error(f"❌ デモ実行エラー: {str(e)}")

if __name__ == "__main__":
    main()
