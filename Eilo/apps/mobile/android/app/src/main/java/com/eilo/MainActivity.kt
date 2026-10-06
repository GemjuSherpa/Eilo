package com.eilo

import com.facebook.react.ReactActivity
import com.facebook.react.ReactActivityDelegate
import com.facebook.react.defaults.DefaultNewArchitectureEntryPoint.fabricEnabled
import com.facebook.react.defaults.DefaultReactActivityDelegate

class MainActivity : ReactActivity() {
  private val controller get() = (application as MainApplication).conversationController
  override fun onCreate(savedInstanceState: android.os.Bundle?) {
    super.onCreate(savedInstanceState)
    controller.bindPermissionAdapter(com.eilo.foundation.AndroidMicrophonePermission(this))
  }
  override fun onResume() { super.onResume(); controller.permissionChanged() }
  // Background capture has not been enabled in S02.
  override fun onPause() { controller.stop(); super.onPause() }
  override fun onDestroy() {
    controller.bindPermissionAdapter(com.eilo.foundation.UnavailablePermissionAdapter())
    super.onDestroy()
  }


  /**
   * Returns the name of the main component registered from JavaScript. This is used to schedule
   * rendering of the component.
   */
  override fun getMainComponentName(): String = "Eilo"

  /**
   * Returns the instance of the [ReactActivityDelegate]. We use [DefaultReactActivityDelegate]
   * which allows you to enable New Architecture with a single boolean flags [fabricEnabled]
   */
  override fun createReactActivityDelegate(): ReactActivityDelegate =
      DefaultReactActivityDelegate(this, mainComponentName, fabricEnabled)
}
