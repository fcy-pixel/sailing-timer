#!/bin/bash
# start_https.sh — 自動產生自簽憑證並以 HTTPS 啟動 Streamlit
# 用途：讓 iOS Safari 也能使用相機（手機需接受憑證）

set -e
cd "$(dirname "$0")"

CERT=ssl_cert.pem
KEY=ssl_key.pem

if [ ! -f "$CERT" ] || [ ! -f "$KEY" ]; then
  echo "🔐 產生自簽 SSL 憑證…"
  openssl req -x509 -newkey rsa:4096 \
    -keyout "$KEY" -out "$CERT" \
    -days 365 -nodes \
    -subj "/CN=sailing-timer"
  echo "✅ 憑證已產生：$CERT / $KEY"
fi

LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "未知")

echo ""
echo "========================================================"
echo "  🚀 以 HTTPS 啟動風帆車計時系統"
echo "  手機網址：https://${LOCAL_IP}:8504"
echo ""
echo "  ⚠️  首次開啟時瀏覽器會顯示「不安全」警告"
echo "  Android Chrome：點「進階」→「繼續前往」即可"
echo "  iOS Safari：點「顯示詳細資訊」→「繼續瀏覽」"
echo "========================================================"
echo ""

python3 -m streamlit run app.py \
  --server.port 8504 \
  --server.sslCertFile "$CERT" \
  --server.sslKeyFile "$KEY" \
  --server.headless true
