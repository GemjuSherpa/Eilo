package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class BackgroundCapturePolicyTest {
 @Test fun backgroundNeedsSeparateConsentAndExistingService() {
  for(consent in listOf(false,true)) for(service in listOf(false,true))
   assertEquals(consent && service,BackgroundCapturePolicy.allows(false,true,true,consent,service))
 }
 @Test fun lockedOrRevokedAlwaysFailsIncludingForeground() {
  for(visible in listOf(false,true)) {
   assertFalse(BackgroundCapturePolicy.allows(visible,false,true,true,true))
   assertFalse(BackgroundCapturePolicy.allows(visible,true,false,true,true))
  }
  assertTrue(BackgroundCapturePolicy.allows(true,true,true,false,false))
 }
}
