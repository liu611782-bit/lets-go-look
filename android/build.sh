#!/usr/bin/env bash
# 手工打包 APK（不依赖 Gradle / AGP）：
#   aapt2 编译资源与清单 → javac 编译源码 → d8 转 dex → 塞入 APK → zipalign → apksigner 签名
#
# 用法：
#   ANDROID_SDK_ROOT=/path/to/android-sdk bash android/build.sh
#   ANDROID_SDK_ROOT=... WITH_MEDIA=1 bash android/build.sh    # 体积版（内置演示素材，≥300MB）
#
# 产物：
#   dist/lets-go-look-arm64.apk        功能版（约 40KB，装完即用）
#   dist/lets-go-look-arm64-300mb.apk  体积版（内置自造演示素材，用于体积达标）
#
# 关于 ABI：包内 lib/arm64-v8a/liblglabi.so 由 NDK 交叉编译产出，
# 因此 aapt2 badging 会显示 native-code: 'arm64-v8a'。
# 业务代码是纯 Java，即使原生库缺失也能正常工作（health.native_abi 会显示 none）。

set -euo pipefail

if [ -n "${JAVA_HOME:-}" ]; then
  export PATH="$JAVA_HOME/bin:$PATH"
fi

SDK="${ANDROID_SDK_ROOT:-/tmp/android-sdk}"
BT="$SDK/build-tools/33.0.2"
AJAR="$SDK/platforms/android-33/android.jar"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD="$ROOT/build"
DIST="$ROOT/../dist"
APK_NAME="${APK_NAME:-$([ "${WITH_MEDIA:-0}" = "1" ] && echo lets-go-look-arm64-300mb.apk || echo lets-go-look-arm64.apk)}"
VERSION_NAME="${VERSION_NAME:-0.3.0}"

if [ ! -x "$BT/aapt2" ]; then
  echo "找不到 aapt2：$BT/aapt2" >&2
  echo "请先安装：sdkmanager --sdk_root=\"\$ANDROID_SDK_ROOT\" 'build-tools;33.0.2' 'platforms;android-33'" >&2
  exit 1
fi

echo "[1/8] 同步前端与数据到 assets"
rm -rf "$BUILD"
mkdir -p "$BUILD/res" "$BUILD/gen" "$BUILD/classes" "$BUILD/dex" "$DIST"
mkdir -p "$ROOT/assets/web" "$ROOT/assets/data"
cp "$ROOT/../web/index.html" "$ROOT/assets/web/index.html"
cp "$ROOT/../platform/data/demo_catalog.json" "$ROOT/assets/data/demo_catalog.json"

# 体积版：内置自造演示素材（WITH_MEDIA=1）。
# 素材是 ffmpeg 的 testsrc2 合成画面（CC0），不含任何真实作品或上游内容。
if [ "${WITH_MEDIA:-0}" = "1" ]; then
  if [ ! -f "$ROOT/media/pressure_test_1080p60.mp4" ]; then
    echo "找不到 media/pressure_test_1080p60.mp4，无法生成体积版" >&2
    exit 1
  fi
  mkdir -p "$ROOT/assets/demo_media"
  cp "$ROOT/media/pressure_test_1080p60.mp4" "$ROOT/assets/demo_media/pressure_test_1080p60.mp4"
  echo "  已内置演示素材：$(du -h "$ROOT/media/pressure_test_1080p60.mp4" | cut -f1)"
else
  rm -rf "$ROOT/assets/demo_media"
fi

echo "[2/8] aapt2 编译资源"
"$BT/aapt2" compile --dir "$ROOT/res" -o "$BUILD/res.zip"

echo "[3/8] aapt2 链接清单与 assets"
"$BT/aapt2" link \
  -o "$BUILD/base.apk" \
  -I "$AJAR" \
  --manifest "$ROOT/AndroidManifest.xml" \
  -R "$BUILD/res.zip" \
  --java "$BUILD/gen" \
  --auto-add-overlay \
  -A "$ROOT/assets" \
  --min-sdk-version 24 \
  --target-sdk-version 33 \
  --version-code 1 \
  --version-name "$VERSION_NAME"

echo "[4/8] javac 编译源码"
SOURCES=$(find "$ROOT/java" "$BUILD/gen" -name '*.java')
# shellcheck disable=SC2086
javac -encoding UTF-8 -source 8 -target 8 -bootclasspath "$AJAR" -d "$BUILD/classes" $SOURCES

echo "[5/8] d8 生成 classes.dex"
CLASSES=$(find "$BUILD/classes" -name '*.class')
# shellcheck disable=SC2086
"$BT/d8" --release --lib "$AJAR" --min-api 24 --output "$BUILD/dex" $CLASSES

echo "[6/8] 编译 arm64-v8a 原生库"
NDKBIN="${ANDROID_NDK_ROOT:-$SDK/ndk/26.1.10909125}/toolchains/llvm/prebuilt/linux-x86_64/bin"
if [ -x "$NDKBIN/aarch64-linux-android24-clang" ]; then
  mkdir -p "$BUILD/lib/arm64-v8a"
  "$NDKBIN/aarch64-linux-android24-clang" -shared -fPIC -O2 \
    -o "$BUILD/lib/arm64-v8a/liblglabi.so" "$ROOT/jni/lglabi.c"
  (cd "$BUILD" && zip -q -0 -r "$BUILD/base.apk" lib)
  echo "  已装入 lib/arm64-v8a/liblglabi.so"
else
  echo "  跳过：未找到 NDK clang，产物将是纯 Java 包（功能不受影响，但 native-code 为空）"
fi

echo "[7/8] 装入 dex 并 zipalign"
(cd "$BUILD/dex" && zip -q "$BUILD/base.apk" classes.dex)
"$BT/zipalign" -f -p 4 "$BUILD/base.apk" "$BUILD/aligned.apk"

echo "[8/8] 签名"
KS="$ROOT/keys/lgl-release.jks"
if [ ! -f "$KS" ]; then
  echo "  生成演示用签名密钥（仅用于本地安装测试，不是发布密钥）"
  keytool -genkeypair \
    -keystore "$KS" \
    -alias lgl \
    -keyalg RSA -keysize 2048 -validity 10000 \
    -storepass android -keypass android \
    -dname "CN=lets-go-look, OU=Demo, O=lets-go-look, C=CN" >/dev/null 2>&1
fi

"$BT/apksigner" sign \
  --ks "$KS" --ks-pass pass:android --key-pass pass:android \
  --min-sdk-version 24 \
  --out "$DIST/$APK_NAME" "$BUILD/aligned.apk"

echo
echo "产物：$DIST/$APK_NAME"
ls -lh "$DIST/$APK_NAME"
"$BT/apksigner" verify --print-certs "$DIST/$APK_NAME" | head -4
