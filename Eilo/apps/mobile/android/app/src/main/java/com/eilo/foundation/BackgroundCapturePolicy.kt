package com.eilo.foundation
/** Unlocked background operation only; never authorizes locked audio or a new Start. */
object BackgroundCapturePolicy {
 fun allows(visible:Boolean,unlocked:Boolean,permission:Boolean,consent:Boolean,serviceRunning:Boolean):Boolean = unlocked && permission && (visible || (consent && serviceRunning))
}
