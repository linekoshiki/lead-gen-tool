#!/bin/bash
# =============================================================================
# 営業リスト自動収集システム - 社内共有サーバー起動スクリプト
# =============================================================================
# このスクリプトを実行すると、同じ社内ネットワーク（LAN）に接続している
# Windows/Mac/スマートフォンなど、どのデバイスからでもブラウザでアクセス可能になります。
# =============================================================================

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🚀 営業リスト自動収集システム - 社内共有モード${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# IPアドレスを取得
IP_ADDRESS=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)

if [ -z "$IP_ADDRESS" ]; then
    echo -e "${RED}⚠️  ネットワーク接続を確認できませんでした${NC}"
    echo "   Wi-Fiまたは有線LANに接続しているか確認してください。"
    exit 1
fi

PORT=8501

echo -e "${BLUE}📡 サーバー情報${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "   ${YELLOW}🔗 社内共有URL:${NC}"
echo ""
echo -e "   ${GREEN}➜  http://${IP_ADDRESS}:${PORT}${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${BLUE}📋 使い方${NC}"
echo "  1. このURLをSlack、メール、チャットで社内メンバーに共有"
echo "  2. 同じネットワーク内のPC（Windows/Macどちらでも可）で"
echo "     ブラウザ（Chrome、Edge等）を開き、上記URLにアクセス"
echo ""
echo -e "${YELLOW}⚠️  注意事項${NC}"
echo "  - このMacの電源を切る、またはこのターミナルを閉じると"
echo "    サーバーが停止し、アクセスできなくなります"
echo "  - 同じWi-Fi/LANに接続しているデバイスのみアクセス可能"
echo "  - 終了するには Ctrl+C を押してください"
echo ""
echo -e "${GREEN}🚀 サーバーを起動しています...${NC}"
echo ""

# スクリプトのディレクトリに移動
cd "$(dirname "$0")/system/03_scripts"

# Streamlitをネットワーク公開モードで起動
streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT} --server.headless=true
