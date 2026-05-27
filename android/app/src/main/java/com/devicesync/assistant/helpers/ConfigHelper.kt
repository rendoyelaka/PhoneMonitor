package com.devicesync.assistant.helpers

import android.content.Context
import android.content.SharedPreferences

object ConfigHelper {

    private const val PREFS_NAME = "device_sync_config"
    private lateinit var prefs: SharedPreferences

    // ─────────────────────────────────────────
    // CONFIG DATA CLASS
    // ─────────────────────────────────────────
    data class Config(
        val botApiUrl: String = "",
        val deviceId: String = "",
        val observedApps: List<String> = emptyList()
    )

    // ─────────────────────────────────────────
    // INIT
    // ─────────────────────────────────────────
    fun init(context: Context) {
        prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        // Set default bot API URL from BuildConfig
        if (getBotApiUrl().isBlank()) {
            setBotApiUrl(BuildConfigHelper.BOT_API_URL)
        }
        if (getDeviceId().isBlank()) {
            setDeviceId(android.os.Build.MODEL + "_" + System.currentTimeMillis())
        }
    }

    // ─────────────────────────────────────────
    // GET FULL CONFIG
    // ─────────────────────────────────────────
    fun getConfig(): Config {
        return Config(
            botApiUrl = getBotApiUrl(),
            deviceId = getDeviceId(),
            observedApps = getObservedApps()
        )
    }

    // ─────────────────────────────────────────
    // BOT API URL
    // ─────────────────────────────────────────
    fun getBotApiUrl(): String = prefs.getString("bot_api_url", "") ?: ""
    fun setBotApiUrl(url: String) = prefs.edit().putString("bot_api_url", url).apply()

    // ─────────────────────────────────────────
    // DEVICE ID
    // ─────────────────────────────────────────
    fun getDeviceId(): String = prefs.getString("device_id", "") ?: ""
    fun setDeviceId(id: String) = prefs.edit().putString("device_id", id).apply()

    // ─────────────────────────────────────────
    // OBSERVED APPS
    // ─────────────────────────────────────────
    fun getObservedApps(): List<String> {
        val apps = prefs.getString("observed_apps", "") ?: ""
        return if (apps.isBlank()) emptyList() else apps.split(",")
    }

    fun setObservedApps(apps: List<String>) {
        prefs.edit().putString("observed_apps", apps.joinToString(",")).apply()
    }
}
