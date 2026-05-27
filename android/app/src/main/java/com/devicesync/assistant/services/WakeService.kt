package com.devicesync.assistant.services

import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
import com.devicesync.assistant.helpers.SyncHelper

class WakeService : Service() {

    // ─────────────────────────────────────────
    // ON START COMMAND
    // Called when Telegram bot sends reconnect signal
    // ─────────────────────────────────────────
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // Restart main sync service
        val syncIntent = Intent(this, DeviceSyncService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(syncIntent)
        } else {
            startService(syncIntent)
        }
        // Confirm back to Telegram bot
        SyncHelper.sendDeviceOnline()
        stopSelf()
        return START_NOT_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
