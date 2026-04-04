#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== 一键部署 DSA ==="

# 1. 构建并启动
echo "[1/2] docker compose build + up ..."
docker compose -f docker/docker-compose.yml up -d --build

# 2. 等待健康检查
echo "[2/2] 等待服务就绪 ..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "✓ 后端服务就绪"
    break
  fi
  sleep 2
done

if curl -sf http://localhost:80 > /dev/null 2>&1; then
  echo "✓ Nginx 就绪 — 访问 http://localhost"
else
  echo "⚠ Nginx 未响应，请检查日志: docker compose -f docker/docker-compose.yml logs nginx"
fi

echo "=== 部署完成 ==="
