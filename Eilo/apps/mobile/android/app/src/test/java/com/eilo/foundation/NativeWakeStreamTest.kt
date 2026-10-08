package com.eilo.foundation

import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

class NativeWakeStreamTest {
    private val paths=WakeModelPaths("/verified/e","/verified/d","/verified/j","/verified/t")
    private val config=WakeConfiguration("HEY EILO",0.125f,1.5f)
    private class API:NativeWakeAPI {
        var created=0;var processed=0;var destroyed=0;var result=1
        var onCreate:()->Unit={};var onProcess:()->Unit={}
        override fun create(paths:WakeModelPaths,configuration:WakeConfiguration):Long {
            assertEquals("/verified/t",paths.tokens);assertEquals(0.125f,configuration.threshold)
            created++;onCreate();return 7L
        }
        override fun process(handle:Long,samples:FloatArray,count:Int,rate:Int):Int {
            assertEquals(7L,handle);processed++;onProcess();return result
        }
        override fun destroy(handle:Long) { assertEquals(7L,handle);destroyed++ }
    }
    @Test fun fixedKeywordLatchResetAndIdempotentClose() {
        val api=API();val s=NativeWakeStream(paths,config,{true},api);val input=floatArrayOf(.5f,Float.NaN)
        s.accept(input,1,16000);api.result=0;s.accept(input,1,16000)
        assertEquals("HEY EILO",s.keyword());assertFalse(s.ready());s.reset();assertEquals("",s.keyword())
        assertEquals(.5f,input[0]);s.close();s.close();assertEquals(1,api.destroyed)
        assertThrows(IllegalStateException::class.java){s.keyword()};assertThrows(IllegalStateException::class.java){s.accept(input,1,16000)}
        assertEquals(2,api.processed)
    }
    @Test fun verificationBeforeAndAfterCreationReleasesCandidate() {
        val api=API();var valid=false
        assertThrows(IllegalStateException::class.java){NativeWakeStream(paths,config,{valid},api)};assertEquals(0,api.created)
        valid=true;api.onCreate={valid=false}
        assertThrows(IllegalStateException::class.java){NativeWakeStream(paths,config,{valid},api)};assertEquals(1,api.destroyed)
        var checks=0;api.onCreate={}
        assertThrows(IllegalStateException::class.java){NativeWakeStream(paths,config,{if(++checks==2)error("synthetic");true},api)}
        assertEquals(2,api.destroyed)
    }
    @Test fun invalidInputAndRouteChangeCloseBeforeNativeBorrow() {
        for(pair in listOf(floatArrayOf() to 0,floatArrayOf(Float.NaN) to 1,floatArrayOf(1.1f) to 1,FloatArray(1601) to 1601,floatArrayOf(0f) to 2)) {
            val api=API();val s=NativeWakeStream(paths,config,{true},api)
            assertThrows(IllegalStateException::class.java){s.accept(pair.first,pair.second,16000)}
            assertEquals(0,api.processed);assertEquals(1,api.destroyed)
        }
        for(rate in listOf(7999,192001)) {
            val api=API();val s=NativeWakeStream(paths,config,{true},api)
            assertThrows(IllegalStateException::class.java){s.accept(floatArrayOf(0f),1,rate)};assertEquals(0,api.processed)
        }
        val api=API();val s=NativeWakeStream(paths,config,{true},api);s.accept(floatArrayOf(0f),1,16000)
        assertThrows(IllegalStateException::class.java){s.accept(floatArrayOf(0f),1,48000)};assertEquals(1,api.processed);assertEquals(1,api.destroyed)
    }
    @Test fun nativeFailureAndVerificationRevocationDisableInput() {
        for(result in listOf(-1,2,1)) {
            val api=API();var valid=true;val s=NativeWakeStream(paths,config,{valid},api);api.result=result
            if(result==1)api.onProcess={valid=false}
            assertThrows(IllegalStateException::class.java){s.accept(floatArrayOf(0f),1,16000)}
            assertThrows(IllegalStateException::class.java){s.accept(floatArrayOf(0f),1,16000)}
            assertEquals(1,api.processed);assertEquals(1,api.destroyed)
        }
    }
    @Test fun closeWaitsForBorrowWithoutDoubleDestruction() {
        val api=API();val entered=CountDownLatch(1);val release=CountDownLatch(1);val done=CountDownLatch(1)
        val s=NativeWakeStream(paths,config,{true},api);api.onProcess={entered.countDown();check(release.await(3,TimeUnit.SECONDS))}
        val worker=Thread{s.accept(floatArrayOf(0f),1,16000)};worker.start();assertTrue(entered.await(3,TimeUnit.SECONDS))
        val closer=Thread{s.close();done.countDown()};closer.start();assertFalse(done.await(50,TimeUnit.MILLISECONDS));assertEquals(0,api.destroyed)
        release.countDown();worker.join(3000);closer.join(3000);assertFalse(worker.isAlive);assertFalse(closer.isAlive);assertEquals(1,api.destroyed)
    }
    @Test fun queuedControllerWakeIsRevokedOnStop() {
        val c=testController();c.dispatch(ControllerEvent.START);val token=c.token()!!;val api=API()
        val d=WakeDetector(config,verified={true},open={NativeWakeStream(paths,it,{true},api)})
        assertTrue(d.begin(token));val event=d.processPCM16(token,shortArrayOf(0),1,16000)!!
        c.stop();assertFalse(event.apply(c));d.close();assertEquals(1,api.destroyed)
    }
    @Test fun invalidPathsConfigurationAndUnavailableDefaultCannotOpen() {
        for(path in listOf("relative","","/e\u0000ignored","/"+"a".repeat(4096)))
            assertThrows(IllegalArgumentException::class.java){WakeModelPaths(path,"/d","/j","/t")}
        val api=API();assertThrows(IllegalStateException::class.java){NativeWakeStream(paths,WakeConfiguration("OTHER",.125f,1.5f),{true},api)}
        assertEquals(0,api.created);assertThrows(IllegalStateException::class.java){NativeWakeStream(paths,config,{true})}
        assertThrows(IllegalStateException::class.java){NativeWakeStream(paths,config,{true},NativeWakeJNI)}
    }
}
