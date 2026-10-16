package com.eilo.foundation

import java.util.concurrent.Executor
import org.junit.Assert.*
import org.junit.Test

class VadAsrCaptureTest {
    private class Worker:Executor {val tasks=ArrayDeque<Runnable>();override fun execute(command:Runnable){tasks.add(command)};fun run(){while(tasks.isNotEmpty())tasks.removeFirst().run()}}
    private class Vad:VadStream {var samples=0;var probability=0.95f;override fun process(pcm:FloatArray,count:Int,final:Boolean):NativeVadObservation{val start=samples;samples+=count;return NativeVadObservation(probability,start,count,final)};override fun close(){}}
    private class Asr:AsrStream {val pcm=mutableListOf<Float>();var closes=0;var onAccept:()->Unit={};var onFinal:()->Unit={};var onClose:()->Unit={};override fun accept(pcm:FloatArray,count:Int){this.pcm.addAll(pcm.take(count));onAccept()};override fun text(finish:Boolean):String{if(finish)onFinal();return "synthetic question"};override fun close(){closes++;onClose()}}
    private fun controller(e:EffectsSpy):NativeController{val c=testController(effects=e);c.dispatch(ControllerEvent.START);c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token());return c}
    private fun feed(s:VadCaptureSlot,count:Int=320){s.submit(ShortArray(count){8192},count,16000)}
    @Test fun exactJoinedPrefixOneFinalUnknownConfidenceClarifies() {
        val w=Worker();val e=EffectsSpy();val c=controller(e);val v=Vad();val a=Asr();val s=VadCaptureSlot(16000)
        val finals=mutableListOf<AsrText>();val events=mutableListOf<VadCaptureOutcome>();var opens=0
        assertTrue(s.install(e,c,c.token()!!,w,{true},{v},{events.add(it)},openAsr={opens++;a},recognized={finals.add(it)},asrVerified={true}))
        repeat(34){i->v.probability=if(i<8)0.95f else 0.05f;feed(s);w.run();if(i<33)assertEquals(0,opens)}
        assertEquals(List(10752){0.25f},a.pcm);assertEquals(1,opens);assertEquals(1,a.closes);assertEquals(1,finals.size);assertEquals(192,events.single().lastChunkConsumed)
        assertTrue(c.finishRecognition(c.token()!!,finals.single(),null,active={true},accepted={fail("confidence must not be invented")}))
        assertEquals(listOf(RecognitionPolicy.CLARIFICATION),e.clauses);s.close();w.run()
    }
    @Test fun silenceAndEarlyEofNeverOpenOrReleaseText() {
        for(silence in listOf(false,true)) {
            val w=Worker();val e=EffectsSpy();val c=controller(e);val v=Vad();val s=VadCaptureSlot(16000);var opens=0;var finals=0;v.probability=0.05f
            assertTrue(s.install(e,c,c.token()!!,w,{true},{v},openAsr={opens++;Asr()},recognized={finals++},asrVerified={true}))
            if(silence)repeat(250){feed(s);w.run()}else{feed(s,7);s.finish();w.run()}
            assertEquals(0,opens);assertEquals(0,finals);s.close();w.run()
        }
    }
    @Test fun stopAtAsrAcceptFinalOrCleanupSuppressesText() {
        repeat(3){phase->
            val w=Worker();val e=EffectsSpy();val c=controller(e);val v=Vad();val a=Asr();val s=VadCaptureSlot(16000);var finals=0
            val stop:()->Unit={c.stop();Unit};when(phase){0->a.onAccept=stop;1->a.onFinal=stop;else->a.onClose=stop}
            assertTrue(s.install(e,c,c.token()!!,w,{true},{v},openAsr={a},recognized={finals++},asrVerified={true}))
            repeat(34){i->v.probability=if(i<8)0.95f else 0.05f;feed(s);w.run()}
            assertEquals(0,finals);assertEquals(1,a.closes);assertEquals(ControllerState.STOPPED,c.state());s.close();w.run()
        }
    }
    @Test fun independentAsrCapabilityRequiredAndRecheckedAfterCleanup() {
        val w=Worker();val e=EffectsSpy();val c=controller(e);val v=Vad();val a=Asr();val s=VadCaptureSlot(16000)
        assertFalse(s.install(e,c,c.token()!!,w,{true},{v},openAsr={a}))
        var valid=true;var finals=0;a.onClose={valid=false}
        assertTrue(s.install(e,c,c.token()!!,w,{true},{v},openAsr={a},recognized={finals++},asrVerified={valid}))
        repeat(34){i->v.probability=if(i<8)0.95f else 0.05f;feed(s);w.run()}
        assertEquals(0,finals);assertEquals(ControllerState.ERROR,c.state());assertEquals(1,a.closes);s.close();w.run()
    }
    @Test fun stopDoesNotWaitForBlockedAsrWorker() {
        val worker=java.util.concurrent.Executors.newSingleThreadExecutor()
        val entered=java.util.concurrent.CountDownLatch(1);val release=java.util.concurrent.CountDownLatch(1)
        val e=EffectsSpy();val c=controller(e);val v=Vad();val a=Asr();val s=VadCaptureSlot(16000);var finals=0
        a.onAccept={entered.countDown();check(release.await(5,java.util.concurrent.TimeUnit.SECONDS))}
        try {
            assertTrue(s.install(e,c,c.token()!!,worker,{true},{v},openAsr={a},recognized={finals++},asrVerified={true}))
            repeat(33){i->v.probability=if(i<8)0.95f else 0.05f;feed(s);worker.submit{}.get(5,java.util.concurrent.TimeUnit.SECONDS)}
            feed(s);assertTrue(entered.await(5,java.util.concurrent.TimeUnit.SECONDS));assertTrue(c.stop());release.countDown()
            worker.submit{}.get(5,java.util.concurrent.TimeUnit.SECONDS);assertEquals(0,finals);assertEquals(1,a.closes)
        } finally {release.countDown();s.close();worker.shutdown();assertTrue(worker.awaitTermination(5,java.util.concurrent.TimeUnit.SECONDS))}
    }
}
