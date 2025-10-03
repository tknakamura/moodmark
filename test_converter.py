#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV to HTML Converter テストスクリプト
"""

import pandas as pd
import re
from datetime import datetime
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
            # CSVを読み込み（改行を含むフィールドに対応）
            df = pd.read_csv(StringIO(csv_content), quoting=1, escapechar='\\')
            
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
            print(f"CSV解析エラー: {str(e)}")
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
            import traceback
            print(f"HTML生成エラー: {str(e)}")
            print("詳細エラー:")
            traceback.print_exc()
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
    print("🧪 CSV to HTML Converter テスト開始")
    print("=" * 50)
    
    # コンバーターをテスト
    converter = CSVToHTMLConverter()
    
    # 実際のCSVファイルを読み込み
    try:
        with open("csv/MOODMARK｜結婚祝い お菓子 - to中村さん結婚祝い お菓子｜改善案 コピー.csv", "r", encoding="utf-8") as f:
            csv_content = f.read()
        
        print("📊 CSV解析テスト...")
        parsed_data = converter.parse_csv(csv_content)
    except Exception as e:
        print(f"❌ CSVファイル読み込みエラー: {str(e)}")
        return
    
    if parsed_data:
        print('✅ CSV解析成功')
        print(f'   タイトル: {parsed_data["title"]}')
        print(f'   説明: {parsed_data["description"]}')
        print(f'   セクション数: {len(parsed_data["sections"])}')
        
        # HTML生成テスト
        print("\n🔧 HTML生成テスト...")
        html_output = converter.generate_html(parsed_data)
        if html_output:
            print('✅ HTML生成成功')
            print(f'   HTMLサイズ: {len(html_output)} 文字')
            
            # ファイルに保存
            with open('test_output.html', 'w', encoding='utf-8') as f:
                f.write(html_output)
            print('   📁 test_output.html に保存しました')
        else:
            print('❌ HTML生成失敗')
    else:
        print('❌ CSV解析失敗')

if __name__ == "__main__":
    main()
