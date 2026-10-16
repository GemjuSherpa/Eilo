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
}
