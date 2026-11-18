# lets-go-look

多源影视 / 短剧 / 小说聚合平台：对一批 Android 安装包（APK）做资产盘点、上游开源源码核对，并实现一个可本地运行的统一聚合服务（领域模型 + 来源适配器 + HTTP API）。

> **仓库边界**
>
> - 本仓库**不包含**任何 APK 安装包本体（7 个 APK 压缩后合计约 221.67 MB）。
> - 本仓库**不包含**对闭源应用的反编译代码、smali/dex 还原产物或从二进制中提取的专有源码。
> - 仓库内唯一的内容数据 `platform/data/demo_catalog.json` 为**自行编写的虚构演示条目**（CC0-1.0），不含真实作品或受版权保护的内容。
> - 仅保留：清单元数据、公开可查的上游仓库链接、许可证核对记录、平台架构文档、接口契约与骨架代码。
> - 接入某个上游时，只能使用其公开 / 已授权的后端接口；闭源应用在取得授权前不得逆向提取接口或资源。

## 资产盘点速览

| # | 本地文件 | 应用名 | 包名 | 版本 | 压缩体积 | 技术栈 | 上游仓库 | 开源状态 |
|---|---|---|---|---|---|---|---|---|
| 1 | base.apk | 小果影视 | `com.yingshib.xg` | 2.0.0 (2112) | 33.66 MB | Flutter + FFmpeg + `libduanju_core.so` | 疑似 guoapp / 真果鉴家族重打包分支，未逐字匹配 | 归属待确认，按闭源占位 |
| 2 | base_1.apk | 阿圈短剧 | `com.aquan.duanju` | 1.11.12 (2074) | 38.59 MB | Flutter/Dart + libmpv + FFmpeg + QuickJS | [wjsqqj/aquan-duanju](https://github.com/wjsqqj/aquan-duanju) | 开源（Apache-2.0，旧版本） |
| 3 | base_2.apk | 阿圈短剧 | `com.aquan.duanju` | 1.12.4 (2082) | 40.26 MB | 同上 | [wjsqqj/aquan-duanju](https://github.com/wjsqqj/aquan-duanju) | 开源（Apache-2.0，中间版本） |
| 4 | base_3.apk | 阿圈短剧 | `com.aquan.duanju` | 1.12.11 (2092) | 42.67 MB | 同上 | [wjsqqj/aquan-duanju](https://github.com/wjsqqj/aquan-duanju) | 开源（Apache-2.0，新版本） |
| 5 | base_4.apk | 笔趣阁 | `com.qsreod.bqgcjb` | 5.0.1 (22) | 24.33 MB | Kotlin/AndroidX + Room + DataStore | 未检索到公开源码仓库 | 闭源 / 疑似重打包（见审计记录） |
| 6 | base_5.apk | i短剧 | `app.iduanju` | 1.5.10-android (1510) | 20.69 MB | Kotlin/Compose + media3 + QuickJS | [my-name-is-alan/iDuanJu](https://github.com/my-name-is-alan/iDuanJu) | 开源（GPL-3.0，APK 为旧版） |
| 7 | base_6.apk | 番茄小说下载器 | `com.pofl.fanqienoveldownloader` | 2026.11.13-536 | 21.47 MB | Tauri（Rust 核心 + Web 前端） | [POf-L/Fanqie-novel-Downloader](https://github.com/POf-L/Fanqie-novel-Downloader) | 公开源码；根目录无 LICENSE，授权待确认 |

## 体积与 300MB 对比

| 口径 | 合计体积 | 对比 300MB |
|---|---|---|
| APK 压缩包（磁盘占用） | **221.67 MB** | **小于** 300MB |
| 解压后（全部 entries 之和） | **481.84 MB** | **大于** 300MB |

> 结论：7 个安装包作为压缩包整体小于 300MB；一旦全部解压展开，体积超过 300MB。明细见 [docs/INVENTORY.md](docs/INVENTORY.md)。

## 本地运行

```bash
PYTHONPATH=. python3 -m platform.cli health            # 来源接入状态
PYTHONPATH=. python3 -m platform.cli search 雾         # 多源检索（合并去重）
PYTHONPATH=. python3 -m platform.cli serve --port 8080 # 启动统一 HTTP API
PYTHONPATH=. python3 -m unittest discover -s tests -v  # 22 项测试
```

仅依赖 Python 标准库。`demo_catalog` 来源是仓库自造虚构数据（CC0-1.0），用于跑通全链路；真实来源按授权状态逐步开放。接口见 [docs/API.md](docs/API.md)。

## 补充：同类开源来源

真果鉴 / 红果鉴家族（短剧多站源客户端）与其他开源小说 / 漫画阅读器的仓库、技术栈与许可证目录，见 [docs/OPEN_SOURCE_SOURCES.md](docs/OPEN_SOURCE_SOURCES.md)。

## 目录结构

```
lets-go-look/
├── README.md                     # 本文件：速览与边界声明
├── docs/
│   ├── INVENTORY.md              # 逐包元数据、权限、原生库与体积明细
│   ├── SOURCE_AUDIT.md           # 上游开源仓库核对方法、证据与结论
│   ├── ARCHITECTURE.md           # 统一聚合平台架构与适配器契约
│   ├── API.md                    # 统一聚合 API 契约与错误码
│   ├── COMPLIANCE.md             # 许可证、再分发与内容版权边界
│   └── OPEN_SOURCE_SOURCES.md    # 真果鉴家族与同类开源阅读软件目录
├── platform/
│   ├── README.md                 # 聚合服务说明与下一步
│   ├── models.py                 # 统一领域数据模型
│   ├── errors.py                 # 统一错误码
│   ├── registry.py               # 适配器注册表
│   ├── aggregator.py             # 多源合并 / 去重 / 排序 / 降级
│   ├── serialization.py          # 领域模型 → JSON
│   ├── server.py                 # HTTP API（标准库）
│   ├── cli.py                    # 命令行入口
│   ├── data/
│   │   └── demo_catalog.json     # 自造演示数据（CC0-1.0）
│   └── adapters/
│       ├── base.py               # 适配器抽象接口
│       ├── demo_catalog.py       # 演示目录适配器（ACTIVE）
│       ├── aquan_duanju.py       # 阿圈短剧适配器（Apache-2.0 上游）
│       ├── iduanju.py            # i短剧适配器（GPL-3.0 上游）
│       ├── fanqie_novel.py       # 番茄小说下载器适配器（授权待确认）
│       ├── zhenguojian.py        # 真果鉴适配器（GPL-3.0 主线，骨架）
│       └── closed_apps.py        # 闭源应用占位（未授权，禁止逆向接入）
└── tests/
    └── test_platform.py          # 注册表 / 聚合 / HTTP 接口测试
```

## 重要概念澄清

**APK 是安装好的客户端二进制，本身不能作为“API 接口”接入数据。**
聚合平台接入某个来源时，对接的是该来源**后端公开 / 已授权的 HTTP 接口**；APK 只作为识别应用包名、版本、技术栈和参考交互逻辑的样本。详见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。
