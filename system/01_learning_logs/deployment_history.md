# Deployment Learning Log: Lead Generation Tool

## 2026/01/12: Web Deployment Strategy
- **Platform**: Streamlit Community Cloud
- **Repository**: [linekoshiki/lead-gen-tool](https://github.com/linekoshiki/lead-gen-tool.git)
- **Main Script**: `system/03_scripts/app.py`
- **Key Configuration**:
    - `requirements.txt` に `playwright` を追記してデプロイを安定化。
    - `.gitignore` に `02_output/` を追加し、ローカルの出力データがWebへ送信されないよう保護。
- **Update Command**:
    ```bash
    git add . && git commit -m "Update message" && git push
    ```
- **Credentials**: "No expiration" トークンを `git remote set-url` で設定済み。
