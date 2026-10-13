package com.eilo.foundation

import java.util.UUID
import java.util.concurrent.Executor
import org.junit.Assert.*
import org.junit.Test

class AndroidOfflineSpeechTest {
    private class Queue : Executor {
        val tasks = ArrayDeque<Runnable>()
        override fun execute(command: Runnable) { tasks.add(command) }
        fun drain() { while (tasks.isNotEmpty()) tasks.removeFirst().run() }
    }
    private class Driver : AndroidSpeechBackend {
        var values = listOf(OfflineVoice("en-au", "en-AU", true, false))
        var callback: (String, OfflineSpeechEvent) -> Unit = { _, _ -> }
        var starts = 0; var stops = 0; var closes = 0; var id = ""; var accepted = true
        override fun voices() = values
        override fun listener(receive: (String, OfflineSpeechEvent) -> Unit) { callback = receive }
        override fun start(id: String, text: String, voice: OfflineVoice, rate: Float, gain: Float): Boolean {
            starts++; this.id=id; assertEquals("Generic fixture.",text); assertEquals("en-au",voice.id)
            assertTrue(rate in 0.5f..1.5f); assertTrue(gain in 0f..1f); return accepted
        }
        override fun stop() { stops++ }
        override fun shutdown() { closes++ }
    }
    private fun token() = GenerationToken(UUID.randomUUID(),UUID.randomUUID(),1,0)
    private fun adapter(d:Driver,q:Queue,allowed:(GenerationToken)->Boolean={true}) = AndroidOfflineSpeech(d,allowed=allowed,worker=q).apply { refresh { assertTrue(it) };q.drain() }
    @Test fun offlineSelectionStartsOnlyOnWorkerAndReportsMetadata() {
        val q=Queue();val d=Driver();val a=adapter(d,q);val events=ArrayList<OfflineSpeechEvent>()
        assertTrue(a.enqueue(token(),"Generic fixture.",gain=0.25f,event=events::add));assertEquals(0,d.starts);q.drain();assertEquals(1,d.starts)
        d.callback(d.id,OfflineSpeechEvent.STARTED);d.callback(d.id,OfflineSpeechEvent.FINISHED);q.drain()
        assertEquals(listOf(OfflineSpeechEvent.STARTED,OfflineSpeechEvent.FINISHED),events);a.close();q.drain();assertEquals(1,d.closes)
    }
    @Test fun cancelledQueuedAndLatePlaybackCannotResume() {
        val q=Queue();val d=Driver();val a=adapter(d,q);val t=token();val events=ArrayList<OfflineSpeechEvent>()
        assertTrue(a.enqueue(t,"Generic fixture.",event=events::add));t.cancelled=true;a.cancel();q.drain();assertEquals(0,d.starts)
        val fresh=token();assertTrue(a.enqueue(fresh,"Generic fixture.",event=events::add));q.drain();a.cancel();d.callback(d.id,OfflineSpeechEvent.FINISHED);q.drain();assertTrue(events.isEmpty())
    }
    @Test fun missingNetworkAndWrongExactVoiceNeverReachSynthesis() {
        val q=Queue();val d=Driver();val a=AndroidOfflineSpeech(d,allowed={true},worker=q)
        for (v in listOf(emptyList(),listOf(OfflineVoice("cloud","en-US",true,true)),listOf(OfflineVoice("missing","en-US",false,false)))) {
            d.values=v;a.refresh { assertFalse(it) };q.drain();assertFalse(a.enqueue(token(),"Generic fixture."){})
        }
        d.values=listOf(OfflineVoice("en-au","en-AU",true,false));a.refresh("absent"){assertFalse(it)};q.drain();assertEquals(0,d.starts)
    }
    @Test fun invalidBoundsAndUnavailableSynthesisAreTruthful() {
        val q=Queue();val d=Driver();val a=adapter(d,q);val t=token()
        assertFalse(a.enqueue(t," "){});assertFalse(a.enqueue(t,"x".repeat(4097)){});assertFalse(a.enqueue(t,"Generic fixture.",rate=Float.NaN){})
        d.accepted=false;val events=ArrayList<OfflineSpeechEvent>();assertTrue(a.enqueue(t,"Generic fixture.",event=events::add));q.drain()
        assertEquals(listOf(OfflineSpeechEvent.FAILED),events)
        val denied=adapter(Driver(),q){false};assertFalse(denied.enqueue(token(),"Generic fixture."){})
    }
    @Test fun voiceRefreshRevokesPendingAndCloseIsIdempotent() {
        val q=Queue();val d=Driver();val a=adapter(d,q);assertTrue(a.enqueue(token(),"Generic fixture."){})
        a.registry.invalidate();q.drain();assertEquals(0,d.starts);a.close();a.close();q.drain();assertEquals(1,d.closes)
        assertFalse(a.enqueue(token(),"Generic fixture."){})
        var completed=false;a.refresh { assertFalse(it);completed=true };assertTrue(completed)
    }
    @Test fun backendExceptionsCompletePreparationAndSynthesisSafely() {
        val q=Queue();val d=Driver()
        val broken=object:AndroidSpeechBackend by d {
            override fun voices():List<OfflineVoice>{throw IllegalStateException("synthetic detail")}
        }
        val first=AndroidOfflineSpeech(broken,allowed={true},worker=q);var completed=false
        first.refresh { assertFalse(it);completed=true };q.drain();assertTrue(completed)
        val failing=object:AndroidSpeechBackend by d {
            override fun start(id:String,text:String,voice:OfflineVoice,rate:Float,gain:Float):Boolean{throw IllegalStateException("synthetic detail")}
        }
        val second=AndroidOfflineSpeech(failing,allowed={true},worker=q);second.refresh{assertTrue(it)};q.drain()
        val events=ArrayList<OfflineSpeechEvent>();assertTrue(second.enqueue(token(),"Generic fixture.",event=events::add));q.drain()
        assertEquals(listOf(OfflineSpeechEvent.FAILED),events)
    }
    @Test fun timedOutPreparationCannotPublishLateReadiness() {
        val q=Queue();val d=Driver();var expired:(()->Unit)?=null;var completions=0
        val scheduler=IdleScheduler { delay,task -> assertEquals(5000,delay);expired=task;IdleCancellation{} }
        val a=AndroidOfflineSpeech(d,allowed={true},worker=q,scheduler=scheduler)
        a.refresh { assertFalse(it);completions++ };expired!!();q.drain()
        assertEquals(1,completions);assertFalse(a.registry.ready());assertFalse(a.enqueue(token(),"Generic fixture."){})
        a.close();q.drain()
    }
    @Test fun replacedPreparationCompletesOldRequestOnce() {
        val q=Queue();val d=Driver();val a=AndroidOfflineSpeech(d,allowed={true},worker=q)
        var old=0;var fresh=0;a.refresh { assertFalse(it);old++ };a.refresh{assertTrue(it);fresh++}
        assertEquals(1,old);q.drain();assertEquals(1,old);assertEquals(1,fresh);a.close();q.drain()
    }
}
