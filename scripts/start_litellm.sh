#!/usr/bin/env bash
set -e

# Load .env if present
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

echo "=========================================================="
echo "🚀 Khởi chạy LiteLLM Proxy (Groq -> Localhost:8000)"
echo "=========================================================="

if [ -z "$GROQ_API_KEY" ]; then
  echo "⚠️ CẢNH BÁO: Chưa tìm thấy biến GROQ_API_KEY trong file .env"
  echo "Vui lòng mở file .env và điền: GROQ_API_KEY=\"gsk_...\""
  echo ""
fi

# Chạy container LiteLLM qua Docker Compose Infra
docker compose -f docker-compose-infra.yaml up -d litellm

echo "✅ LiteLLM Proxy đang chạy tại: http://localhost:8000"
echo "   Endpoint tương thích OpenAI: http://localhost:8000/v1"
echo "   Model alias: 'localhost' -> groq/llama-3.3-70b-versatile"
echo ""
echo "Kiểm tra log: docker logs -f autoresearching-litellm"
