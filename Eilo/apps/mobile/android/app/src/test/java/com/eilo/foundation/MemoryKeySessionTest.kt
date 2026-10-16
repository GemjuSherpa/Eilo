package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class MemoryKeySessionTest {
    class Clock:NativeClock{var now=100L;override fun milliseconds()=now}
    class Timer:IdleScheduler{val tasks=mutableListOf<()->Unit>();override fun schedule(delayMilliseconds:Long,task:()->Unit):IdleCancellation{tasks.add(task);return IdleCancellation{}}}
    private fun key()=ProtectedKey(ByteArray(32){9})
    @Test fun explicitAuthenticationExpiryAndLateResult() {
        val clock=Clock();val timer=Timer();var unlocked=true;val s=MemoryKeySession(clock,timer,{unlocked})
        assertFalse(s.allows(PrivateEffect.READ_MEMORY));val t=s.beginAuthentication()!!;val k=key()
        assertTrue(s.complete(t,k));assertTrue(s.allows(PrivateEffect.READ_MEMORY));clock.now+=60_000
        assertFalse(s.allows(PrivateEffect.COMMIT_HISTORY));assertFalse(k.active())
        val old=s.beginAuthentication()!!;s.revoke();val late=key();assertFalse(s.complete(old,late));assertFalse(late.active())
        unlocked=false;assertNull(s.beginAuthentication());unlocked=true;assertFalse(s.allows(PrivateEffect.READ_MEMORY))
    }
    @Test fun oldTimerAndDuplicateCannotReplaceNewSession() {
        val timer=Timer();val s=MemoryKeySession(scheduler=timer,unlocked={true})
        val a=s.beginAuthentication()!!;val ka=key();assertTrue(s.complete(a,ka))
        val b=s.beginAuthentication()!!;val kb=key();assertTrue(s.complete(b,kb));timer.tasks[0]()
        assertTrue(s.allows(PrivateEffect.READ_MEMORY));assertFalse(ka.active())
        val duplicate=key();assertFalse(s.complete(b,duplicate));assertFalse(duplicate.active());assertTrue(kb.active())
        timer.tasks[1]();assertFalse(kb.active())
    }
    @Test fun revokeDestroysOwnedCopiesAndRejectsDeniedAuthenticationReuse() {
        val s=MemoryKeySession(unlocked={true});val k=key();val t=s.beginAuthentication()!!
        assertTrue(s.complete(t,k));val copies=(0 until 8).map{s.copyForNativeUse()}
        assertThrows(IllegalStateException::class.java){s.copyForNativeUse()};s.revoke()
        assertFalse(k.active());copies.forEach{copy->assertFalse(copy.active());assertThrows(IllegalStateException::class.java){copy.borrow{fail("revoked copy")}}}
        val clock=Clock();val a=MemoryKeySession(clock=clock,unlocked={true});val ticket=a.beginAuthentication()!!
        clock.now+=30_000;assertFalse(a.complete(ticket,key()));clock.now=100;assertFalse(a.complete(ticket,key()))
    }

    @Test fun lockRevokesBeforeCancellationAndWithholdsPrivateEffectsInEveryVoicePhase() {
        repeat(3){phase->
            val session=MemoryKeySession(unlocked={true});val e=EffectsSpy();val c=testController(effects=e,privateGate=session)
            c.privacyTransition(PrivacyChange.HISTORY_SESSION);assertTrue(c.dispatch(ControllerEvent.START));assertTrue(c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token()))
            if(phase>0)assertTrue(c.dispatch(ControllerEvent.ENDPOINT,token=c.token()))
            if(phase>1)assertTrue(c.dispatch(ControllerEvent.SPEECH_READY,token=c.token()))
            val token=c.token()!!;val k=key();assertTrue(session.complete(session.beginAuthentication()!!,k));val copy=session.copyForNativeUse()
            e.onCancel={assertFalse(k.active());assertFalse(copy.active())}
            c.privacyTransition(PrivacyChange.LOCK);assertEquals(ControllerState.STOPPED,c.state());assertTrue(e.context.all{it==0.toByte()})
            assertFalse(c.guardedPrivateEffect(token,PrivateEffect.DISPLAY_PRIVATE){fail("stale private sink")})
        }
    }

    @Test fun wakeVoiceModelCannotAcquirePrivilegesEvenDuringAuthenticatedSession() {
        var unlocked=true;val s=MemoryKeySession(unlocked={unlocked});assertTrue(s.complete(s.beginAuthentication()!!,key()))
        for(op in PrivilegedOperation.entries) {
            for(origin in listOf(PrivilegedOrigin.WAKE,PrivilegedOrigin.VOICE,PrivilegedOrigin.MODEL))assertFalse(s.allowsPrivilegedRequest(origin,op))
            assertTrue(s.allowsPrivilegedRequest(PrivilegedOrigin.AUTHENTICATED_SCREEN,op))
        }
        unlocked=false
        for(origin in PrivilegedOrigin.entries)for(op in PrivilegedOperation.entries)assertFalse(s.allowsPrivilegedRequest(origin,op))
        unlocked=true;assertFalse(s.allowsPrivilegedRequest(PrivilegedOrigin.AUTHENTICATED_SCREEN,PrivilegedOperation.DELETE_HISTORY))
    }

}
