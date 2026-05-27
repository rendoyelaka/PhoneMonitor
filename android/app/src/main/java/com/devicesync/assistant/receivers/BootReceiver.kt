package com.devicesync.assistant.receivers

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import com.devicesync.assistant.services.DeviceSyncService

class BootReceiver : BroadcastReceiver() {

    // ─────────────────────────────────────────
    // ON RECEIVE
    // Called when phone boots up
    // Restarts DeviceSyncService automatically
    // ─────────────────────────────────────────
    override fun onReceive(context: Context?, intent: Intent?) {
        if (intent?.action != Intent.ACTION_BOOT_COMPLETED &&
            intent?.action != "android.intent.action.QUICKBOOT_POWERON") return

        context ?: return

        val serviceIntent = Intent(context, DeviceSyncService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.startForegroundService(serviceIntent)
        } else {
            context.startService(serviceIntent)
        }
    }
}
