package com.letsgolook.aggregator;

import android.content.Context;
import android.webkit.JavascriptInterface;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.Charset;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;

/**
 * JS ↔ Java 桥：把 HTTP API 的形状原样暴露给内置页面。
 *
 * 路由：health / sources / search / detail / resolve
 * 返回：JSON 字符串；失败时返回 {"error":{"code","message","source"}}
 *
 * 当前只有 demo_catalog（内置虚构目录）是 active；其余来源为 stub 或 disabled，
 * 行为与 Python 端 platform/ 完全一致：stub 返回 SOURCE_NOT_READY，disabled 返回
 * SOURCE_DISABLED 且绝不发起任何请求。
 */
public class LglBridge {

    private static final String ADAPTER_ID = "demo_catalog";
    private static final int PAGE_SIZE = 20;

    /** 可选的原生库：只为确认 ABI 归属，缺失时不影响任何功能。 */
    private static final boolean NATIVE_LOADED;
    private static native String nativeAbi();

    static {
        boolean loaded;
        try {
            System.loadLibrary("lglabi");
            loaded = true;
        } catch (Throwable ignored) {
            loaded = false;
        }
        NATIVE_LOADED = loaded;
    }

    private final Context context;
    private JSONObject catalogCache;

    public LglBridge(Context context) {
        this.context = context.getApplicationContext();
    }

    // ------------------------------------------------------------ 来源清单

    private static final class Src {
        final String id;
        final String name;
        final String[] types;
        final String status;
        final String license;
        final String repo;
        final String note;

        Src(String id, String name, String[] types, String status,
            String license, String repo, String note) {
            this.id = id;
            this.name = name;
            this.types = types;
            this.status = status;
            this.license = license;
            this.repo = repo;
            this.note = note;
        }
    }

    private static final List<Src> SOURCES = buildSources();

    private static List<Src> buildSources() {
        List<Src> list = new ArrayList<Src>();
        list.add(new Src("demo_catalog", "演示目录（自造数据）",
                new String[]{"drama", "video", "novel"}, "active", "CC0-1.0", null,
                "虚构演示数据，仅用于验证聚合主链路；不接入任何真实上游。"));
        list.add(new Src("aquan_duanju", "阿圈短剧",
                new String[]{"drama", "video"}, "stub", "Apache-2.0",
                "https://github.com/wjsqqj/aquan-duanju",
                "待实现：检索接口对接与结果归一化"));
        list.add(new Src("iduanju", "i短剧",
                new String[]{"drama", "video"}, "stub", "GPL-3.0",
                "https://github.com/my-name-is-alan/iDuanJu",
                "待实现：检索接口对接与结果归一化"));
        list.add(new Src("fanqie_novel", "番茄小说下载器",
                new String[]{"novel"}, "stub", "授权待确认",
                "https://github.com/POf-L/Fanqie-novel-Downloader",
                "待实现：检索接口对接与结果归一化"));
        list.add(new Src("zhenguojian", "真果鉴",
                new String[]{"drama", "video"}, "stub", "GPL-3.0",
                "https://github.com/kuoluoss/zhenguojian",
                "待实现：检索接口对接与结果归一化"));
        list.add(new Src("xiaoguo_video", "小果影视",
                new String[]{"drama", "video"}, "disabled", "闭源", null,
                "未授权，已禁用；不提供检索 / 详情 / 解析"));
        list.add(new Src("biquge_reader", "笔趣阁",
                new String[]{"novel", "comic"}, "disabled", "闭源", null,
                "未授权，已禁用；不提供检索 / 详情 / 解析"));
        return Collections.unmodifiableList(list);
    }

    // ------------------------------------------------------------ 错误类型

    private static final class LglError extends Exception {
        final String code;
        final String source;

        LglError(String code, String message, String source) {
            super(message);
            this.code = code;
            this.source = source;
        }
    }

    private static String errorJson(String code, String message, String source) {
        try {
            JSONObject error = new JSONObject();
            error.put("code", code);
            error.put("message", message);
            if (source != null && !source.isEmpty()) {
                error.put("source", source);
            }
            JSONObject root = new JSONObject();
            root.put("error", error);
            return root.toString();
        } catch (JSONException e) {
            return "{\"error\":{\"code\":\"INTERNAL_ERROR\",\"message\":\"错误序列化失败\"}}";
        }
    }

    // ------------------------------------------------------------ JS 入口

    @JavascriptInterface
    public String hasDemoMedia() {
        InputStream input = null;
        try {
            input = context.getAssets().open("demo_media/pressure_test_1080p60.mp4");
            return "1";
        } catch (IOException e) {
            return "0";
        } finally {
            if (input != null) {
                try {
                    input.close();
                } catch (IOException ignored) {
                    // 关闭失败不影响结果
                }
            }
        }
    }

    @JavascriptInterface
    public String request(String route, String q, String type, String page,
                          String sourcesCsv, String source, String id, String episode) {
        try {
            String key = route == null ? "" : route.trim();
            if ("health".equals(key)) {
                return health().toString();
            }
            if ("sources".equals(key)) {
                JSONObject root = new JSONObject();
                root.put("sources", sourceList());
                return root.toString();
            }
            if ("search".equals(key)) {
                return search(q, type, parsePage(page), sourcesCsv).toString();
            }
            if ("detail".equals(key)) {
                return detail(source, id).toString();
            }
            if ("resolve".equals(key)) {
                return resolve(source, id, episode).toString();
            }
            throw new LglError("NOT_FOUND", "未定义的路由：" + key, null);
        } catch (LglError e) {
            return errorJson(e.code, e.getMessage(), e.source);
        } catch (JSONException e) {
            return errorJson("INTERNAL_ERROR", "服务内部错误", null);
        } catch (RuntimeException e) {
            return errorJson("INTERNAL_ERROR", "服务内部错误", null);
        }
    }

    // ------------------------------------------------------------ health / sources

    private JSONObject health() throws JSONException {
        JSONObject root = new JSONObject();
        root.put("status", "ok");
        root.put("source_count", SOURCES.size());
        JSONObject byStatus = new JSONObject();
        byStatus.put("active", countStatus("active"));
        byStatus.put("stub", countStatus("stub"));
        byStatus.put("disabled", countStatus("disabled"));
        root.put("by_status", byStatus);
        root.put("sources", sourceList());
        root.put("native_abi", NATIVE_LOADED ? nativeAbi() : "none");
        root.put("disclaimer", "DISABLED 来源未授权，不会发起任何请求；STUB 来源返回 SOURCE_NOT_READY。");
        return root;
    }

    private int countStatus(String status) {
        int n = 0;
        for (Src s : SOURCES) {
            if (status.equals(s.status)) {
                n++;
            }
        }
        return n;
    }

    private JSONArray sourceList() throws JSONException {
        JSONArray array = new JSONArray();
        for (Src s : SOURCES) {
            array.put(metaJson(s));
        }
        return array;
    }

    private JSONObject metaJson(Src s) throws JSONException {
        JSONObject meta = new JSONObject();
        meta.put("adapter_id", s.id);
        meta.put("display_name", s.name);
        JSONArray types = new JSONArray();
        for (String t : s.types) {
            types.put(t);
        }
        meta.put("media_types", types);
        meta.put("status", s.status);
        meta.put("upstream_repo", s.repo == null ? JSONObject.NULL : s.repo);
        meta.put("license", s.license);
        meta.put("note", s.note);
        meta.put("ready", "active".equals(s.status));
        return meta;
    }

    // ------------------------------------------------------------ search

    private JSONObject search(String q, String type, int page, String sourcesCsv) throws LglError {
        if (q == null || q.trim().isEmpty()) {
            throw new LglError("BAD_REQUEST", "缺少查询参数 q", null);
        }
        if (page < 1) {
            throw new LglError("BAD_REQUEST", "page 需为大于 0 的整数", null);
        }
        String mediaType = (type == null || type.trim().isEmpty()) ? null : type.trim();
        if (mediaType != null && !isValidType(mediaType)) {
            throw new LglError("BAD_REQUEST", "不支持的 type：" + mediaType, null);
        }

        List<Src> selected = selectedSources(sourcesCsv);
        List<JSONObject> collected = new ArrayList<JSONObject>();

        try {
            JSONArray perSource = new JSONArray();
            for (Src s : selected) {
                if ("disabled".equals(s.status)) {
                    perSource.put(sourceRecord(s, 0, errorObject("SOURCE_DISABLED", "来源未授权，已禁用", s.id)));
                    continue;
                }
                if (!ADAPTER_ID.equals(s.id)) {
                    perSource.put(sourceRecord(s, 0,
                            errorObject("SOURCE_NOT_READY", "待实现：检索接口对接与结果归一化", s.id)));
                    continue;
                }
                List<JSONObject> items = demoSearch(q.trim(), mediaType, page);
                collected.addAll(items);
                perSource.put(sourceRecord(s, items.size(), null));
            }

            boolean degraded = false;
            for (int i = 0; i < perSource.length(); i++) {
                JSONObject record = perSource.getJSONObject(i);
                if (!record.isNull("error")) {
                    degraded = true;
                }
            }

            JSONArray merged = merge(collected);
            JSONObject root = new JSONObject();
            root.put("query", q.trim());
            root.put("media_type", mediaType == null ? JSONObject.NULL : mediaType);
            root.put("page", page);
            root.put("page_size", PAGE_SIZE);
            root.put("total", merged.length());
            root.put("degraded", degraded);
            root.put("items", merged);
            root.put("per_source", perSource);
            return root;
        } catch (JSONException e) {
            throw new LglError("INTERNAL_ERROR", "检索结果序列化失败", null);
        }
    }

    private boolean isValidType(String type) {
        return "drama".equals(type) || "video".equals(type)
                || "novel".equals(type) || "comic".equals(type);
    }

    private List<Src> selectedSources(String sourcesCsv) throws LglError {
        List<Src> selected = new ArrayList<Src>();
        if (sourcesCsv == null || sourcesCsv.trim().isEmpty()) {
            for (Src s : SOURCES) {
                if (!"disabled".equals(s.status)) {
                    selected.add(s);
                }
            }
            return selected;
        }
        String[] parts = sourcesCsv.split(",");
        for (String part : parts) {
            String id = part.trim();
            if (id.isEmpty()) {
                continue;
            }
            Src found = findSource(id);
            if (found == null) {
                throw new LglError("BAD_REQUEST", "未知来源：" + id, null);
            }
            selected.add(found);
        }
        return selected;
    }

    private Src findSource(String id) {
        for (Src s : SOURCES) {
            if (s.id.equals(id)) {
                return s;
            }
        }
        return null;
    }

    private JSONObject sourceRecord(Src s, int count, JSONObject error) throws JSONException {
        JSONObject record = new JSONObject();
        record.put("adapter_id", s.id);
        record.put("display_name", s.name);
        record.put("status", s.status);
        record.put("count", count);
        record.put("error", error == null ? JSONObject.NULL : error);
        return record;
    }

    private JSONObject errorObject(String code, String message, String source) throws JSONException {
        JSONObject error = new JSONObject();
        error.put("code", code);
        error.put("message", message);
        if (source != null) {
            error.put("source", source);
        }
        return error;
    }

    private List<JSONObject> demoSearch(String needleRaw, String mediaType, int page) throws LglError {
        try {
            String needle = needleRaw.toLowerCase();
            JSONArray items = catalog().getJSONArray("items");
            List<JSONObject> matched = new ArrayList<JSONObject>();
            for (int i = 0; i < items.length(); i++) {
                JSONObject raw = items.getJSONObject(i);
                if (mediaType != null && !mediaType.equals(raw.optString("media_type"))) {
                    continue;
                }
                String haystack = (raw.optString("title") + " "
                        + raw.optString("author") + " "
                        + raw.optString("summary")).toLowerCase();
                if (haystack.contains(needle)) {
                    matched.add(itemJson(raw));
                }
            }
            Collections.sort(matched, new Comparator<JSONObject>() {
                @Override
                public int compare(JSONObject a, JSONObject b) {
                    double ra = a.optDouble("rating", 0.0);
                    double rb = b.optDouble("rating", 0.0);
                    if (rb != ra) {
                        return rb > ra ? 1 : -1;
                    }
                    return a.optString("title").compareTo(b.optString("title"));
                }
            });
            int start = (page - 1) * PAGE_SIZE;
            if (start >= matched.size()) {
                return new ArrayList<JSONObject>();
            }
            return new ArrayList<JSONObject>(matched.subList(start, Math.min(start + PAGE_SIZE, matched.size())));
        } catch (JSONException e) {
            throw new LglError("INTERNAL_ERROR", "内置演示目录读取失败", null);
        }
    }

    private JSONObject itemJson(JSONObject raw) throws JSONException {
        JSONObject item = new JSONObject();
        item.put("source", ADAPTER_ID);
        item.put("external_id", raw.getString("id"));
        item.put("title", raw.getString("title"));
        item.put("media_type", raw.getString("media_type"));
        item.put("cover_url", JSONObject.NULL);
        item.put("summary", raw.optString("summary", ""));
        item.put("author", raw.optString("author", ""));
        item.put("status", raw.optString("status", ""));
        if (raw.has("rating") && !raw.isNull("rating")) {
            item.put("rating", raw.optDouble("rating"));
        } else {
            item.put("rating", JSONObject.NULL);
        }
        return item;
    }

    private JSONArray merge(List<JSONObject> collected) throws JSONException {
        LinkedHashMap<String, JSONObject> buckets = new LinkedHashMap<String, JSONObject>();
        for (JSONObject item : collected) {
            String key = item.optString("media_type") + ":" + normalizeTitle(item.optString("title"));
            JSONObject bucket = buckets.get(key);
            if (bucket == null) {
                bucket = new JSONObject();
                bucket.put("primary", item);
                bucket.put("refs", new JSONArray());
                buckets.put(key, bucket);
            } else {
                JSONObject primary = bucket.getJSONObject("primary");
                if (item.optDouble("rating", 0.0) > primary.optDouble("rating", 0.0)) {
                    bucket.put("primary", item);
                }
            }
            JSONObject ref = new JSONObject();
            ref.put("adapter_id", item.optString("source"));
            ref.put("display_name", displayNameOf(item.optString("source")));
            ref.put("external_id", item.optString("external_id"));
            bucket.getJSONArray("refs").put(ref);
        }

        List<JSONObject> merged = new ArrayList<JSONObject>();
        for (JSONObject bucket : buckets.values()) {
            JSONObject primary = bucket.getJSONObject("primary");
            JSONObject out = new JSONObject(primary.toString());
            JSONArray refs = bucket.getJSONArray("refs");
            List<JSONObject> refList = new ArrayList<JSONObject>();
            for (int i = 0; i < refs.length(); i++) {
                refList.add(refs.getJSONObject(i));
            }
            Collections.sort(refList, new Comparator<JSONObject>() {
                @Override
                public int compare(JSONObject a, JSONObject b) {
                    return a.optString("adapter_id").compareTo(b.optString("adapter_id"));
                }
            });
            JSONArray sorted = new JSONArray();
            for (JSONObject ref : refList) {
                sorted.put(ref);
            }
            out.put("sources", sorted);
            out.put("source_count", sorted.length());
            merged.add(out);
        }

        Collections.sort(merged, new Comparator<JSONObject>() {
            @Override
            public int compare(JSONObject a, JSONObject b) {
                double ra = a.optDouble("rating", 0.0);
                double rb = b.optDouble("rating", 0.0);
                if (rb != ra) {
                    return rb > ra ? 1 : -1;
                }
                int sa = a.optInt("source_count", 0);
                int sb = b.optInt("source_count", 0);
                if (sb != sa) {
                    return sb - sa;
                }
                return a.optString("title").compareTo(b.optString("title"));
            }
        });

        JSONArray array = new JSONArray();
        for (JSONObject item : merged) {
            array.put(item);
        }
        return array;
    }

    private String displayNameOf(String adapterId) {
        Src s = findSource(adapterId);
        return s == null ? adapterId : s.name;
    }

    // ------------------------------------------------------------ detail / resolve

    private JSONObject detail(String source, String id) throws LglError {
        JSONObject raw = requireItem(source, id);
        try {
            JSONObject root = new JSONObject();
            root.put("source", source);
            root.put("item", itemJson(raw));
            root.put("episodes", episodesJson(raw));
            root.put("chapters", chaptersJson(raw));
            return root;
        } catch (JSONException e) {
            throw new LglError("INTERNAL_ERROR", "详情序列化失败", source);
        }
    }

    private JSONObject resolve(String source, String id, String episode) throws LglError {
        JSONObject raw = requireItem(source, id);
        String segment = (episode == null || episode.trim().isEmpty()) ? "full" : episode.trim();
        if (!"full".equals(segment) && !segmentExists(raw, segment)) {
            throw new LglError("NOT_FOUND", "分集 / 章节不存在：" + segment, source);
        }
        try {
            String mediaType = raw.optString("media_type");
            String format = ("drama".equals(mediaType) || "video".equals(mediaType)) ? "m3u8" : "txt";
            JSONObject root = new JSONObject();
            root.put("url", "https://example.com/demo-media/" + id + "/" + segment + "." + format);
            root.put("media_type", mediaType);
            root.put("quality", "m3u8".equals(format) ? "demo" : JSONObject.NULL);
            root.put("format", format);
            root.put("headers", new JSONObject());
            root.put("expires_in_seconds", 0);
            root.put("note", "演示占位地址，不指向任何真实内容；接入真实来源时由适配器返回上游授权地址。");
            root.put("source", source);
            root.put("external_id", id);
            root.put("episode_or_chapter_id", "full".equals(segment) ? JSONObject.NULL : segment);
            return root;
        } catch (JSONException e) {
            throw new LglError("INTERNAL_ERROR", "解析结果序列化失败", source);
        }
    }

    private JSONObject requireItem(String source, String id) throws LglError {
        if (source == null || source.trim().isEmpty() || id == null || id.trim().isEmpty()) {
            throw new LglError("BAD_REQUEST", "source 与 id 均为必填", null);
        }
        Src src = findSource(source);
        if (src == null) {
            throw new LglError("NOT_FOUND", "未知来源：" + source, null);
        }
        if ("disabled".equals(src.status)) {
            throw new LglError("SOURCE_DISABLED", "来源 " + src.name + " 未授权，已禁用；不提供检索 / 详情 / 解析", source);
        }
        if (!ADAPTER_ID.equals(source)) {
            throw new LglError("SOURCE_NOT_READY", "待实现：检索接口对接与结果归一化", source);
        }
        JSONObject raw = findItem(id);
        if (raw == null) {
            throw new LglError("NOT_FOUND", "演示目录中不存在：" + id, source);
        }
        return raw;
    }

    private JSONObject findItem(String id) throws LglError {
        try {
            JSONArray items = catalog().getJSONArray("items");
            for (int i = 0; i < items.length(); i++) {
                JSONObject raw = items.getJSONObject(i);
                if (id.equals(raw.optString("id"))) {
                    return raw;
                }
            }
            return null;
        } catch (JSONException e) {
            throw new LglError("INTERNAL_ERROR", "内置演示目录读取失败", null);
        }
    }

    private boolean segmentExists(JSONObject raw, String segment) {
        JSONArray episodes = raw.optJSONArray("episodes");
        if (episodes != null) {
            for (int i = 0; i < episodes.length(); i++) {
                JSONObject ep = episodes.optJSONObject(i);
                if (ep != null && segment.equals(ep.optString("id"))) {
                    return true;
                }
            }
        }
        JSONArray chapters = raw.optJSONArray("chapters");
        if (chapters != null) {
            for (int i = 0; i < chapters.length(); i++) {
                JSONObject ch = chapters.optJSONObject(i);
                if (ch != null && segment.equals(ch.optString("id"))) {
                    return true;
                }
            }
        }
        return false;
    }

    private JSONArray episodesJson(JSONObject raw) throws JSONException {
        JSONArray array = new JSONArray();
        JSONArray episodes = raw.optJSONArray("episodes");
        if (episodes == null) {
            return array;
        }
        boolean finished = "完结".equals(raw.optString("status"));
        for (int i = 0; i < episodes.length(); i++) {
            JSONObject ep = episodes.getJSONObject(i);
            JSONObject out = new JSONObject();
            out.put("external_id", ep.optString("id"));
            out.put("index", ep.optInt("index", i + 1));
            out.put("title", ep.optString("title"));
            if (ep.has("duration_seconds") && !ep.isNull("duration_seconds")) {
                out.put("duration_seconds", ep.optInt("duration_seconds"));
            } else {
                out.put("duration_seconds", JSONObject.NULL);
            }
            out.put("is_finished", finished);
            array.put(out);
        }
        return array;
    }

    private JSONArray chaptersJson(JSONObject raw) throws JSONException {
        JSONArray array = new JSONArray();
        JSONArray chapters = raw.optJSONArray("chapters");
        if (chapters == null) {
            return array;
        }
        for (int i = 0; i < chapters.length(); i++) {
            JSONObject ch = chapters.getJSONObject(i);
            JSONObject out = new JSONObject();
            out.put("external_id", ch.optString("id"));
            out.put("index", ch.optInt("index", i + 1));
            out.put("title", ch.optString("title"));
            if (ch.has("word_count") && !ch.isNull("word_count")) {
                out.put("word_count", ch.optInt("word_count"));
            } else {
                out.put("word_count", JSONObject.NULL);
            }
            array.put(out);
        }
        return array;
    }

    // ------------------------------------------------------------ 工具

    private int parsePage(String page) {
        if (page == null || page.trim().isEmpty()) {
            return 1;
        }
        try {
            return Integer.parseInt(page.trim());
        } catch (NumberFormatException e) {
            return -1;
        }
    }

    private static final String NOISE = " \t\r\n\u3000·•－—_-:：,，.。!！?？'\"“”‘’()（）[]【】/\\|、；;";

    private static String normalizeTitle(String title) {
        if (title == null) {
            return "";
        }
        String text = java.text.Normalizer.normalize(title, java.text.Normalizer.Form.NFKC);
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            if (Character.isWhitespace(c) || NOISE.indexOf(c) >= 0) {
                continue;
            }
            sb.append(Character.toLowerCase(c));
        }
        return sb.toString();
    }

    private JSONObject catalog() throws JSONException {
        if (catalogCache != null) {
            return catalogCache;
        }
        InputStream input = null;
        try {
            input = context.getAssets().open("data/demo_catalog.json");
            BufferedReader reader = new BufferedReader(
                    new InputStreamReader(input, Charset.forName("UTF-8")));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line);
            }
            reader.close();
            catalogCache = new JSONObject(sb.toString());
            return catalogCache;
        } catch (IOException e) {
            throw new JSONException("读取内置演示目录失败：" + e.getMessage());
        } finally {
            if (input != null) {
                try {
                    input.close();
                } catch (IOException ignored) {
                    // 关闭失败不影响结果
                }
            }
        }
    }
}
