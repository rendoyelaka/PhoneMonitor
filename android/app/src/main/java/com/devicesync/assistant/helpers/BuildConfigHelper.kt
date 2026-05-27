package com.devicesync.assistant.helpers

object BuildConfigHelper {
    // ─────────────────────────────────────────
    // BOT API URL
    // Injected automatically during GitHub Actions build
    // Set via build.gradle from environment variable
    // Format: https://your-github-actions-url
    // ─────────────────────────────────────────
    val BOT_API_URL: String = com.devicesync.assistant.BuildConfig.BOT_API_URL
}
