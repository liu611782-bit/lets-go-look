"""前端页面与配置化接入通道的验证记录。

验收方式：把本仓库重新 clone 到干净目录，直接跑测试与启动服务，
确认「远端代码可运行」而不是仅「本地可运行」。

## 验收结果（2026-11-18）

- 干净 clone 后 `PYTHONPATH=. python3 -m unittest discover -s tests` → **41 项 OK**（4.0s）
- `git ls-files | grep pycache` → 0，确认缓存文件未入库
- 服务实测：`/` 200（15064 字节，web/index.html）、`/health` 200、`/search?q=雾` 命中 1 条
- 界面实测：搜索「雾」→ 卡片「雾港三封信」→ 详情抽屉 3 集 → 点击第一集解析出占位地址

## 界面

`web/index.html`，单文件、无第三方依赖、移动端优先：

- 顶部来源状态徽章：来源总数 / 可用 / 未就绪 / 未授权
- 搜索框 + 类型筛选（短剧 / 影视 / 小说）
- 结果卡片：标题、评分、简介、类型、作者、状态、命中来源标签
- 底部（≥760px 居中）详情抽屉：分集 / 章节点击解析
- `degraded` 折叠提示：哪些来源没返回数据、错误码是什么
- 所有输出走 `esc()` 转义；`Escape` 与遮罩点击可关闭抽屉

## 配置化接入

新增可配置来源不需要写 Python 代码：

1. 复制 `platform/config/sources.example.json` 到仓库外；
2. 填 `base_url` / `endpoints` / `fields`，`enabled` 置 `true`；
3. `LGL_SOURCES_CONFIG=<文件路径>` 启动。

运行时约束：域名白名单、仅 GET、超时与有限重试、最小请求间隔、凭证只从环境变量注入。
