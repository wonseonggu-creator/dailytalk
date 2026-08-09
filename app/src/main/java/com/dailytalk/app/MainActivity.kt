package com.dailytalk.app

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.VibrationEffect
import android.os.Vibrator
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.webkit.JavascriptInterface
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.webkit.WebViewAssetLoader
import java.util.Locale

class MainActivity : Activity(), TextToSpeech.OnInitListener {

    private lateinit var web: WebView
    private var tts: TextToSpeech? = null
    private var ttsReady = false
    private var fileCb: ValueCallback<Array<Uri>>? = null

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        web = WebView(this)
        setContentView(web)

        val s = web.settings
        s.javaScriptEnabled = true
        s.domStorageEnabled = true                       // localStorage 진행 저장
        s.mediaPlaybackRequiresUserGesture = false
        s.allowFileAccess = true
        s.mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW // 앱(https 오리진) -> 집 서버(http) 동기화 허용
        s.textZoom = 100

        val loader = WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this))
            .build()
        web.webViewClient = object : WebViewClient() {
            override fun shouldInterceptRequest(
                view: WebView, request: WebResourceRequest
            ): WebResourceResponse? = loader.shouldInterceptRequest(request.url)
        }

        // 사진 선택 (<input type="file">) 지원 — 응원단 딸 사진 등록용
        web.webChromeClient = object : WebChromeClient() {
            override fun onShowFileChooser(
                view: WebView?,
                filePathCallback: ValueCallback<Array<Uri>>,
                fileChooserParams: FileChooserParams
            ): Boolean {
                fileCb?.onReceiveValue(null)
                fileCb = filePathCallback
                return try {
                    startActivityForResult(fileChooserParams.createIntent(), REQ_FILE)
                    true
                } catch (e: Exception) {
                    fileCb = null
                    false
                }
            }
        }

        web.addJavascriptInterface(Bridge(), "AndroidTTS")
        tts = TextToSpeech(this, this)

        web.loadUrl("https://appassets.androidplatform.net/assets/dailytalk.html")
    }

    @Deprecated("deprecated in api")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQ_FILE) {
            fileCb?.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(resultCode, data))
            fileCb = null
        }
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            tts?.language = Locale.US
            tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) {}
                override fun onDone(utteranceId: String?) = notifyEnd()
                @Deprecated("deprecated in api")
                override fun onError(utteranceId: String?) = notifyEnd()
            })
            ttsReady = true
        }
    }

    private fun notifyEnd() {
        runOnUiThread { web.evaluateJavascript("window._ttsEnd&&window._ttsEnd()", null) }
    }

    inner class Bridge {
        @JavascriptInterface
        fun speak(text: String, rate: Float) {
            if (!ttsReady) return
            tts?.setSpeechRate(rate)
            tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "dt")
        }

        @JavascriptInterface
        fun stop() { tts?.stop() }

        @JavascriptInterface
        @Suppress("DEPRECATION")
        fun vibrate(ms: Int) {
            val v = getSystemService(Vibrator::class.java) ?: return
            v.vibrate(VibrationEffect.createOneShot(ms.toLong().coerceIn(10, 300), VibrationEffect.DEFAULT_AMPLITUDE))
        }
    }

    @Deprecated("deprecated in api")
    override fun onBackPressed() {
        // 레슨 중이면 레슨 종료, 다른 탭이면 홈으로, 홈이면 앱 종료
        web.evaluateJavascript(
            "(function(){var l=document.getElementById('s-lesson');" +
            "if(l&&l.classList.contains('on')){quitLesson();return 1}" +
            "var h=document.getElementById('s-home');" +
            "if(h&&!h.classList.contains('on')){go('home');return 1}return 0})()"
        ) { v -> if (v == "0") finish() }
    }

    override fun onDestroy() {
        tts?.stop(); tts?.shutdown()
        super.onDestroy()
    }

    companion object { private const val REQ_FILE = 1 }
}
