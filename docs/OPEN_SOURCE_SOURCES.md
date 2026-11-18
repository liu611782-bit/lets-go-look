# 同类开源来源补充目录（短剧 / 影视 / 小说阅读）

> 检索时间：2026-11-18。星标数与仓库状态会随时间变动，接入前以各仓库当前 `LICENSE` 与 README 为准。
> 本目录只记录公开可查的上游仓库、技术栈与许可证状态；不包含 APK 本体与反编译产物。

## 一、真果鉴 / 红果鉴 家族（短剧多站源客户端）

**背景**：Flutter + Go 多端独立短剧 / 影视客户端，原名「短剧库 APP」。编译选项决定应用名：红果鉴（仅红果站源）、真果鉴（全部站源）、蓝果鉴（仅蓝果）。站源请求、解析、下载与播放均在设备本地完成，不依赖自建服务器。上游 `applicationId = com.duanju.duanju_app`。

| 仓库 | 语言 / 栈 | 星标（检索时） | 许可证状态 | 备注 |
|---|---|---:|---|---|
| [kuoluoss/zhenguojian](https://github.com/kuoluoss/zhenguojian) | Dart/Flutter + Go | 276 | GPL-3.0（根目录 LICENSE） | 红果 / 真果 / 蓝果三版本；包名 `com.duanju.duanju_app` |
| [zhoufuweigg/guoapp](https://github.com/zhoufuweigg/guoapp) | Dart/Flutter + Go | 1976 | **根目录无 LICENSE**；README 声明源码来自原作者“鱼佬”，仅打包测试，随时可能删库 | 镜像 / 打包分发，授权状态需谨慎，按“保留所有权利”处理 |
| [enginJie/guoapp](https://github.com/enginJie/guoapp) | Dart/Flutter + Go | 146 | 待核 | 社区镜像，含 GitHub Actions 自动构建 |
| [czgyz/hongguo](https://github.com/czgyz/hongguo) | 待核 | 27 | 待核 | 标注支持 Android 6.0 |
| [xudahua520/guoapp](https://github.com/xudahua520/guoapp) | 待核 | 78 | 待核 | 源码镜像（Actions 构建） |

### 与本地 base.apk 的关系判定

本地 `base.apk`（小果影视，`com.yingshib.xg`，主 Activity `com.guoapp.MainActivity`）：

- 主 Activity 名 `com.guoapp.MainActivity` 与 guoapp 家族项目同名，技术栈同为 Flutter + FFmpeg，**外观上属于该家族的改名 / 二次打包分支**；
- 但其 `applicationId` 为 `com.yingshib.xg`，与上述上游的 `com.duanju.duanju_app` **不一致**，未在已核对上游中逐字匹配；
- 结论：**疑似家族重打包分支，源码归属与授权待确认**，在核对到对应上游分支前按闭源占位处理（见 `platform/adapters/closed_apps.py`）。

## 二、小说 / 漫画阅读客户端（开源）

| 仓库 | 平台 / 栈 | 星标（检索时） | 许可证状态 | 特点 |
|---|---|---:|---|---|
| [gedoor/legado](https://github.com/gedoor/legado) | Android / Kotlin（阅读 3.0） | — | 历史上为 GPL；**官方仓库源码已清空，仅余 README 与公告图**，下游 fork 可查 | Legado 书源生态源头；接入前需在下游 fork 中核对许可证 |
| [read-cat/read-cat](https://github.com/read-cat/read-cat) | Electron / TypeScript | 1029 | GPL-3.0 | 免费、简洁、无广告的小说阅读器 |
| [ssnangua/ColorTxt](https://github.com/ssnangua/ColorTxt) | Electron / TypeScript（桌面） | 2011 | MPL-2.0 | 本地 TXT/EPUB；章节识别、简繁互转、标注、词典、朗读、AI 阅读助手 |
| [akira399/sakura-read](https://github.com/akira399/sakura-read) | Flutter/Dart（Android） | 77 | LICENSE 见上游 | 二次元风格；TXT/EPUB + 阅读 3.0 书源 + 桌宠 |
| [radiumCN/inkwell](https://github.com/radiumCN/inkwell) | Kotlin / Compose（Android） | 42 | LICENSE 见上游 | 本地 txt/EPUB/MOBI + Legado 书源在线追更 + WebDAV 同步 |
| [FactorCitrus/Juyue](https://github.com/FactorCitrus/Juyue) | SwiftUI（iOS） | 37 | LICENSE / NOTICE 见上游 | 兼容 Legado 3.0 书源生态 |
| [bennytsai1234/Night-Reader](https://github.com/bennytsai1234/Night-Reader) | Flutter/Dart（Android/iOS） | 27 | LICENSE 见上游 | 兼容 Legado 书源；TXT、TTS 朗读、离线下载 |
| [Leon-Ning-san/HomuraReader](https://github.com/Leon-Ning-san/HomuraReader) | TypeScript（桌面 + Android） | 108 | LICENSE 见上游 | 本地 EPUB/KEPUB/PDF/MOBI/CBZ-ZIP/TXT/Markdown |

## 三、接入提示

- **书源生态**：多数阅读 App 兼容 Legado 3.0 书源规则；平台侧可抽象“书源规则适配层”，但必须遵守各站点版权、用户协议与频次限制。
- **Copyleft 义务**：GPL-3.0 具有传染性，MPL-2.0 为文件级 copyleft；与本平台代码的链接 / 隔离方式见 [COMPLIANCE.md](COMPLIANCE.md)，发布前建议法律复核。
- **无 LICENSE 镜像**：根目录未附 LICENSE 的 guoapp 镜像 / 改名包，在作者确认前按“保留所有权利”处理，不复制源码、不二次分发安装包。
- **内容版权**：短剧、影视、小说、漫画内容版权归原权利人；平台只做入口编排，不转存受版权保护的内容文件。
