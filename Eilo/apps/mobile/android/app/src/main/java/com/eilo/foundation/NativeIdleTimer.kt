package com.eilo.foundation
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
fun interface NativeClock { fun milliseconds(): Long }
fun interface IdleCancellation { fun cancel() }
fun interface IdleScheduler { fun schedule(delayMilliseconds: Long, task: () -> Unit): IdleCancellation }
class MonotonicClock : NativeClock { override fun milliseconds(): Long = System.nanoTime() / 1_000_000 }
class NativeIdleScheduler : IdleScheduler {
    private val executor by lazy { Executors.newSingleThreadScheduledExecutor { runnable -> Thread(runnable,"Eilo-idle").apply { isDaemon=true } } }
    override fun schedule(delayMilliseconds: Long, task: () -> Unit): IdleCancellation {
        val future=executor.schedule({ task() },delayMilliseconds,TimeUnit.MILLISECONDS)
        return IdleCancellation { future.cancel(false) }
    }
}
