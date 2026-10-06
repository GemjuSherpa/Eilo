package com.eilo

import android.app.Application
import com.facebook.react.PackageList
import com.facebook.react.ReactApplication
import com.facebook.react.ReactHost
import com.facebook.react.ReactNativeApplicationEntryPoint.loadReactNative
import com.facebook.react.defaults.DefaultReactHost.getDefaultReactHost

class MainApplication : Application(), ReactApplication {

  // One native authority per process; startup never invokes Start or restores capture.
  private val modelPacks by lazy { com.eilo.foundation.PackStore(java.io.File(noBackupFilesDir,"generic-models"),emptyMap(),"5e03bdd8700948b9c41c54dd1b00f28a2aebc03f",android=android.os.Build.VERSION.SDK_INT) }
  private val modelReadiness by lazy { com.eilo.foundation.PackReadiness(modelPacks) }
  @Volatile var foregroundCaptureVisible = false
  private val captureWorker = java.util.concurrent.Executors.newSingleThreadExecutor { task ->
    Thread(task, "eilo-native-capture").apply { isDaemon = true }
  }
  private val foregroundCapture by lazy {
    com.eilo.foundation.ForegroundCapture(captureWorker, {
      foregroundCaptureVisible &&
        checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) == android.content.pm.PackageManager.PERMISSION_GRANTED &&
        !getSystemService(android.app.KeyguardManager::class.java).isDeviceLocked
    }, { com.eilo.foundation.AndroidCaptureDevice(this) })
  }
  val conversationController by lazy { com.eilo.foundation.NativeController(effects=foregroundCapture,models=modelReadiness) }

  override val reactHost: ReactHost by lazy {
    getDefaultReactHost(
      context = applicationContext,
      packageList =
        PackageList(this).packages.apply {
          // Packages that cannot be autolinked yet can be added manually here, for example:
          // add(MyReactNativePackage())
        },
    )
  }

  override fun onCreate() {
    super.onCreate()
    loadReactNative(this)
  }
}
