import streamlit as st
import pandas as pd
import asyncio
from lead_collector import collect_leads
import os
from datetime import datetime
import io
import subprocess
import traceback

# Page Config - フルワイド
st.set_page_config(page_title="営業リスト収集", page_icon="🚀", layout="wide")

# ==========================================
# 環境セットアップ (Streamlit Cloud対策)
# ==========================================
@st.cache_resource
def ensure_playwright_browsers():
    """Streamlit Cloud環境でPlaywrightのブラウザが不足している場合にインストールを試みる"""
    try:
        # ブラウザが起動できるか軽量なテスト
        import subprocess
        # st.info("Checking Playwright environment...")
        res = subprocess.run(["playwright", "install", "chromium"], capture_output=True, text=True)
        if res.returncode != 0:
            # alternative command
            subprocess.run(["python", "-m", "playwright", "install", "chromium"], capture_output=True)
        return True
    except Exception as e:
        st.error(f"Playwrightのセットアップ中にエラーが発生しました: {e}")
        return False

# 起動時に実行
if os.environ.get("STREAMLIT_RUNTIME_DEBUG") is None: # 通常のStreamlit環境
     ensure_playwright_browsers()

# Custom CSS - ミニマルUX & スティッキーヘッダー
st.markdown("""
<style>
    /* ベースカラー: 白基調 */
    .stApp {
        background: #ffffff;
        color: #1e293b;
    }
    
    /* ヘッダーなど余計な要素を非表示 */
    header[data-testid="stHeader"] { display: none; }
    footer { display: none; }
    .block-container { 
        padding-top: 0 !important; 
        padding-bottom: 2rem !important;
        max-width: 100% !important;
    }
    
    /* 
       スティッキーヘッダーの実装 
    */
    div[data-testid="stVerticalBlock"] > div:has(div.sticky-marker) {
        position: sticky;
        top: 0;
        z-index: 9999;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(12px);
        padding: 1rem 3% 0.5rem 3%;
        margin-top: 0;
        border-bottom: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    /* 入力フィールドのスタイル調整 (白背景用) */
    .stTextInput input, .stNumberInput input {
        background: #f8fafc !important;
        border: 1px solid #cbd5e1 !important;
        color: #334155 !important;
        border-radius: 6px !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #c53d43 !important;
        box-shadow: 0 0 0 2px rgba(197, 61, 67, 0.2) !important;
    }
    .stTextInput label, .stNumberInput label {
        color: #64748b !important;
    }
    
    /* ボタン */
    .stButton > button {
        background: linear-gradient(90deg, #c53d43 0%, #9b1c20 100%) !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
        box-shadow: 0 2px 4px rgba(197, 61, 67, 0.2);
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(197, 61, 67, 0.3);
    }
    
    /* ダウンロードボタン */
    .stDownloadButton > button {
        background: linear-gradient(90deg, #059669 0%, #047857 100%) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 2px 4px rgba(5, 150, 105, 0.2);
    }
    
    /* データフレーム */
    .stDataFrame {
        width: 100%;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
    }
    
    /* バッジなど */
    .list-info {
        display: flex;
        align-items: center;
        gap: 15px;
        margin: 20px 0 10px 0;
        padding: 0 2%;
        color: #334155;
    }
    .source-badge {
        font-size: 0.75rem;
        color: #64748b;
        background: #f1f5f9;
        padding: 2px 8px;
        border-radius: 4px;
        border: 1px solid #e2e8f0;
    }
    
    /* 続きを表示ボタン (少し控えめに) */
    .load-more-btn button {
        background: #f1f5f9 !important;
        color: #334155 !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: none !important;
    }
    .load-more-btn button:hover {
        background: #e2e8f0 !important;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if "leads_df" not in st.session_state:
    st.session_state.leads_df = None
if "visible_count" not in st.session_state:
    st.session_state.visible_count = 20

# ==========================================
# スティッキーヘッダーエリア
# ==========================================
with st.container():
    # このdivがあるコンテナがCSSでstickyになります
    st.markdown('<div class="sticky-marker"></div>', unsafe_allow_html=True)
    
    # 1段目: 検索条件
    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1.5])
    with col1:
        region = st.text_input("📍 地域", placeholder="例：京都市", key="region", label_visibility="collapsed")
    with col2:
        industry = st.text_input("🏢 業種", placeholder="例：印刷業", key="industry", label_visibility="collapsed")
    with col3:
        others = st.text_input("🔍 その他", placeholder="条件追加", key="others", label_visibility="collapsed")
    with col4:
        count = st.number_input("件数", min_value=1, max_value=300, value=20, label_visibility="collapsed")
    with col5:
        start_btn = st.button("🚀 収集開始", use_container_width=True)

    # 2段目: ダウンロードボタン（データがある時のみ）
    if st.session_state.leads_df is not None:
        df = st.session_state.leads_df
        # 少しマージンを空けて配置
        st.markdown('<div style="height: 5px;"></div>', unsafe_allow_html=True)
        
        d_col1, d_col2, d_spacer = st.columns([1, 1, 6])
        
        timestamp = datetime.now().strftime('%y%m%d_%H%M')
        base_filename = f"営業リスト_{timestamp}"
        
        with d_col1:
            excel_buffer = io.BytesIO()
            df.to_excel(excel_buffer, index=False, engine='openpyxl')
            excel_buffer.seek(0)
            st.download_button("📊 Excel", excel_buffer, f"{base_filename}.xlsx", 
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        
        with d_col2:
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📄 CSV", csv_data, f"{base_filename}.csv", "text/csv", use_container_width=True)


# ==========================================
# コンテンツエリア
# ==========================================

# 収集ロジック
if start_btn:
    if not region or not industry:
        st.warning("「地域」と「業種」を入力してください")
    else:
        try:
            keyword = f"{region} {industry} {others}".strip()
            
            progress_area = st.empty()
            
            def update_progress(current, total, status):
                pct = int((current / total) * 10 if total > 0 else 0)
                bar = "▓" * pct + "░" * (10 - pct)
                progress_area.info(f"【収集進行中】 {status}  [{bar}] {current}/{total if total > 0 else '?'}")
            
            results = asyncio.run(collect_leads(keyword, count, update_progress))
            progress_area.empty()
            
            if results:
                df = pd.DataFrame(results)
                # カラムの並び順を調整（ユーザー指定の順序：SNSの右横にWebカタログ）
                cols = ["業種", "企業名", "Webサイト", "電話番号", "問合せフォーム", "SNS", "Webカタログ", "住所", "備考", "収集日"]
                # 実際に存在するカラムだけで構成
                existing_cols = [c for c in cols if c in df.columns]
                rest_cols = [c for c in df.columns if c not in existing_cols]
                df = df[existing_cols + rest_cols]
                
                st.session_state.leads_df = df
                st.session_state.visible_count = 20 # リセット
                
                # 自動保存
                output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../02_output"))
                os.makedirs(output_dir, exist_ok=True)
                df.to_excel(os.path.join(output_dir, f"営業リスト_{datetime.now().strftime('%y%m%d_%H%M')}.xlsx"), index=False)
                
                st.rerun()
            else:
                st.error("おっと、情報が見つかりませんでした。条件を変えて試してみてください。")
        except Exception as e:
            progress_area.empty()
            st.error(f"❌ 収集中にエラーが発生しました")
            with st.expander("エラー詳細を表示"):
                st.code(traceback.format_exc())
            st.info("💡 ヒント: Streamlit Cloudの場合、一度アプリを再起動（Reboot）するとブラウザが正しくインストールされることがあります。")

# リスト表示
if st.session_state.leads_df is not None:
    df = st.session_state.leads_df
    total_count = len(df)
    
    # ページネーション用スライス
    current_visible = min(st.session_state.visible_count, total_count)
    display_df = df.iloc[:current_visible]
    
    st.markdown(f"""
    <div class="list-info">
        <h3 style="margin:0;">📦 収集済みリスト <span style="font-size:0.8em; color:#f87171; margin-left:10px;">{total_count}件中 {current_visible}件表示</span></h3>
        <span class="source-badge">情報源: Google Maps + Web解析</span>
    </div>
    """, unsafe_allow_html=True)
    
    # データフレーム表示
    # 高さ計算: ヘッダー35px + 1行35px換算
    # 20件なら 35 + 20*35 = 735px くらい
    calc_height = (len(display_df) * 35) + 38
    
    st.dataframe(
        display_df, 
        use_container_width=True, 
        hide_index=True, 
        height=calc_height,
        column_config={
            "Webサイト": st.column_config.LinkColumn(
                "Webサイト",
                help="クリックすると企業のWebサイトを別タブで開きます",
                validate="^https?://.+"
            )
        }
    )
    
    # 続きを表示ボタン
    if current_visible < total_count:
        # 中央寄せのためのカラム構成
        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            st.markdown('<div class="load-more-btn">', unsafe_allow_html=True)
            if st.button(f"⬇️ 続きを表示する ({total_count - current_visible}件)", use_container_width=True):
                st.session_state.visible_count += 20
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

else:
    # 初期画面
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.info("👆 上のフォーム条件を入力して「収集開始」を押してください。<br>Google MapsとWebサイト解析を行い、営業リストを自動作成します。")
