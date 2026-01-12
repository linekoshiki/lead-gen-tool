#!/usr/bin/env python3
"""
lead_collector.py
Google Mapsから企業情報をスクレイピングし、Webサイトを解析して詳細情報を収集するコアエンジン。
"""
import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import datetime
import re
from urllib.parse import urlparse

async def analyze_website(page, url):
    """
    Webサイトを訪問してSNSリンクや各種フォーム、Webカタログの有無を確認する
    """
    info = {
        "sns": [],
        "has_form": False,
        "catalog_types": set(),
        "remarks": []
    }
    
    if not url or url == "なし":
        return info

    try:
        # タイムアウト付きでアクセス
        await page.goto(url, timeout=15000, wait_until="domcontentloaded")
        
        # ページ内の全リンクを取得
        links = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('a')).map(a => {
                return { href: a.href, text: a.innerText };
            });
        }''')
        
        # SNS検知 (略)
        sns_domains = {
            "twitter.com": "Twitter",
            "x.com": "X",
            "facebook.com": "Facebook",
            "instagram.com": "Instagram",
            "youtube.com": "YouTube",
            "linkedin.com": "LinkedIn",
            "line.me": "LINE"
        }
        
        found_sns = set()
        for link_obj in links:
            link = link_obj["href"]
            for domain, name in sns_domains.items():
                if domain in link and name not in found_sns:
                    found_sns.add(name)
        info["sns"] = list(found_sns)
        
        # フォーム検知 (略)
        content = await page.content()
        form_keywords = ['contact', 'inquiry', 'form', 'お問い合わせ', 'お問合せ', '相談', '申込']
        
        if any(k in url.lower() for k in form_keywords):
            info["has_form"] = True
        elif "<form" in content.lower():
             if "submit" in content.lower() or "送信" in content:
                 info["has_form"] = True
        else:
            for link_obj in links:
                if any(k in link_obj["href"].lower() or k in link_obj["text"].lower() for k in form_keywords):
                    info["has_form"] = True
                    break

        # Webカタログ検知 (詳細化)
        catalog_keywords = ['catalog', 'catalogue', 'カタログ', '電子カタログ', 'デジタルカタログ', '冊子']
        for link_obj in links:
            l_href = link_obj["href"].lower()
            l_text = link_obj["text"].lower()
            
            if any(k in l_href or k in l_text for k in catalog_keywords):
                # PDF判定
                if ".pdf" in l_href:
                    info["catalog_types"].add("PDF")
                # 電子book判定 (book, viewer, ebook, digital-bookなどのキーワード)
                elif any(k in l_href for k in ["book", "viewer", "ebook", "digital"]) or any(k in l_text for k in ["電子", "デジタル"]):
                    info["catalog_types"].add("book")
                # その他カタログキーワードはあるが形式不明な場合も一応チェック
                elif any(k in l_text for k in catalog_keywords):
                    # テキストに「電子」が含まれていれば電子book、そうでなければ一旦カタログとして扱うが
                    # ユーザー指定の「PDF」か「book」に寄せる
                    if "電子" in l_text or "デジタル" in l_text:
                        info["catalog_types"].add("book")
                    else:
                        # 判定がつかない場合はPDFか電子bookのどちらかであれば良いが
                        # 多くの場合は電子bookビューワーへの誘導なので「book」寄り
                        info["catalog_types"].add("book")
                    
    except Exception as e:
        info["remarks"].append(f"Webサイト解析エラー: {str(e)[:50]}")
    
    return info

async def collect_leads(keyword, max_results=20, progress_callback=None):
    """
    Google Mapsから企業情報を収集 + Webサイト解析
    """
    leads = []
    
    def report_progress(current, total, status):
        if progress_callback:
            progress_callback(current, total, status)
    
    async with async_playwright() as p:
        report_progress(0, max_results, "🌐 ブラウザを起動中... (Web解析モード)")
        if max_results > 50:
            # 大量取得時はヘッドレス推奨
            browser = await p.chromium.launch(headless=True)
        else:
             # 少量ならデバッグしやすいように見える場合もあるが、安定性のためTrue
            browser = await p.chromium.launch(headless=True)
            
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Google Mapsを開いて検索
        report_progress(0, max_results, f"🔍 Google Mapsで「{keyword}」を検索中...")
        await page.goto(f"https://www.google.com/maps/search/{keyword}")
        
        try:
            await page.wait_for_selector('a.hfpxzc', timeout=10000)
        except:
            report_progress(0, max_results, "❌ 結果が見つかりませんでした")
            return []

        # スクロール処理
        report_progress(0, max_results, "📜 リスト読み込み中...")
        scroll_attempts = 0
        while len(await page.query_selector_all('a.hfpxzc')) < max_results and scroll_attempts < 15:
            feed = await page.query_selector('div[role="feed"]')
            if feed:
                await page.evaluate('(el) => el.scrollBy(0, 5000)', feed)
            else:
                await page.mouse.wheel(0, 5000)
            await asyncio.sleep(2)
            scroll_attempts += 1
            
        articles = await page.query_selector_all('a.hfpxzc')
        total_to_process = min(len(articles), max_results)
        report_progress(0, total_to_process, f"✅ {total_to_process}件の候補を取得。詳細解析を開始します...")

        # 解析用ページ（タブ）を作成して並行処理っぽくする手もあるが、今回は直列で確実に
        analysis_page = await context.new_page()

        for i, article in enumerate(articles[:total_to_process]):
            try:
                name = await article.get_attribute("aria-label")
                report_progress(i + 1, total_to_process, f"🏢 [{i+1}/{total_to_process}] {name} の基本情報を取得中...")
                
                # 詳細取得クリック
                await article.click()
                await asyncio.sleep(1.5)
                
                # --- 基本情報取得 ---
                # 業種 (カテゴリ)
                industry_elem = await page.query_selector('button.DkEaL')
                industry = await industry_elem.inner_text() if industry_elem else "不明"
                
                # 住所
                address_elem = await page.query_selector('button[data-item-id="address"]')
                address = await address_elem.get_attribute("aria-label") if address_elem else "不明"
                address = address.replace("住所: ", "").strip()

                # 電話
                phone_elem = await page.query_selector('button[data-item-id^="phone:tel:"]')
                phone = await phone_elem.get_attribute("aria-label") if phone_elem else "不明"
                phone = phone.replace("電話番号: ", "").strip()
                
                # Webサイト
                website_elem = await page.query_selector('a[data-item-id="authority"]')
                website = await website_elem.get_attribute("href") if website_elem else "なし"
                
                # --- Webサイト詳細解析 ---
                web_info = {"sns": [], "has_form": False, "catalog_types": set(), "remarks": []}
                if website != "なし":
                    report_progress(i + 1, total_to_process, f"🌍 {name} のWebサイトを解析中...")
                    web_info = await analyze_website(analysis_page, website)
                
                # Webカタログの表示テキスト作成
                catalog_text = "なし/不明"
                if web_info["catalog_types"]:
                    catalog_text = ", ".join(sorted(list(web_info["catalog_types"])))

                leads.append({
                    "企業名": name,
                    "業種": industry,
                    "住所": address,
                    "電話番号": phone,
                    "Webサイト": website,
                    "問合せフォーム": "あり" if web_info["has_form"] else "なし/不明",
                    "SNS": ", ".join(web_info["sns"]) if web_info["sns"] else "なし",
                    "Webカタログ": catalog_text,
                    "備考": " ".join(web_info["remarks"]),
                    "収集日": datetime.datetime.now().strftime("%Y-%m-%d")
                })
                
            except Exception as e:
                report_progress(i + 1, total_to_process, f"⚠️ エラー発生: {str(e)[:20]}...スキップします")
                continue

        await analysis_page.close()
        await browser.close()
        
        report_progress(len(leads), len(leads), "🎉 全件の収集と解析が完了しました！")
        
    return leads

if __name__ == "__main__":
    # テスト用
    res = asyncio.run(collect_leads("京都市 司法書士", max_results=3))
    print(res)
