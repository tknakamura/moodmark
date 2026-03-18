#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
コミュニティコンバーター
ランキングなし・スライダーなしバージョンのCSV to HTMLコンバーター
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import re
from datetime import datetime
from io import StringIO
import json
import os
import sys

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# 認証関連の関数（既存のcsv_to_html_dashboard.pyからインポート）
from csv_to_html_dashboard import (
    load_users,
    verify_password,
    check_authentication,
    login_page,
    render_likepass_footer,
)

# ページ設定
st.set_page_config(
    page_title="MOODMARK コミュニティコンバーター",
    page_icon="📄",
    layout="wide"
)

class CommunityCSVToHTMLConverter:
    def __init__(self, article_cgid='J012542'):
        self.html_template = self._load_html_template()
        self.article_cgid = article_cgid  # 記事の商品リンクに使用するcgid
        # ランキングとスライダーは常に無効
        self.enable_ranking = False
        self.enable_slider = False
    
    def _load_html_template(self):
        """HTMLテンプレートを読み込み（参照HTMLベース、ランキング・スライダー除外）"""
        return """
<link rel="stylesheet" type="text/css" href="assets/css/c_article.css?$staticlink$">

<script src="assets/js/jquery.min.js?$staticlink$"></script>
<div class="breadcrumb">
    <ol>
        <li><a href="$url('Home-Show')$">HOME</a></li>
        <li>{breadcrumb_text}</li>
    </ol>
</div>

  <!-- メインエリア ここから -->
 <section class="article_c article">

  <!-- メインエリア-タイトル ここから -->
    <div class="article_title">
        <h1 class="article_title_txt">{h1_title}</h1>
    </div>
  <!-- メインエリア-タイトル ここまで -->

  <div class="article_container">
    <div class="article_container_box">

            <!-- メインエリア-メインビジュアル ここから -->
            <div class="article_container_box_img mv">
                <img src="assets/images/top/img_dummy.gif?$staticlink$"
                     data-echo="assets/images/s_article/{main_image}?$staticlink$"
                     alt="{h1_title}">
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
          <a href="https://isetan.mistore.jp/moodmark/christmas/" class="btn_link">クリスマス特集を見る</a>
        </div>
      </div>
      <!-- メインエリア-索引 ここまで -->
    </div>
  </div>
  <!-- メインエリア ここまで -->

  {content}

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

            def clean_value(value):
                if pd.isna(value):
                    return ''
                val = str(value).strip()
                return '' if val.lower() == 'nan' else val

            # データを整理
            parsed_data = {
                'title': '',
                'h1_title': '',
                'description': '',
                'sections': [],
                'index_items': [],
                'div_items': [],  # divタグ用
                'standalone_p_tags': []  # 独立したpタグ用
            }
            
            current_section = None
            current_h3 = None
            current_h4 = None
            
            # テキストリンク統合用：すべての行をリストに変換
            rows_list = []
            for index, row in df.iterrows():
                rows_list.append({
                    'index': index,
                    'row': row
                })
            
            # テキストリンクのdivタグを検出して、直前のpタグにマークを付ける
            for i, item in enumerate(rows_list):
                row = item['row']
                tag = clean_value(row['タグ'])
                div_type = clean_value(row.get('div種類', ''))
                
                # テキストリンクのdivタグの場合、直前のpタグにマークを付ける
                if tag == 'div' and div_type == 'テキストリンク' and i > 0:
                    prev_item = rows_list[i - 1]
                    prev_row = prev_item['row']
                    prev_tag = clean_value(prev_row['タグ'])
                    
                    if prev_tag == 'pタグ':
                        # 直前の行がpタグの場合、マークを付ける
                        prev_item['has_text_link_after'] = {
                            'text': clean_value(row.get('title or description or heedline', '')),
                            'url': clean_value(row.get('URL（商品・リンク）①', ''))
                        }
                        item['is_text_link_merged'] = True  # このdivは統合されたので処理をスキップ
            
            # 通常の処理を実行
            for item in rows_list:
                index = item['index']
                row = item['row']
                tag = clean_value(row['タグ'])
                title_text = clean_value(row['title or description or heedline'])
                description_text = clean_value(row['見出し下に＜p＞タグを入れる場合のテキスト'])
                div_type = clean_value(row.get('div種類', ''))
                display = clean_value(row.get('表示', ''))
                link_state = clean_value(row.get('商品リンク状態', ''))
                
                # テキストリンクが統合済みの場合はスキップ
                if item.get('is_text_link_merged', False):
                    continue

                if tag == 'title':
                    parsed_data['title'] = title_text
                elif tag == 'description':
                    parsed_data['description'] = title_text
                elif tag == 'H1':
                    parsed_data['h1_title'] = title_text
                elif tag == 'H2':
                    # 新しいセクション開始
                    if current_section:
                        parsed_data['sections'].append(current_section)
                    
                    current_section = {
                        'title': title_text,
                        'description': description_text,
                        'h3_items': [],
                        'div_items': [],
                        'p_tags': [],
                        'id': f"article_{len(parsed_data['sections']) + 1:02d}"
                    }
                    
                    # インデックスに追加
                    parsed_data['index_items'].append({
                        'title': title_text,
                        'id': current_section['id']
                    })
                    
                    current_h3 = None
                    current_h4 = None

                elif tag == 'H3':
                    if current_section:
                        current_h3 = {
                            'title': title_text,
                            'description': description_text,
                            'h4_items': []
                        }
                        current_section['h3_items'].append(current_h3)
                        current_h4 = None
                
                elif tag == 'H4':
                    # H3が存在しないセクションでもH4（商品枠）を出せるようにする
                    # 参照HTMLでは「H2 → div(ボタン) → item-box(H4)」の並びがあり、H3無しのケースがある
                    if (current_h3 is None) and current_section:
                        current_h3 = {
                            'title': '',
                            'description': '',
                            'h4_items': []
                        }
                        current_section['h3_items'].append(current_h3)

                    if current_h3:
                        # 商品情報を取得（最大4リンクまで対応）
                        url1 = clean_value(row.get('URL（商品・リンク）①', ''))
                        alt1 = clean_value(row.get('alt（商品名）①', ''))
                        span1 = clean_value(row.get('span（商品名）①', ''))
                        url2 = clean_value(row.get('URL（商品・リンク）②', ''))
                        span2 = clean_value(row.get('span（商品名）②', ''))
                        
                        # 3つ目と4つ目のリンクを取得（列が存在する場合）
                        url3 = clean_value(row.get('URL（商品・リンク）③', '')) if 'URL（商品・リンク）③' in row else ''
                        span3 = clean_value(row.get('span（商品名）③', '')) if 'span（商品名）③' in row else ''
                        url4 = clean_value(row.get('URL（商品・リンク）④', '')) if 'URL（商品・リンク）④' in row else ''
                        span4 = clean_value(row.get('span（商品名）④', '')) if 'span（商品名）④' in row else ''
                        
                        # E列（表示）とF列（商品リンク状態）の処理
                        # displayが空または'ON'の場合はTrue（表示）、'OFF'の場合はFalse
                        display_value = True
                        if display and display.strip():
                            display_upper = display.upper().strip()
                            if display_upper == 'OFF':
                                display_value = False
                            elif display_upper == 'ON':
                                display_value = True
                        
                        # link_stateが空または'ON'の場合はTrue（リンク有効）、'OFF'の場合はFalse
                        link_enabled_value = True
                        if link_state:
                            link_state_cleaned = str(link_state).strip()
                            if link_state_cleaned:
                                link_state_upper = link_state_cleaned.upper()
                                if link_state_upper == 'OFF':
                                    link_enabled_value = False
                                elif link_state_upper == 'ON':
                                    link_enabled_value = True
                        
                        h4_item = {
                            'title': title_text,
                            'description': description_text,
                            'products': [],
                            'display': display_value,
                            'link_enabled': link_enabled_value
                        }
                        
                        # 商品1
                        if url1:
                            h4_item['products'].append({
                                'url': url1,
                                'alt': alt1,
                                'span': span1 or alt1
                            })
                        
                        # 商品2
                        if url2:
                            h4_item['products'].append({
                                'url': url2,
                                'alt': alt1,  # altは共通
                                'span': span2 or alt1
                            })
                        
                        # 商品3
                        if url3:
                            h4_item['products'].append({
                                'url': url3,
                                'alt': alt1,  # altは共通
                                'span': span3 or alt1
                            })
                        
                        # 商品4
                        if url4:
                            h4_item['products'].append({
                                'url': url4,
                                'alt': alt1,  # altは共通
                                'span': span4 or alt1
                            })
                        
                        current_h3['h4_items'].append(h4_item)
                        current_h4 = h4_item
                
                elif tag == 'div':
                    # divタグの処理（テキストリンクは既にpタグに統合済みのため、ここでは処理しない）
                    if div_type == 'テキストリンク':
                        # テキストリンクは既にpタグに統合されているのでスキップ
                        continue
                    
                    # ボタンリンク、画像の場合
                    div_item = {
                        'type': div_type,  # ボタンリンク、画像
                        'text': title_text,  # B列
                        'image_name': description_text,  # C列（画像名）
                        'url': clean_value(row.get('URL（商品・リンク）①', ''))  # URL列から取得
                    }
                    
                    if current_section:
                        current_section['div_items'].append(div_item)
                    else:
                        parsed_data['div_items'].append(div_item)
                
                elif tag == 'pタグ':
                    if current_h4:
                        # H4に紐づくpタグ（スライダー用、今回は無効）
                        pass
                    elif current_section:
                        # 独立したpタグ
                        p_tag_item = {
                            'text': title_text or description_text
                        }
                        # テキストリンクが統合されている場合は追加
                        if item.get('has_text_link_after'):
                            p_tag_item['text_link'] = item['has_text_link_after']
                        current_section['p_tags'].append(p_tag_item)
                    else:
                        # セクション外の独立したpタグ
                        p_tag_item = {
                            'text': title_text or description_text
                        }
                        # テキストリンクが統合されている場合は追加
                        if item.get('has_text_link_after'):
                            p_tag_item['text_link'] = item['has_text_link_after']
                        parsed_data['standalone_p_tags'].append(p_tag_item)
            
            # 最後のセクションを追加
            if current_section:
                parsed_data['sections'].append(current_section)
            
            return parsed_data
            
        except Exception as e:
            st.error(f"CSV解析エラー: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
            return None
    
    def generate_html(self, parsed_data):
        """解析済みデータからHTMLを生成"""
        try:
            # インデックスリスト生成
            index_list = ""
            for item in parsed_data['index_items']:
                index_list += f'''          <li>
            <a href="#{item["id"]}">{item["title"]}</a>
          </li>
'''
            
            # コンテンツ生成
            content = ""
            for section in parsed_data['sections']:
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
                
                # H3アイテムを処理
                for h3_item in section['h3_items']:
                    # H3が無いセクション向けに、内部的に作った“無名H3”は見出しを出さない
                    if h3_item.get('title'):
                        content += f'''
  <h3 class="section-subtitle">{h3_item['title']}</h3><br>
'''
                        # descriptionがnan以外の場合のみ追加
                        if h3_item.get('description') and h3_item['description'] != 'nan':
                            content += f'''
  <p class="text">{h3_item['description']}</p>
'''
                    
                    # H4アイテムを処理
                    for h4_item in h3_item['h4_items']:
                        # E列（表示）がOFFの場合は商品枠を生成しない
                        if not h4_item.get('display', True):
                            continue
                        
                        if h4_item['products']:
                            # 商品ボックス生成
                            primary_product_id = self._extract_product_id(h4_item['products'][0]['url'])
                            primary_alt = h4_item['products'][0]['alt']
                            link_enabled = h4_item.get('link_enabled', True)
                            
                            content += f'''
  <!-- アイテム ここから -->
  <div class="item-box">
    <div class="box">
      <h4 class="item-box-subtitle">{h4_item['title']}</h4>
'''
                            if h4_item['description']:
                                content += f'''
      <p class="text">{h4_item['description']}</p>
'''
                            content += f'''
      <div class="img-box">
        <img src="assets/images/top/img_dummy.gif?$staticlink$"
          data-echo="assets/images/s_article/{primary_product_id}.jpg?$staticlink$" 
          alt="{primary_alt}" class="img">
      </div>
      <div class="link">
'''
                            
                            # 商品リンク生成
                            for i, product in enumerate(h4_item['products']):
                                if i > 0:
                                    content += '<br>'
                                product_id = self._extract_product_id(product['url'])
                                
                                if link_enabled:
                                    # F列がONの場合：通常のリンク
                                    content += f'''
      <a href="$url('Product-Show','pid','{product_id}')$?cgid={self.article_cgid}" class="item">
        <span class="text">{product['span']}</span>
        <img src="assets/images/s_article/ico_circle_arrow.svg?$staticlink$" alt="詳しくはこちら" class="img">
      </a>
'''
                                else:
                                    # F列がOFFの場合：リンク無効（参照HTMLに合わせて<a>タグでclass="item soldout"を使用）
                                    content += f'''
      <a href="$url('Product-Show','pid','{product_id}')$?cgid={self.article_cgid}" class="item soldout">
        <span class="text">{product['span']}</span>
        <img src="assets/images/s_article/ico_circle_arrow.svg?$staticlink$" alt="詳しくはこちら" class="img">
      </a>
'''
                                
                                content += f'''
      <p class="price">
        $include('Product-GetIncTaxPrice', 'pid', '{product_id}')$
      </p>
      <div class="tags">
        $include('Product-GetProductTags', 'pid', '{product_id}')$
      </div>
'''
                            
                            content += '''
    </div>
    </div>
    <div class="box img-box">
      <img src="assets/images/top/img_dummy.gif?$staticlink$"
        data-echo="assets/images/s_article/''' + primary_product_id + '''.jpg?$staticlink$" 
        alt="''' + primary_alt + '''" class="img">
    </div>
  </div>
  <!-- アイテム ここまで -->
'''
                
                # divアイテムを処理（セクション内）
                for div_item in section.get('div_items', []):
                    content += self._generate_div_html(div_item)
                
                # 独立したpタグを処理（セクション内）
                for p_tag in section.get('p_tags', []):
                    p_text = p_tag.get('text', '')
                    text_link = p_tag.get('text_link', None)
                    
                    if text_link:
                        # テキストリンクが統合されている場合
                        url = text_link.get('url', '#')
                        link_text = text_link.get('text', '')
                        # pタグ内にテキストリンクを埋め込む
                        if url:
                            content += f'''
  <p class="text">{p_text}<a href="{url}" style="color:red;" target="_blank">{link_text}</a></p>
'''
                        else:
                            content += f'''
  <p class="text">{p_text}<a href="#" style="color:red;" target="_blank">{link_text}</a></p>
'''
                    else:
                        # 通常のpタグ
                        content += f'''
  <p class="text">{p_text}</p>
'''
                
                content += '''
  <!-- グレー線 ここから -->
  <hr class="gray s_article">
  <!-- グレー線 ここまで -->
'''
            
            # セクション外のdivアイテムを処理
            for div_item in parsed_data.get('div_items', []):
                content += self._generate_div_html(div_item)
            
            # セクション外の独立したpタグを処理
            for p_tag in parsed_data.get('standalone_p_tags', []):
                p_text = p_tag.get('text', '')
                text_link = p_tag.get('text_link', None)
                
                if text_link:
                    # テキストリンクが統合されている場合
                    url = text_link.get('url', '#')
                    link_text = text_link.get('text', '')
                    if url:
                        content += f'''
  <p class="text">{p_text}<a href="{url}" style="color:red;" target="_blank">{link_text}</a></p>
'''
                    else:
                        content += f'''
  <p class="text">{p_text}<a href="#" style="color:red;" target="_blank">{link_text}</a></p>
'''
                else:
                    # 通常のpタグ
                    content += f'''
  <p class="text">{p_text}</p>
'''
            
            # 固定日付
            date_str = datetime.now().strftime("%Y-%m-%dT10:00")
            date_display = datetime.now().strftime("%Y年%m月%d日 更新")
            
            # HTMLテンプレートに値を挿入
            h1_title = parsed_data.get('h1_title', parsed_data.get('title', ''))
            html_output = self.html_template
            html_output = html_output.replace('{h1_title}', h1_title)
            html_output = html_output.replace('{title}', parsed_data.get('title', ''))
            html_output = html_output.replace('{description}', parsed_data.get('description', ''))
            html_output = html_output.replace('{index_list}', index_list)
            html_output = html_output.replace('{content}', content)
            html_output = html_output.replace('{date}', date_str)
            html_output = html_output.replace('{date_display}', date_display)
            html_output = html_output.replace('{breadcrumb_text}', h1_title[:50] if h1_title else '')
            html_output = html_output.replace('{main_image}', 'J012547_main.jpg')  # デフォルト画像
            
            return html_output
            
        except Exception as e:
            st.error(f"HTML生成エラー: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
            return None
    
    def _generate_div_html(self, div_item):
        """divアイテムのHTMLを生成"""
        div_type = div_item.get('type', '')
        text = div_item.get('text', '')
        image_name = div_item.get('image_name', '')
        url = div_item.get('url', '')
        
        if div_type == 'ボタンリンク':
            # ボタンリンク
            return f'''
 <!-- ボタン ここから -->
  <div class="article_container_box_btn btn transparent-red">
    <a href="{url}" class="btn_link">{text}</a>
  </div>
  <!-- ボタン ここまで -->
'''
        elif div_type == 'テキストリンク':
            # テキストリンク
            if url:
                return f'''
  <a href="{url}" style="color:red;" target="_blank">{text}</a>
'''
            else:
                # URLがない場合でもテキストを表示
                return f'''
  <a href="#" style="color:red;" target="_blank">{text}</a>
'''
        elif div_type == '画像':
            # 画像
            alt_text = text if text else image_name
            return f'''
  <div class="article_container_box_img">
    <img src="assets/images/top/img_dummy.gif?$staticlink$" 
         data-echo="assets/images/s_article/{image_name}?$staticlink$" 
         alt="{alt_text}">
  </div>
'''
        else:
            # タイプが不明な場合
            return ''
    
    def _extract_product_id(self, url):
        """URLから商品IDを抽出"""
        if not url or url == 'nan':
            return 'dummy'
        
        # URLから商品IDを抽出（例: MM-0410771005508, MMV-4580435590216）
        # URL形式: https://isetan.mistore.jp/moodmark/product/MM-4582700706797.html
        match = re.search(r'MM[A-Z0-9]*-[\w-]+', url)
        if match:
            return match.group(0)
        return 'dummy'

def main():
    # サイドバーにナビゲーションを追加
    with st.sidebar:
        st.markdown("### 🔗 ダッシュボード")
        st.markdown("---")
        
        # 現在のページを強調表示
        st.markdown("**📄 コミュニティコンバーター**")
        st.markdown("（現在のページ）")
        st.markdown("")
        
        # 他のダッシュボードへのリンク
        st.markdown('[<div style="text-align: center;"><button style="background-color: #4CAF50; color: white; padding: 0.5rem 1rem; border: none; border-radius: 0.25rem; cursor: pointer; width: 100%;">📄 CSV to HTML コンバーター</button></div>](/)', unsafe_allow_html=True)
        st.markdown('[<div style="text-align: center;"><button style="background-color: #FF4B4B; color: white; padding: 0.5rem 1rem; border: none; border-radius: 0.25rem; cursor: pointer; width: 100%; margin-bottom: 0.5rem;">📊 GA4/GSC AI分析チャット</button></div>](analytics_chat)', unsafe_allow_html=True)
        st.markdown('[<div style="text-align: center;"><button style="background-color: #009688; color: white; padding: 0.5rem 1rem; border: none; border-radius: 0.25rem; cursor: pointer; width: 100%;">📦 記事掲載商品・在庫</button></div>](article_stock)', unsafe_allow_html=True)
        
        st.markdown("---")
    
    # 認証チェック
    if not check_authentication():
        login_page()
        return
    
    # Google Tag Manager - 親ウィンドウに動的に挿入
    gtm_script = """
    <script>
    (function() {
        var doc = window.parent.document;
        if (!doc.querySelector('script[src*="googletagmanager.com/gtm.js"]')) {
            (function(w,d,s,l,i){
                w[l]=w[l]||[];
                w[l].push({'gtm.start': new Date().getTime(),event:'gtm.js'});
                var f=d.getElementsByTagName(s)[0],
                j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';
                j.async=true;
                j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;
                f.parentNode.insertBefore(j,f);
            })(window.parent,doc,'script','dataLayer','GTM-KLXFVW7G');
            var noscript = doc.createElement('noscript');
            var iframe = doc.createElement('iframe');
            iframe.src = 'https://www.googletagmanager.com/ns.html?id=GTM-KLXFVW7G';
            iframe.height = '0';
            iframe.width = '0';
            iframe.style.display = 'none';
            iframe.style.visibility = 'hidden';
            noscript.appendChild(iframe);
            doc.body.insertBefore(noscript, doc.body.firstChild);
        }
    })();
    </script>
    """
    components.html(gtm_script, height=0)
    
    st.title("MOODMARK｜コミュニティコンバーター")
    st.markdown('<p style="font-size: 14px; color: #666; text-align: center; margin-top: -10px;">developed by Takeshi Nakamura</p>', unsafe_allow_html=True)
    st.markdown("---")
    
    # サイドバー
    with st.sidebar:
        st.header("📋 使用方法")
        st.markdown("""
        1. CSVファイルをアップロード
        2. cgidパラメータを設定
        3. プレビューで内容を確認
        4. HTMLをダウンロード
        
        **特徴:**
        - ランキングスライダーなし
        - 段落内スライダーなし
        - divタグ対応（ボタンリンク、テキストリンク、画像）
        - 商品枠の表示/非表示制御
        - 商品リンクの有効/無効制御
        """)
        
        st.header("⚙️ 設定")
        article_cgid = st.text_input(
            "記事の商品リンク用cgid",
            value="J012542",
            help="商品リンクに使用されるcgidパラメータ"
        )
        
        st.markdown("---")
        
        # ログアウトボタン
        st.header("🔐 アカウント")
        if st.session_state.get('username'):
            st.info(f"ログイン中: **{st.session_state.username}**")
        if st.button("🚪 ログアウト", type="secondary"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.rerun()
    
    # メインエリア
    converter = CommunityCSVToHTMLConverter(article_cgid=article_cgid)
    
    # ファイルアップロード
    uploaded_file = st.file_uploader(
        "CSVファイルをアップロードしてください",
        type=['csv'],
        help="コミュニティコンバーター用のCSVファイルを選択してください"
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
                    st.info(f"**説明:** {parsed_data['description'][:100]}..." if parsed_data['description'] else "**説明:** なし")
                    st.info(f"**セクション数:** {len(parsed_data['sections'])}")
                
                with col2:
                    st.subheader("🔧 HTML生成")
                    
                    if st.button("🚀 HTMLを生成", type="primary"):
                        with st.spinner("HTMLを生成中..."):
                            html_output = converter.generate_html(parsed_data)
                        
                        if html_output:
                            st.success("✅ HTML生成が完了しました！")
                            
                            # プレビュー表示の選択
                            preview_option = st.radio(
                                "プレビュー表示オプション:",
                                ["最初の1000文字", "最初の2000文字", "最初の5000文字", "完全表示"],
                                index=3,
                                horizontal=True
                            )
                            
                            # HTMLプレビュー
                            st.subheader("👀 HTMLプレビュー")
                            html_lines = len(html_output.splitlines())
                            st.info(f"📊 HTMLサイズ: {len(html_output):,} 文字, {html_lines:,} 行")
                            
                            if preview_option == "最初の1000文字":
                                preview_text = html_output[:1000] + "..." if len(html_output) > 1000 else html_output
                            elif preview_option == "最初の2000文字":
                                preview_text = html_output[:2000] + "..." if len(html_output) > 2000 else html_output
                            elif preview_option == "最初の5000文字":
                                preview_text = html_output[:5000] + "..." if len(html_output) > 5000 else html_output
                            else:
                                preview_text = html_output
                            
                            st.code(preview_text, language="html")
                            
                            # ダウンロードボタン
                            st.download_button(
                                label="📥 HTMLファイルをダウンロード",
                                data=html_output,
                                file_name=f"community_article_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
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
                                    if h4.get('display', True)
                                )
                                st.metric("商品数", total_products)
                            with col_c:
                                st.metric("HTMLサイズ", f"{len(html_output):,} 文字")
        
        except Exception as e:
            st.error(f"❌ エラーが発生しました: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
    
    else:
        # デモ表示
        st.subheader("🎯 デモ: サンプルCSVでHTML生成")
        st.info("CSVファイルをアップロードしてHTMLを生成してください。")

    render_likepass_footer()


if __name__ == "__main__":
    main()

