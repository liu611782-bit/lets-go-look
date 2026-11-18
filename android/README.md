# android/ — 安卓壳（arm64-v8a）

把同一个聚合平台装进手机：`WebView` 加载 `web/index.html`，数据经 JS 桥 `LglBridge` 读取内置演示目录。**同一份前端代码**同时服务浏览器与 App，避免两套界面漂移。

## 两个产物

| 产物 | 体积 | 用途 |
|---|---|---|
| `dist/lets-go-look-arm64.apk` | 约 37 KB | 功能版：装完即用，界面 / 检索 / 详情 / 解析齐全 |
| `dist/lets-go-look-arm64-300mb.apk` | 约 332 MB | 体积版：功能完全相同，额外内置一段自造演示素材，使包体 ≥300MB |

两个包包名相同（`com.letsgolook.aggregator`），只能装其中一个。

## 构建

依赖：

- JDK 17（提供 `javac` / `keytool`）
- Android SDK：`build-tools;33.0.2`、`platforms;android-33`
- NDK 26.1（编译 arm64-v8a 的 ABI 标识库）

```bash
export ANDROID_SDK_ROOT=/path/to/android-sdk
export JAVA_HOME=/path/to/jdk17

bash android/build.sh                  # 功能版 → dist/lets-go-look-arm64.apk

bash android/make_media.sh             # 生成演示素材（约 332MB，ffmpeg 合成画面）
WITH_MEDIA=1 bash android/build.sh     # 体积版 → dist/lets-go-look-arm64-300mb.apk
```

构建链是手工的：`aapt2` 编译资源与清单 → `javac` → `d8` 转 dex → 塞入 APK → `zipalign` → `apksigner` 签名。不依赖 Gradle / AGP，因此不需要下载整套构建系统。

## 结构

```
android/
├── AndroidManifest.xml              # 包名 / SDK / 图标 / 单 Activity
├── build.sh                         # 手工打包脚本（8 步）
├── make_media.sh                    # 生成体积版用的演示素材
├── res/
│   ├── values/strings.xml
│   └── drawable/ic_launcher.xml     # 矢量图标，随源码入库，任意密度可缩放
├── jni/lglabi.c                     # ABI 标识库（只回报自身 ABI）
├── java/com/letsgolook/aggregator/
│   ├── MainActivity.java            # WebView 外壳 + 返回键处理
│   └── LglBridge.java               # health / sources / search / detail / resolve
└── assets/                          # 构建时生成，不入库
    ├── web/index.html               # 从 ../web/ 同步
    ├── data/demo_catalog.json       # 从 ../platform/data/ 同步
    └── demo_media/                  # 仅体积版存在
```

## ABI

包内 `lib/arm64-v8a/liblglabi.so` 由 NDK 交叉编译，`aapt2 dump badging` 因此显示：

```
native-code: 'arm64-v8a'
```

该库只做一件事：被加载时回报自身 ABI（`/health` 的 `native_abi` 字段）。业务代码是纯 Java，原生库缺失时自动降级为 `none`，不影响功能。

## 与 Web 端的一致性

`LglBridge` 的返回形状与 `docs/API.md` 完全一致：

- `search` 返回 `{query, media_type, page, page_size, total, degraded, items[], per_source[]}`；
- `detail` 返回 `{source, item, episodes[], chapters[]}`；
- `resolve` 返回 `{url, media_type, quality, format, headers, expires_in_seconds, note, ...}`；
- 失败返回 `{"error":{"code","message","source"}}`，错误码与 HTTP 端相同。

因此 `web/index.html` 里的 `api()` 只需要一个分支：有 `window.LGLNative` 走桥，否则走 `fetch`。

## 限制

- **未在真机 / 模拟器上运行**：构建环境没有 Android 设备。已验证的是清单、ABI、签名（v2 + v3）、assets 内容、dex 类数量、前端脚本语法，以及 Bridge 逻辑与 Python 端逐条对照。
- 签名使用演示密钥（`android/keys/`，已被 `.gitignore` 排除），**不可用于发布**；正式发布请换自己的 keystore 并走 `apksigner`。
- 体积版的 332MB 全部来自 `assets/demo_media/pressure_test_1080p60.mp4`（ffmpeg `testsrc2` 合成画面，CC0），与业务代码无关；功能版的 37KB 才是代码与资源真实体积。
