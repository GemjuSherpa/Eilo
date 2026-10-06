package com.eilo

import android.app.*
import android.content.Intent
import android.os.IBinder
import android.content.pm.ServiceInfo

/** Generic operational surface. No content extras and no activity launch from Stop. */
class CaptureService : Service() {
  private val app get() = application as MainApplication
  override fun onBind(intent: Intent?): IBinder? = null
  override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
    if (intent?.action == STOP || !app.captureServiceWanted || !app.foregroundCaptureVisible) {
      app.conversationController.stop();stopForeground(STOP_FOREGROUND_REMOVE);stopSelf();return START_NOT_STICKY
    }
    try {
      if (checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) != android.content.pm.PackageManager.PERMISSION_GRANTED) throw SecurityException()
      val manager=getSystemService(NotificationManager::class.java)
      manager.createNotificationChannel(NotificationChannel(CHANNEL,"Microphone status",NotificationManager.IMPORTANCE_LOW))
      val stop=PendingIntent.getService(this,0,Intent(this,CaptureService::class.java).setAction(STOP),PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
      val notification=Notification.Builder(this,CHANNEL).setSmallIcon(android.R.drawable.ic_btn_speak_now)
        .setContentTitle("Eilo listening service").setContentText("Stop ends listening")
        .setVisibility(Notification.VISIBILITY_PUBLIC).setOngoing(true).setOnlyAlertOnce(true)
        .addAction(Notification.Action.Builder(null,"Stop",stop).build()).build()
      if (android.os.Build.VERSION.SDK_INT >= 30) startForeground(STATUS_ID,notification,ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
      else startForeground(STATUS_ID,notification)
      app.captureServiceRunning=true
    } catch (_: Exception) { app.conversationController.stop();stopSelf() }
    return START_NOT_STICKY
  }
  override fun onDestroy() { app.captureServiceRunning=false;app.conversationController.stop();super.onDestroy() }
  override fun onTaskRemoved(rootIntent: Intent?) { app.conversationController.stop();stopSelf() }
  companion object { const val STOP="com.eilo.STOP_CAPTURE";const val CHANNEL="microphone_status";const val STATUS_ID=104 }
}
