# APK 资产盘点明细

> 数据来源：对 7 个本地 APK 的 `AndroidManifest.xml`、签名证书、`classes*.dex` 字符串与原生库目录做静态解析。解析时间：2026-11-18。
> 体积口径：压缩 = APK 文件磁盘大小；解压 = zip 内全部 entries 未压缩长度之和。

## 体积总览

| 文件 | 压缩 (MB) | 解压 (MB) |
|---|---:|---:|
| base.apk | 33.66 | 78.48 |
| base_1.apk | 38.59 | 85.90 |
| base_2.apk | 40.26 | 89.98 |
| base_3.apk | 42.67 | 97.10 |
| base_4.apk | 24.33 | 44.39 |
| base_5.apk | 20.69 | 56.59 |
| base_6.apk | 21.47 | 29.39 |
| **合计** | **221.67** | **481.84** |

- 压缩包合计 **221.67 MB < 300 MB**
- 解压后合计 **481.84 MB > 300 MB**

---

## 1. base.apk — 小果影视

| 项 | 值 |
|---|---|
| 包名 | `com.yingshib.xg` |
| 版本 | 2.0.0（versionCode 2112） |
| min / target SDK | 24 / 36 |
| 主 Activity | `com.guoapp.MainActivity` |
| 签名主体 | CN=ked101099709c |
| 技术栈 | Flutter（`libapp.so`）+ FFmpeg（`libavcodec/avformat/avfilter/avutil/avdevice`）+ `libduanju_core.so`（约 24.9 MB，短剧核心原生库）+ `libffmpegkit` |

**权限**：`INTERNET`、`ACCESS_NETWORK_STATE`、`ACCESS_WIFI_STATE`、`WAKE_LOCK`、`POST_NOTIFICATIONS`、`FOREGROUND_SERVICE`、`FOREGROUND_SERVICE_DATA_SYNC`、`WRITE_EXTERNAL_STORAGE`、`RECEIVE_BOOT_COMPLETED`、自定义动态广播权限。

**备注**：DEX 字符串中未发现公开源码仓库地址；未检索到匹配的 GitHub 上游。归类为闭源二进制。

## 2–4. base_1 / base_2 / base_3.apk — 阿圈短剧（三个版本）

| 项 | base_1 | base_2 | base_3 |
|---|---|---|---|
| 包名 | `com.aquan.duanju` | `com.aquan.duanju` | `com.aquan.duanju` |
| 版本 | 1.11.12 (2074) | 1.12.4 (2082) | 1.12.11 (2092) |
| 压缩 / 解压 (MB) | 38.59 / 85.90 | 40.26 / 89.98 | 42.67 / 97.10 |
| min / target SDK | 24 / 36 | 24 / 36 | 24 / 36 |
| 主 Activity | `com.aquan.duanju.MainActivity` | 同左 | 同左 |
| 签名主体 | CN=Aquan Duanju, OU=Mobile, O=Aquan, L=Zhoushan, ST=Zhejiang, C=CN | 同左 | 同左 |

**技术栈（三者一致）**：Flutter/Dart（`libapp.so`、`libflutter.so`）+ libmpv（`libmpv.so`，约 12.37 MB）+ FFmpeg（`libffmpeg.so`，约 28.15 MB）+ QuickJS（`libqjs.so`、`libfastdev_quickjs_runtime.so`）+ `libaquan_core.so` + `libmediakitandroidhelper.so`。

**权限（三者一致）**：`INTERNET`、`ACCESS_NETWORK_STATE`、`WAKE_LOCK`、`FOREGROUND_SERVICE`、`FOREGROUND_SERVICE_MEDIA_PLAYBACK`、`FOREGROUND_SERVICE_MEDIA_PROJECTION`、`RECORD_AUDIO`、`REQUEST_INSTALL_PACKAGES`、`CHANGE_WIFI_MULTICAST_STATE`、`POST_NOTIFICATIONS`、自定义动态广播权限。

**备注**：上游仓库 `wjsqqj/aquan-duanju` 的 `applicationId` 与包名逐字一致（见 SOURCE_AUDIT.md），许可证 Apache-2.0。三个 APK 为同一应用的历史版本。

## 5. base_4.apk — 笔趣阁

| 项 | 值 |
|---|---|
| 包名 | `com.qsreod.bqgcjb` |
| 版本 | 5.0.1（versionCode 22） |
| min / target SDK | 26 / 37 |
| 主 Activity | `com.qingsong.read.app.MainActivity` |
| 签名主体 | C=CN（其余字段缺失） |
| 技术栈 | Kotlin / AndroidX（appcompat、constraintlayout、lifecycle、room、datastore） |

**权限（共 19 项，摘选）**：`INTERNET`、`ACCESS_NETWORK_STATE`、`ACCESS_WIFI_STATE`、`QUERY_ALL_PACKAGES`、`READ_PHONE_STATE`、`ACCESS_COARSE_LOCATION`、`VIBRATE`、`WRITE_EXTERNAL_STORAGE`、`MANAGE_EXTERNAL_STORAGE`、`REQUEST_INSTALL_PACKAGES`、`FOREGROUND_SERVICE_DATA_SYNC`、`AD_ID`、自定义动态广播权限。

**静态观察**：
- DEX 中出现追书神器搜索接口域名 `b02.zhuishushenqi.com`（模糊搜索 / 统计）。
- 集成友盟统计（`alogsus.umeng.com`、`aspect-upush.umeng.com`）与 AnyThink 广告 SDK（`adx.anythinktech.com`、`statisticslinks.com`）。
- DEX 字符串中出现 `L-JINBIN/ApkSignatureKillerEx`（签名绕过工具）引用，提示该包可能经过重打包 / 二次签名处理。
- 未检索到公开源码仓库。归类为闭源 / 疑似重打包，**不得复用其签名绕过逻辑**。

## 6. base_5.apk — i短剧

| 项 | 值 |
|---|---|
| 包名 | `app.iduanju` |
| 版本 | 1.5.10-android（versionCode 1510） |
| min / target SDK | 26 / 35 |
| 主 Activity | `app.iduanju.MainActivity` |
| 签名主体 | CN=iDuanJu, O=iDuanJu, C=CN |
| 技术栈 | Kotlin / Jetpack Compose + media3（ExoPlayer）+ QuickJS Android Wrapper（四 ABI）+ Rhino（MPL-2.0）+ HGCurrentPlayer（Apache-2.0） |

**权限（共 6 项）**：`INTERNET`、`ACCESS_NETWORK_STATE`、`FOREGROUND_SERVICE`、`FOREGROUND_SERVICE_MEDIA_PLAYBACK`、`REQUEST_INSTALL_PACKAGES`、自定义动态广播权限。

**备注**：DEX 中更新检查地址指向 `api.github.com/repos/my-name-is-alan/iDuanJu/releases`；上游仓库 `android/app/build.gradle.kts` 的 `applicationId = "app.iduanju"` 逐字一致，许可证 GPL-3.0。本地 APK（1.5.10）落后于上游（1.5.14-android）。

## 7. base_6.apk — 番茄小说下载器

| 项 | 值 |
|---|---|
| 包名 | `com.pofl.fanqienoveldownloader` |
| 版本 | 2026.11.13-536（versionCode 100827） |
| min / target SDK | 26 / 36 |
| 主 Activity | `com.pofl.fanqienoveldownloader.MainActivity` |
| 签名主体 | CN=POf-L, OU=Fanqie Novel Downloader, O=Fanqie, L=Shanghai, ST=Shanghai, C=CN |
| 技术栈 | Tauri（Rust 核心 `libfanqie_novel_downloader_tauri.so` + Web 前端），`assets/tauri.conf.json`、`THIRD_PARTY_LICENSES.html` |

**权限（共 8 项）**：`INTERNET`、`ACCESS_NETWORK_STATE`、`WAKE_LOCK`、`FOREGROUND_SERVICE`、`FOREGROUND_SERVICE_MEDIA_PLAYBACK`、`REQUEST_INSTALL_PACKAGES`、`POST_NOTIFICATIONS`、自定义动态广播权限。

**备注**：`tauri.conf.json` 内更新端点指向 `github.com/POf-L/Fanqie-novel-Downloader` Releases；上游仓库公开可读，但**根目录未附 LICENSE 文件**，复用 / 再分发前需向作者确认授权范围。
