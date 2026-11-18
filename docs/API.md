# 统一聚合 API

平台把多个来源收敛到同一组端点。所有响应为 UTF-8 JSON，字段名使用 `snake_case`。

## 1. 启动

```bash
# 仓库根目录
PYTHONPATH=. python3 -m platform.cli serve --host 127.0.0.1 --port 8080
# 打开 http://127.0.0.1:8080
```

仅依赖 Python 标准库（3.10+），无第三方包。日常巡检也可走 CLI：

```bash
PYTHONPATH=. python3 -m platform.cli health
PYTHONPATH=. python3 -m platform.cli search 雾 --type drama
```

## 2. 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 服务导航页（HTML） |
| GET | `/health` | 服务状态 + 各来源状态汇总 |
| GET | `/sources` | 来源清单：adapter_id、支持类型、许可证、接入状态 |
| GET | `/search` | 多源检索，跨源合并去重后分页返回 |
| GET | `/detail` | 取详情 + 分集 / 分章节 |
| GET | `/resolve` | 解析播放 / 阅读地址 |

### `/search`

| 参数 | 必填 | 说明 |
|---|---|---|
| `q` | 是 | 关键词；空白会返回 `BAD_REQUEST` |
| `type` | 否 | `drama` / `video` / `novel` / `comic` |
| `page` | 否 | 从 1 开始，默认 1 |
| `sources` | 否 | 逗号分隔的 `adapter_id`；缺省为全部可用来源（不含 DISABLED） |

响应要点：

- `items[]` 每条是**跨源聚合后的作品**，`sources[]` 列出命中该作品的所有来源，`source_count` 为来源数；
- 主项取评分最高的来源，其字段直接展开在 `items[]` 元素上；
- `per_source[]` 给出每个来源的 `count` 与 `error`，单个来源失败不会影响整体结果；
- `degraded=true` 表示至少一个来源未返回数据（骨架来源会返回 `SOURCE_NOT_READY`）。

```json
{
  "query": "雾",
  "media_type": "drama",
  "page": 1,
  "page_size": 20,
  "total": 1,
  "degraded": true,
  "items": [
    {
      "source": "demo_catalog",
      "external_id": "demo-drama-001",
      "title": "雾港三封信",
      "media_type": "drama",
      "summary": "失去记忆的邮差在雾港逐封投递十年前的信……",
      "author": "演示编剧 A",
      "status": "完结",
      "rating": 8.6,
      "sources": [
        {"adapter_id": "demo_catalog", "display_name": "演示目录（自造数据）", "external_id": "demo-drama-001"}
      ],
      "source_count": 1
    }
  ],
  "per_source": [
    {"adapter_id": "demo_catalog", "status": "active", "count": 1, "error": null},
    {"adapter_id": "aquan_duanju", "status": "stub", "count": 0,
     "error": {"code": "SOURCE_NOT_READY", "message": "待实现：检索接口对接与结果归一化", "source": "aquan_duanju"}}
  ]
}
```

### `/detail`

| 参数 | 必填 | 说明 |
|---|---|---|
| `source` | 是 | 来源 `adapter_id` |
| `id` | 是 | 来源内 `external_id` |

返回 `{source, item, episodes[], chapters[]}`。

### `/resolve`

| 参数 | 必填 | 说明 |
|---|---|---|
| `source` / `id` | 是 | 同上 |
| `episode` 或 `chapter` | 否 | 分集 / 章节 ID；省略时解析整部 |

返回 `{url, media_type, quality, format, headers, expires_in_seconds, note, source, external_id, episode_or_chapter_id}`。

> `headers` 中只放必要的引用标识；真实令牌由服务端会话注入，不入库、不入仓库。

## 3. 错误码

| 错误码 | HTTP | 含义 | 客户端处理建议 |
|---|---|---|---|
| `BAD_REQUEST` | 400 | 参数缺失或非法 | 修正请求参数 |
| `NOT_FOUND` | 404 | 路由或内容不存在 | 提示未找到 |
| `SOURCE_DISABLED` | 403 | 来源未授权 / 闭源，已禁用 | 隐藏该来源入口 |
| `SOURCE_NOT_READY` | 409 | 骨架来源，上游尚未实现或授权未到 | 展示“暂未开放” |
| `RATE_LIMITED` | 429 | 触发上游频次限制 | 退避重试 |
| `UPSTREAM_ERROR` | 502 | 上游异常 | 可重试，勿透传内部错误 |
| `INTERNAL_ERROR` | 500 | 平台内部错误 | 记录 trace id 后反馈 |

错误响应统一形状：

```json
{"error": {"code": "SOURCE_DISABLED", "message": "来源 小果影视 未授权，已禁用……", "source": "xiaoguo_video"}}
```

服务端不返回上游原始堆栈、接口地址或凭证。

## 4. 来源接入状态对 API 的影响

| 状态 | 出现在 `/sources` | 参与 `/search` | `/detail` `/resolve` |
|---|---|---|---|
| `active` | 是 | 是 | 可用 |
| `stub` | 是 | 是（返回 `SOURCE_NOT_READY`） | 409 |
| `disabled` | 是 | 否（显式指定时记 `SOURCE_DISABLED`） | 403 |

## 5. 演示数据

`demo_catalog` 适配器读取 `platform/data/demo_catalog.json`，全部为仓库自造虚构条目（CC0-1.0），用于验证 `search → detail → resolve` 主链路。其 `resolve` 返回 `https://example.com/...` 占位地址，**不指向任何真实内容**。接入真实来源后应替换为上游授权地址。
