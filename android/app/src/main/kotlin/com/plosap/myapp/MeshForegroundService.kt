package com.plosap.myapp

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat

/**
 * Keeps the Blousab process in the "foreground" priority class while the app is
 * in the background, so Bluetooth links, Wi-Fi Aware sessions and the LAN listener
 * are not frozen by the system. It does not move any transport logic out of the
 * activity: swiping the app away from the recents list still stops the mesh.
 */
class MeshForegroundService : Service() {
    companion object {
        private const val CHANNEL_ID = "blousab_mesh_keepalive"
        private const val NOTIFICATION_ID = 7101
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        createChannel()
        val notification = buildNotification()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NOTIFICATION_ID, notification,
                android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
        return START_STICKY
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = getSystemService(NotificationManager::class.java)
        if (manager.getNotificationChannel(CHANNEL_ID) != null) return
        val channel = NotificationChannel(CHANNEL_ID, "اتصال بلوساب", NotificationManager.IMPORTANCE_LOW)
        channel.description = "يُبقي بث الإشارة واستقبالها يعملان أثناء وجود التطبيق في الخلفية"
        channel.setShowBadge(false)
        manager.createNotificationChannel(channel)
    }

    private fun buildNotification(): Notification {
        val launch = packageManager.getLaunchIntentForPackage(packageName)
        val pending = if (launch != null) PendingIntent.getActivity(
            this, 0, launch, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        ) else null
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("بلوساب يعمل")
            .setContentText("بث واستقبال الإشارة نشطان")
            .setSmallIcon(applicationInfo.icon)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setContentIntent(pending)
            .build()
    }
}
