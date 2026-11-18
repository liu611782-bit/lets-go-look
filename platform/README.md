# platform/ — 聚合平台骨架

统一领域模型 + 来源适配器接口 + 各来源占位实现。当前不含真实接口调用，仅固化契约与合规边界。

## 目录

```
platform/
├── models.py              # 统一领域模型（MediaItem / Episode / Chapter / ResolvedSource ...）
└── adapters/
    ├── base.py            # SourceAdapter 抽象契约
    ├── aquan_duanju.py    # 阿圈短剧（Apache-2.0 上游，骨架）
    ├── iduanju.py         # i短剧（GPL-3.0 上游，骨架）
    ├── fanqie_novel.py    # 番茄小说下载器（许可证待确认，骨架）
    └── closed_apps.py     # 小果影视 / 笔趣阁（闭源，禁用占位）
```

## 适配器状态

| adapter_id | 来源 | 状态 | 说明 |
|---|---|---|---|
| `aquan_duanju` | 阿圈短剧 | STUB | 上游 Apache-2.0，可在保留 NOTICE 前提下对接公开接口 |
| `iduanju` | i短剧 | STUB | GPL-3.0，链接 / 衍生边界需先做合规复核 |
| `fanqie_novel` | 番茄小说下载器 | STUB | 上游未附 LICENSE，授权确认前不实现 |
| `xiaoguo_video` | 小果影视 | DISABLED | 闭源，未授权，禁止逆向接入 |
| `biquge_reader` | 笔趣阁 | DISABLED | 闭源 / 疑似重打包，禁止复用签名绕过逻辑 |

## 使用示例（骨架）

```python
from platform.adapters import ADAPTERS

adapter = ADAPTERS["aquan_duanju"]()
print(adapter.meta())
# search / detail / episodes / resolve 待按上游公开接口实现
```

## 下一步

1. 固化 `models.py` 字段，补齐前端需要的展示属性。
2. 选许可证清晰的来源（`aquan_duanju`）打通 `search → detail → resolve` 主链路。
3. 在聚合服务层做多源合并、去重、排序与统一错误码。
4. 其余来源按授权与许可证状态逐个开放；DISABLED 来源在授权前不得实现业务方法。

> 合规要求见 [`../docs/COMPLIANCE.md`](../docs/COMPLIANCE.md)，架构说明见 [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)。
