#!/usr/bin/env bash
# 生成体积版用的演示素材（ffmpeg 合成画面，CC0）。
# 输出：android/media/pressure_test_1080p60.mp4（约 332MB，1080p60，45 秒，62Mbps）
#
# 这段素材只用于把安装包推到 300MB 以上（验证下载 / 安装 / 存储压力），
# 不含任何真实影视内容，也不参与业务逻辑。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$ROOT/media/pressure_test_1080p60.mp4"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "需要 ffmpeg" >&2
  exit 1
fi

mkdir -p "$ROOT/media"
ffmpeg -hide_banner -loglevel error -y \
  -f lavfi -i "testsrc2=size=1920x1080:rate=60" \
  -t 45 -c:v libx264 -preset ultrafast -b:v 62M -pix_fmt yuv420p \
  "$OUT"

ls -lh "$OUT"
echo "素材已生成：$OUT"
