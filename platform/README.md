# platform/ — 聚合服务

统一领域模型 + 来源适配器 + **可运行的聚合服务**（标准库 HTTP API / CLI）。
当前只有 `demo_catalog` 是 ACTIVE（仓库自造虚构数据），其余来源按授权状态占位。

## 目录

```
platform/
├── models.py              # 统一领域模型（MediaItem / Episode / Chapter / ResolvedSource ...）
├── errors.py              # 统一错误码与异常归一
├── registry.py            # 适配器注册表 + 实例缓存 + 状态筛选
├── aggregator.py          # 多源合并、跨源去重、排序、TTL 缓存、错误降级
├── serialization.py       # 领域模型 → JSON
├── server.py              # HTTP API（http.server，无第三方依赖）
├── cli.py                 # 命令行：sources / health / search / detail / resolve / serve
├── data/
│   └── demo_catalog.json  # 自造虚构演示目录（CC0-1.0）
└── adapters/
    ├── base.py            # SourceAdapter 抽象契约
    ├── demo_catalog.py    # 演示目录（ACTIVE，本地 JSON，无网络请求）
    ├── aquan_duanju.py    # 阿圈短剧（Apache-2.0 上游，骨架）
    ├── iduanju.py         # i短剧（GPL-3.0 上游，骨架）
    ├── fanqie_novel.py    # 番茄小说下载器（许可证待确认，骨架）
    ├── zhenguojian.py     # 真果鉴（GPL-3.0 主线，骨架）
    └── closed_apps.py     # 小果影视 / 笔趣阁（闭源，禁用占位）
```

## 快速运行

```bash
PYTHONPATH=. python3 -m platform.cli health           # 来源健康状态
PYTHONPATH=. python3 -m platform.cli search 雾         # 多源检索
PYTHONPATH=. python3 -m platform.cli serve --port 8080
PYTHONPATH=. python3 -m unittest discover -s tests -v # 22 项测试
```

接口细节见 [`../docs/API.md`](../docs/API.md)。

## 适配器状态

| adapter_id | 来源 | 状态 | 说明 |
|---|---|---|---|
| `demo_catalog` | 演示目录（自造） | ACTIVE | 本地虚构 JSON，用于验证主链路；`resolve` 返回占位地址 |
| `aquan_duanju` | 阿圈短剧 | STUB | 上游 Apache-2.0，可在保留 NOTICE 前提下对接公开接口 |
| `iduanju` | i短剧 | STUB | GPL-3.0，链接 / 衍生边界需先做合规复核 |
| `fanqie_novel` | 番茄小说下载器 | STUB | 上游未附 LICENSE，授权确认前不实现 |
| `zhenguojian` | 真果鉴 | STUB | 主线 GPL-3.0，家族镜像无 LICENSE，需先复核 |
| `xiaoguo_video` | 小果影视 | DISABLED | 闭源，未授权，禁止逆向接入 |
| `biquge_reader` | 笔趣阁 | DISABLED | 闭源 / 疑似重打包，禁止复用签名绕过逻辑 |

## 用代码调用

```python
from platform.aggregator import Aggregator
from platform.models import MediaType

agg = Aggregator()
outcome = agg.search("雾", media_type=MediaType.DRAMA)
print(outcome.total, [i.title for i in outcome.items])
detail = agg.detail("demo_catalog", "demo-drama-001")
print(detail["episodes"][0]["title"])
```

注册新来源：

```python
from platform.registry import default_registry
from platform.adapters.aquan_duanju import AquanDuanjuAdapter

default_registry.register("aquan_duanju_v2", AquanDuanjuAdapter)
```

## 实现约定

1. **逐源隔离**：任一适配器抛错只影响该源记录，不中断整体聚合；异常统一归一为平台错误码。
2. **授权门禁**：`DISABLED` 来源默认不参与检索，显式请求返回 `SOURCE_DISABLED`（HTTP 403）。
3. **去重规则**：按 `media_type + 标题归一化（全半角、标点、空白、大小写）` 聚类，主项取评分最高来源。
4. **缓存**：检索结果按 TTL（默认 60s）缓存，键含关键词、类型、分页与来源集合。
5. **不落敏感数据**：日志不记录查询内容以外的凭证；`ResolvedSource.headers` 不放真实令牌。

## 下一步

1. 选许可证清晰、接口公开的来源（`aquan_duanju`）打通真实 `search → detail → resolve`，替换骨架实现。
2. 增加统一 HTTP 客户端（超时、重试、限流、UA 策略）与按来源的频次配置。
3. 补书架 / 进度 / 历史（存本地或用户自有账号，不做跨源画像）。
4. 其余来源按授权与许可证状态逐个开放；DISABLED 来源在授权前不得实现业务方法。

> 合规要求见 [`../docs/COMPLIANCE.md`](../docs/COMPLIANCE.md)，架构说明见 [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)。
