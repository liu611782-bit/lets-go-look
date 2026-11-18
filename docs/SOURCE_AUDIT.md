# 上游开源源码核对记录

## 核对方法

1. 从 APK 的 `AndroidManifest.xml` 读取包名、版本、主 Activity 与权限。
2. 从 DEX / 配置文件字符串中提取更新检查地址、官网域名、第三方库链接。
3. 在 GitHub 按包名、应用名、签名组织名检索公开仓库。
4. 对候选仓库读取其 Android 构建配置（`build.gradle.kts` / `build.gradle`），核对 `applicationId` / `namespace` 是否与 APK 包名逐字一致；一致才判定为同一上游。
5. 读取上游 `LICENSE` / `README` 记录许可证状态。

> 说明：本记录只核对“是否存在公开上游源码仓库”，不代表对上游代码做了逐行审计。

## 逐包结论

### 已核对到上游（包名一致）

| APK | 上游仓库 | 核对证据 | 许可证 |
|---|---|---|---|
| base_1 / base_2 / base_3.apk（阿圈短剧） | [wjsqqj/aquan-duanju](https://github.com/wjsqqj/aquan-duanju) | 上游 `android/app/build.gradle.kts`：`namespace = "com.aquan.duanju"`、`applicationId = "com.aquan.duanju"`，与 APK 包名一致；README 应用名“阿圈短剧”一致；Flutter/Dart + libmpv + FFmpeg + QuickJS 技术栈与原生库目录吻合 | Apache-2.0（上游 `LICENSE`） |
| base_5.apk（i短剧） | [my-name-is-alan/iDuanJu](https://github.com/my-name-is-alan/iDuanJu) | DEX 更新端点 `api.github.com/repos/my-name-is-alan/iDuanJu/releases`；上游 `android/app/build.gradle.kts`：`namespace = "app.iduanju"`、`applicationId = "app.iduanju"`，与 APK 包名一致；仓库含 `android/` 目录 | GPL-3.0（上游 `LICENSE`） |
| base_6.apk（番茄小说下载器） | [POf-L/Fanqie-novel-Downloader](https://github.com/POf-L/Fanqie-novel-Downloader) | `assets/tauri.conf.json` 的 `identifier = "com.pofl.fanqienoveldownloader"`，更新端点指向该仓库 Releases；产品名 `Fanqie Novel Downloader` / “番茄小说下载器”一致 | **根目录无 LICENSE 文件**；README 仅附免责声明，授权范围需向作者确认 |

### 未核对到公开上游

| APK | 检索情况 | 归类 |
|---|---|---|
| base.apk（小果影视 `com.yingshib.xg`） | 主 Activity 为 `com.guoapp.MainActivity`，与 guoapp / 真果鉴家族同名，技术栈同为 Flutter + FFmpeg；但 `applicationId` 与已核对上游 `com.duanju.duanju_app` 不一致，未逐字匹配到对应分支 | 疑似家族改名 / 二次打包分支，归属待确认；核对到上游前按闭源占位 |
| base_4.apk（笔趣阁 `com.qsreod.bqgcjb`） | 按包名、应用名、`com.qingsong.read` 等标识检索无匹配仓库；DEX 内含签名绕过工具引用与广告 / 统计 SDK | 闭源 / 疑似重打包 |

## 版本对应关系

- 阿圈短剧：本地三个 APK（1.11.12 / 1.12.4 / 1.12.11）为同一上游的历史版本；接入时应以上游最新主干为准，不要直接复用旧包内资源。
- i短剧：本地 APK 为 1.5.10-android，上游构建配置显示 1.5.14-android；存在版本差。
- 番茄小说下载器：本地包版本 `2026.11.13-536`，上游 Releases 持续更新。

## 补充核对：真果鉴家族与同类阅读软件

首轮盘点后补充检索的短剧家族与开源阅读器目录，见 [OPEN_SOURCE_SOURCES.md](OPEN_SOURCE_SOURCES.md)，要点：

- 真果鉴 / 红果鉴（guoapp 家族）主线仓库 `kuoluoss/zhenguojian`，GPL-3.0，包名 `com.duanju.duanju_app`；另有多个无 LICENSE 的社区镜像。
- 同类开源阅读客户端：Legado（官方源码已清空，下游 fork 可查）、read-cat（GPL-3.0）、ColorTxt（MPL-2.0）、sakura-read、inkwell、Juyue、Night-Reader、HomuraReader 等。

## 风险与待办

- [ ] 番茄小说下载器：向上游作者确认许可证 / 再分发条款后，再决定平台内复用方式。
- [ ] 小果影视、笔趣阁：在未取得源码授权或公开 API 授权前，平台侧仅保留“来源占位”，不做接口逆向。
- [ ] 所有上游接口接入前，复核其 README / 免责声明中关于使用范围、频次与版权的约定。
