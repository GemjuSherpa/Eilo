package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class PrivacyEpochTest {
    @Test fun transitionsRejectStaleReadsWritesDisplayAndSpeech() {
        for (change in PrivacyChange.entries) {
            val spy=EffectsSpy(); val c=NativeController(effects=spy,privateGate=PrivateEffectGate { true })
            c.privacyTransition(PrivacyChange.HISTORY_SESSION); c.dispatch(ControllerEvent.START)
            c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token()); c.dispatch(ControllerEvent.ENDPOINT,token=c.token()); val old=c.token()!!
            var count=0; assertTrue(c.guardedPrivateEffect(old,PrivateEffect.READ_MEMORY) { count++ })
            c.privacyTransition(change)
            for (effect in PrivateEffect.entries) assertFalse(c.guardedPrivateEffect(old,effect) { count++ })
            assertFalse(c.releaseSpeech(old,"stale private clause")); assertEquals(1,count); assertTrue(old.cancelled)
        }
    }
    @Test fun defaultAndPrivateModeNeverAuthorizeMemory() {
        val c=NativeController(); c.dispatch(ControllerEvent.START)
        assertFalse(c.guardedPrivateEffect(c.token()!!,PrivateEffect.COMMIT_HISTORY) { fail("unauthorized") })
        c.privacyTransition(PrivacyChange.LOCK); assertFalse(c.dispatch(ControllerEvent.START)); c.privacyTransition(PrivacyChange.UNLOCK)
        assertEquals(ControllerState.STOPPED,c.state()); assertNull(c.token())
    }
    @Test fun delayedThreadAfterLockCannotCommit() {
        val c=NativeController(privateGate=PrivateEffectGate { true }); c.privacyTransition(PrivacyChange.HISTORY_SESSION); c.dispatch(ControllerEvent.START); val old=c.token()!!
        val latch=java.util.concurrent.CountDownLatch(1); val count=java.util.concurrent.atomic.AtomicInteger(0)
        val thread=Thread { latch.await(); c.guardedPrivateEffect(old,PrivateEffect.COMMIT_HISTORY) { count.incrementAndGet() } }
        thread.start(); c.privacyTransition(PrivacyChange.LOCK); latch.countDown(); thread.join(2000)
        assertFalse(thread.isAlive); assertEquals(0,count.get())
    }
}
