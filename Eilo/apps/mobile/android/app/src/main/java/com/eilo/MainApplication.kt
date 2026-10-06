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
  val consent by lazy { com.eilo.foundation.NativeConsentPolicy(com.eilo.foundation.AndroidConsentPersistence(this)) }
  @Volatile private var captureSessionId=0
  private val interruptionHandler: com.eilo.foundation.AudioInterruptionHandler by lazy { com.eilo.foundation.AudioInterruptionHandler(conversationController) }
  private val audioFocus: com.eilo.foundation.AndroidAudioFocus by lazy { com.eilo.foundation.AndroidAudioFocus(this) { interruptionHandler.receive(com.eilo.foundation.AudioInterruption.FOCUS_LOSS) } }
  @Volatile var captureServiceWanted=false
  @Volatile var captureServiceRunning=false
  @Volatile var foregroundCaptureVisible = false
  private val captureWorker = java.util.concurrent.Executors.newSingleThreadExecutor { task ->
    Thread(task, "eilo-native-capture").apply { isDaemon = true }
  }
  private val foregroundCapture by lazy {
    com.eilo.foundation.ForegroundCapture(captureWorker, {
      foregroundCaptureVisible &&
        checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) == android.content.pm.PackageManager.PERMISSION_GRANTED &&
        !getSystemService(android.app.KeyguardManager::class.java).isDeviceLocked
    }, { com.eilo.foundation.AndroidCaptureDevice(this).also { captureSessionId=it.sessionId } }, {
      audioFocus.acquire()
      captureServiceWanted=true
      startForegroundService(android.content.Intent(this,CaptureService::class.java))
    }, {
      captureSessionId=0
      audioFocus.release()
      captureServiceWanted=false
      stopService(android.content.Intent(this,CaptureService::class.java))
    })
  }
  val conversationController: com.eilo.foundation.NativeController by lazy { com.eilo.foundation.NativeController(effects=foregroundCapture,models=modelReadiness,privateGate=com.eilo.foundation.PrivateEffectGate { consent.personalWritesAllowed() }) }

  override val reactHost: ReactHost by lazy {
    getDefaultReactHost(
      context = applicationContext,
      packageList =
        PackageList(this).packages.apply {
          add(EiloControlPackage())
        },
    )
  }

  override fun onCreate() {
    super.onCreate()
    if (android.os.Build.VERSION.SDK_INT >= 29) {
      getSystemService(android.media.AudioManager::class.java).registerAudioRecordingCallback(object: android.media.AudioManager.AudioRecordingCallback() {
        override fun onRecordingConfigChanged(configs: MutableList<android.media.AudioRecordingConfiguration>) {
          if (configs.any { it.clientAudioSessionId == captureSessionId && it.isClientSilenced }) interruptionHandler.receive(com.eilo.foundation.AudioInterruption.CAPTURE_CONTENTION)
        }
      },android.os.Handler(android.os.Looper.getMainLooper()))
    }
    getSystemService(android.media.AudioManager::class.java).registerAudioDeviceCallback(object: android.media.AudioDeviceCallback() {
      override fun onAudioDevicesRemoved(devices: Array<out android.media.AudioDeviceInfo>) {
        if (devices.any { it.isSink && (it.type in setOf(android.media.AudioDeviceInfo.TYPE_WIRED_HEADPHONES,android.media.AudioDeviceInfo.TYPE_WIRED_HEADSET,android.media.AudioDeviceInfo.TYPE_BLUETOOTH_SCO,android.media.AudioDeviceInfo.TYPE_BLUETOOTH_A2DP) || (android.os.Build.VERSION.SDK_INT >= 31 && it.type == android.media.AudioDeviceInfo.TYPE_BLE_HEADSET)) }) conversationController.routeDisconnected()
      }
    },android.os.Handler(android.os.Looper.getMainLooper()))
    conversationController.setOutputGain((consent.snapshot()["volume"] as Int)/100f)
    loadReactNative(this)
  }
}
