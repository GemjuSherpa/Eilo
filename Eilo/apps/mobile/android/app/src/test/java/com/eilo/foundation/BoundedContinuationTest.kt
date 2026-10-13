package com.eilo.foundation
import java.util.UUID
import org.junit.Assert.*
import org.junit.Test
class BoundedContinuationTest {
    private val controllers=java.util.IdentityHashMap<GenerationToken,NativeController>()
    private fun token():GenerationToken {val c=NativeController(effects=object:ControllerEffects{override fun startCapture()=true;override fun playClause(clause:String){};override fun cancelWork(){};override fun releaseCapture(){};override fun clearVolatileContext(){}},permission=object:MicrophonePermissionAdapter{override fun status()=MicrophonePermission.GRANTED;override fun request(completion:(MicrophonePermission)->Unit){completion(status())}},models=ModelReadinessAdapter{ModelStatus.READY});c.dispatch(ControllerEvent.START);c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token());c.dispatch(ControllerEvent.ENDPOINT,token=c.token());return c.token()!!.also{controllers[it]=c}}
    private fun policy(t:GenerationToken=token())=BoundedContinuation.create(controllers[t]!!,t,"Requested longer answer.",requestedLonger=true,allowed={!it.cancelled})!!
    private fun create(t:GenerationToken,latest:String,requested:Boolean=false)=BoundedContinuation.create(controllers[t]!!,t,latest,requestedLonger=requested)
    @Test fun fakeLongStreamStopsAtFourBoundedChunks(){val p=policy();repeat(4){val chunk=p.next{it.length}!!;assertEquals(it+1,chunk.index);assertTrue(chunk.plan.promptTokens+chunk.plan.outputLimit<=4096);assertEquals(256,chunk.plan.outputLimit);assertTrue(chunk.plan.text.contains("Requested longer answer."));val fakeTokens=List(256){"w"};assertTrue(p.complete(chunk,fakeTokens.joinToString(" "),fakeTokens.size,true))};assertEquals(1024,p.totalGenerated);assertNull(p.next{it.length})}
    @Test fun defaultRequestAndApprovalDenyContinuation(){assertNull(create(token(),"Normal reply."));assertNull(create(token(),"Longer.",true));val p=policy();val chunk=p.next{it.length}!!;assertFalse(p.complete(chunk,"Unapproved.",8));assertNull(p.next{it.length})}
    @Test fun oversizeDuplicateStaleAndCancelledCannotRevive(){val p=policy();val c=p.next{it.length}!!;assertFalse(p.complete(c,"Too many.",257,true));assertNull(p.next{it.length});val t=token();val stale=policy(t);val old=stale.next{it.length}!!;t.cancelled=true;assertFalse(stale.complete(old,"Late.",8,true))
        val duplicate=policy();val first=duplicate.next{it.length}!!;assertTrue(duplicate.complete(first,"Approved.",8,true));assertFalse(duplicate.complete(first,"Replay.",8,true));assertNull(duplicate.next{it.length})
    }
    @Test fun cancellationDuringBudgetAndIrreducibleContextFailClosed(){val p=policy();assertNull(p.next{p.requestCancellation();it.length});assertNull(p.next{it.length});val ht=token();val huge=BoundedContinuation.create(controllers[ht]!!,ht,"x".repeat(4000),requestedLonger=true,allowed={true})!!;assertNull(huge.next{it.length})}
    @Test fun onePolicyPerGenerationAndControllerStopRevokes(){val t=token();val p=policy(t);assertNull(BoundedContinuation.create(controllers[t]!!,t,"Reset.",requestedLonger=true,allowed={true}));val chunk=p.next{it.length}!!;controllers[t]!!.stop();assertFalse(p.complete(chunk,"Late.",8,true));assertNull(p.next{it.length})}

    @Test fun failedCancellationSignalCannotPreventStopCleanup(){val t=token();val c=controllers[t]!!;assertTrue(c.prepareContinuation(t){throw IllegalStateException("synthetic")});assertTrue(c.stop());assertEquals("stopped",c.snapshot()["state"]);assertTrue(t.cancelled)}

}
