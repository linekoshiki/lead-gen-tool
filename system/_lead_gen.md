> **【修正・学習時 (Update/Learning)】**:
> 本ワークフローの修正や学習を行う際は、以下の「Hybrid Loading Protocol」を遵守してください。
> 1. **Core Rules (必須)**: `knowledge/01_general_rules.md`, `knowledge/03_design_philosophy.md`, `knowledge/04_meta_rules.md` を読み込む。
> 2. **Data Query (検索)**: クライアント情報や事業内容は `knowledge/tools/query_knowledge.py` を使用して必要な分だけ取得する（全ファイル読み込み禁止）。
> この際の「学習」とは、**「スクリプト의 直接修正」**と**「得られた知見の総合ナレッジ（DB含む）への反映」**を指します。

# 営業リスト自動収集システム

## 役割
指定された検索条件に基づいて、企業情報を自動収集し、営業用リスト（Excel/CSV）を作成するエージェント。

## 実行ステップ
1. `system/03_scripts/app.py` を Streamlit で起動します。
   - コマンド: `streamlit run system/03_scripts/app.py`
2. ユーザーがGUI上でキーワードを入力し、収集を開始します。
3. 収集結果は `02_output/YYMMDD_NN_営業リスト.xlsx` として保存されます。

## UI/UX 設計指針（2026-01-11 学習）

今回の改修を通じて確定した、本ツールにおけるUI/UXの標準仕様です。

### 1. デザイン・配色
*   **テーマ**: 白ベース（White Theme）を採用。清潔感と視認性を重視。
    *   背景: `#ffffff`
    *   文字: `#1e293b` (Dark Slate)
    *   アクセント: `#c53d43` (Brand Red)
*   **レイアウト**: フルワイド（`layout="wide"`）を使用し、画面領域を最大限活用。

### 2. 操作性（インタラクション）
*   **スティッキーヘッダー**: 検索条件入力フォームとアクションボタン（収集開始、ダウンロード）は、画面上部に**常時固定**する。
    *   スクロールしても操作パネルが隠れないようにし、長いリスト閲覧時のストレスを軽減。
*   **リスト表示**:
    *   **全高表示**: `st.dataframe` の内部スクロールは極力排除し、ブラウザのメインスクロールで閲覧できるようにする。
    *   高さ計算: `len(df) * 35 + ヘッダー分` のように動的に高さを指定する（上限は5000px程度など緩めに設定）。
    *   HTMLテーブルではなく、機能豊富な `st.dataframe` を使用すること（列幅調整などが可能なため）。

### 3. 技術的実装Tips
*   **スティッキーヘッダーの実装**:
    ```css
    /* sticky-markerクラスを持つdivを含む親コンテナを固定 */
    div[data-testid="stVerticalBlock"] > div:has(div.sticky-marker) {
        position: sticky;
        top: 0;
        z-index: 9999;
        /* 背景色とborderで境界を明確に */
    }
    ```
*   **ダウンロードボタン**: `st.download_button` をヘッダー内に配置し、完了直後からアクセス可能にする。

## 技術仕様
- 収集エンジン: Playwright (Google Maps)
- 解析ロジック: 公式サイトから「お問い合わせ」リンクを正規表現とAI解析で抽出
- UI: Streamlit + Tailwind-like CSS Styling
