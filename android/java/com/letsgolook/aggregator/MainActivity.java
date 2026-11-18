package com.letsgolook.aggregator;

import android.app.Activity;
import android.os.Bundle;
import android.view.ViewGroup;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

/**
 * 应用外壳：WebView 加载内置前端页面，数据经 {@link LglBridge} 暴露的 JS 接口读取。
 *
 * 设计选择的原因：
 * 1) 平台后端是 Python，Android 上无法直接运行 CPython，因此把「演示源」的检索 /
 *    详情 / 解析逻辑用纯 Java 复刻到 Bridge 中，接口形状与 HTTP API 完全一致；
 * 2) 同一份 web/index.html 同时服务浏览器与 App，避免两套界面漂移。
 */
public class MainActivity extends Activity {

    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        webView = new WebView(this);
        webView.setLayoutParams(new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(false);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);

        webView.setWebViewClient(new WebViewClient());
        webView.addJavascriptInterface(new LglBridge(this), "LGLNative");

        setContentView(webView);
        webView.loadUrl("file:///android_asset/web/index.html");
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
            return;
        }
        super.onBackPressed();
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.removeJavascriptInterface("LGLNative");
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }
}
