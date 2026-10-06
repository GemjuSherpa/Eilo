package com.eilo

import com.facebook.react.bridge.*
import com.facebook.react.module.annotations.ReactModule
import android.os.Handler
import android.os.Looper
import org.json.JSONObject

/** Generated TurboModule surface contains only bounded metadata and allowlisted commands. */
@ReactModule(name=EiloControlModule.NAME)
class EiloControlModule(context: ReactApplicationContext): NativeEiloControlSpec(context) {
  private val app get() = reactApplicationContext.applicationContext as MainApplication
  private val main=Handler(Looper.getMainLooper())
  private var active=false
  private var last=""
  private var previousPayload=""
  private var revision=0L
  private var notificationRequested=false
  private val refresh=object:Runnable {
    override fun run() {
      if (!active) return
      try { val value=snapshot();if(value!=last) { last=value;emitOnSnapshot(value) } } catch (_:Exception) { /* getSnapshot exposes a generic failure on reconnect. */ }
      main.postDelayed(this,250)
    }
  }
  override fun getName()=NAME
  override fun initialize() { super.initialize();active=true;main.post(refresh) }
  override fun invalidate() { active=false;main.removeCallbacks(refresh);super.invalidate() } // UI detachment never owns audio.
  private fun snapshot():String {
    val c=app.conversationController;c.permissionChanged()
    val payload=JSONObject(mapOf("version" to 1,"controller" to c.snapshot(),"capturePending" to c.captureIsPending(),"speakerConfirmationRequired" to c.speakerConfirmationRequired(),"preferences" to app.consent.snapshot()))
    val raw=payload.toString()
    if(raw!=previousPayload) { revision++;previousPayload=raw }
    return payload.put("revision",revision).toString()
  }
  override fun getSnapshot(promise:Promise) { main.post { try { promise.resolve(snapshot()) } catch (_:Exception) { promise.reject("unavailable","Native controls unavailable") } } }
  override fun command(name:String,value:String,promise:Promise) {
    main.post {
      try {
        val c=app.conversationController
        val unlocked=!app.getSystemService(android.app.KeyguardManager::class.java).isDeviceLocked
        if(name !in setOf("start","stop","confirmSpeaker","history","completeOnboarding") || (name!="history" && value!="") || (name=="history" && value !in setOf("private","history"))) { promise.reject("invalid_command","Unsupported control");return@post }
        when(name) {
          "history" -> if(app.foregroundCaptureVisible && unlocked) {
            c.privacyTransition(com.eilo.foundation.PrivacyChange.PRIVATE_SESSION)
            if(!app.consent.chooseHistory(if(value=="private") com.eilo.foundation.HistoryChoice.PRIVATE else com.eilo.foundation.HistoryChoice.HISTORY)) throw IllegalStateException()
          }
          "completeOnboarding" -> if(app.foregroundCaptureVisible && unlocked && !app.consent.completeOnboarding()) throw IllegalStateException()
          "stop" -> c.stop()
          "confirmSpeaker" -> if(app.foregroundCaptureVisible && unlocked) c.confirmSpeaker() else c.stop()
          "start" -> if(app.foregroundCaptureVisible && unlocked && app.consent.canStart()) {
            val activity=reactApplicationContext.currentActivity
            val needsNotification=android.os.Build.VERSION.SDK_INT >= 33 && app.checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) != android.content.pm.PackageManager.PERMISSION_GRANTED
            if(needsNotification && c.modelStatus()==com.eilo.foundation.ModelStatus.READY && app.checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)==android.content.pm.PackageManager.PERMISSION_GRANTED) {
              if(!notificationRequested && activity is com.facebook.react.modules.core.PermissionAwareActivity) {
                notificationRequested=true
                activity.requestPermissions(arrayOf(android.Manifest.permission.POST_NOTIFICATIONS),2702,com.facebook.react.modules.core.PermissionListener { code,_,_-> code==2702 })
              }
              // A later explicit Start is required, never a delayed permission auto-start.
              c.stop()
            } else c.dispatch(com.eilo.foundation.ControllerEvent.START)
          } else c.stop()
        }
        promise.resolve(snapshot())
      } catch (_:Exception) { app.conversationController.stop();promise.reject("unavailable","Native control unavailable") }
    }
  }
  companion object { const val NAME="EiloControl" }
}
class EiloControlPackage: com.facebook.react.BaseReactPackage() {
  override fun getModule(name:String,context:ReactApplicationContext):NativeModule? = if(name==EiloControlModule.NAME) EiloControlModule(context) else null
  override fun getReactModuleInfoProvider()=com.facebook.react.module.model.ReactModuleInfoProvider {
    mapOf(EiloControlModule.NAME to com.facebook.react.module.model.ReactModuleInfo(EiloControlModule.NAME,EiloControlModule.NAME,false,false,false,true))
  }
}
