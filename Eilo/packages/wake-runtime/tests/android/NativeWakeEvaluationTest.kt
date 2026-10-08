package com.eilo.foundation

import org.junit.Assert.*
import org.junit.Test
import org.json.JSONObject
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** Explicit host-JVM evaluation only. Not part of the app's normal test source set. */
class NativeWakeEvaluationTest {
    private fun pcmBytes(file:File):ByteArray {
        val bytes=file.readBytes()
        try {
            val b=ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
            check(bytes.size>=12 && String(bytes,0,4,Charsets.US_ASCII)=="RIFF" && String(bytes,8,4,Charsets.US_ASCII)=="WAVE")
            var offset=12;var format=false
            while(offset+8<=bytes.size) {
                val tag=String(bytes,offset,4,Charsets.US_ASCII);val size=b.getInt(offset+4)
                check(size>=0 && size<=bytes.size-offset-8);val start=offset+8
                if(tag=="fmt ") {
                    check(size>=16 && b.getShort(start).toInt()==1 && b.getShort(start+2).toInt()==1 && b.getInt(start+4)==16000 && b.getShort(start+14).toInt()==16)
                    format=true
                }
                if(tag=="data") { check(format && size>0 && size%2==0);return bytes.copyOfRange(start,start+size) }
                offset=start+size+(size%2)
            }
            error("invalid fixture")
        } finally {bytes.fill(0)}
    }
    @Test fun realJNIAndKotlinDecoderAcceptFrozenSyntheticSet() {
        val root=File(System.getProperty("eilo.wake.root"))
        System.load(System.getProperty("eilo.wake.library"))
        val provenance=JSONObject(File(root,"provenance.json").readText())
        val cache=File(System.getProperty("eilo.wake.cache"))
        val model=File(cache,provenance.getJSONObject("model").getString("directory"))
        val paths=WakeModelPaths(File(model,"encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx").path,
            File(model,"decoder-epoch-12-avg-2-chunk-16-left-64.onnx").path,
            File(model,"joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx").path,File(model,"tokens.txt").path)
        val config=WakeConfiguration("HEY EILO",.125f,1.5f)
        val fixtures=JSONObject(File(root,"tests/fixtures/manifest.json").readText()).getJSONArray("fixtures")
        val report=JSONObject().put("runtime","sherpa-onnx 1.13.8 host macOS ARM64")
            .put("environment","Host JVM JNI + actual Kotlin binding/controller; not Android device execution")
            .put("microphone","not used").put("model_readiness","unchanged/unavailable")
        val cases=org.json.JSONArray();var wakes=0;var nonwakes=0
        for(index in 0 until fixtures.length()) {
            val fixture=fixtures.getJSONObject(index);val file=fixture.getString("file")
            val bytes=pcmBytes(File(cache,"fixtures/$file"))
            val buffer=ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN);val pcm=ShortArray(bytes.size/2){buffer.short}
            val stream=NativeWakeStream(paths,config,{true},NativeWakeJNI)
            var detections=0
            val frame=FloatArray(320)
            try {
                var offset=0
                while(offset<pcm.size) {
                    val count=minOf(frame.size,pcm.size-offset)
                    for(i in 0 until count)frame[i]=pcm[offset+i]/32768f
                    stream.accept(frame,count,16000)
                    if(stream.keyword().isNotEmpty()){detections++;stream.reset()}
                    frame.fill(0f);offset+=count
                }
            } finally { frame.fill(0f);stream.close() }
            assertThrows(IllegalStateException::class.java){stream.accept(floatArrayOf(0f),1,16000)}
            // Actual native controller integration, using explicit synthetic capture/readiness fixtures.
            val c=testController();c.dispatch(ControllerEvent.START);val token=c.token()!!
            val detector=WakeDetector(config,verified={true},open={NativeWakeStream(paths,it,{true},NativeWakeJNI)})
            assertTrue(detector.begin(token));var event:WakeActivation?=null
            try {
                var offset=0;val chunk=ShortArray(320)
                while(offset<pcm.size) {
                    val count=minOf(chunk.size,pcm.size-offset);pcm.copyInto(chunk,0,offset,offset+count)
                    detector.processPCM16(token,chunk,count,16000)?.let { event=it };chunk.fill(0);offset+=count
                }
                if(detections>0) { assertNotNull(event);assertTrue(event!!.apply(c));assertEquals(ControllerState.CAPTURING,c.state()) }
                else { assertNull(event);assertEquals(ControllerState.STANDBY,c.state()) }
                c.stop();event?.let{assertFalse(it.apply(c))};assertNull(detector.processPCM16(token,shortArrayOf(0),1,16000))
            } finally {detector.close();pcm.fill(0);bytes.fill(0)}
            val kind=fixture.getString("kind")
            if(kind=="wake"){assertEquals(file,1,detections);wakes++}
            if(kind=="nonwake"){assertEquals(file,0,detections);nonwakes++}
            cases.put(JSONObject().put("file",file).put("kind",kind).put("detections",detections).put("closed_input_rejected",true).put("controller_stop_rejected",true))
        }
        assertEquals(28,fixtures.length());assertEquals(11,wakes);assertEquals(15,nonwakes)
        // IDs are opaque and never reusable pointers. Invalid input disables the handle in JNI too.
        val old=NativeWakeJNI.create(paths,config);assertTrue(old>0)
        assertEquals(-1,NativeWakeJNI.process(old,floatArrayOf(0f),2,16000));NativeWakeJNI.destroy(old)
        assertEquals(-1,NativeWakeJNI.process(old,floatArrayOf(0f),1,16000))
        val fresh=NativeWakeJNI.create(paths,config);assertTrue(fresh>old)
        NativeWakeJNI.destroy(old);assertEquals(0,NativeWakeJNI.process(fresh,floatArrayOf(0f),1,16000))
        assertEquals(-1,NativeWakeJNI.process(fresh,floatArrayOf(Float.NaN),1,16000))
        assertEquals(-1,NativeWakeJNI.process(fresh,floatArrayOf(0f),1,16000));NativeWakeJNI.destroy(fresh)
        report.put("cases",cases).put("fixture_count",fixtures.length()).put("acoustic_acceptance","PASS ON SYNTHETIC SET ONLY")
            .put("jni_invalid_stale_handles","PASS")
        File(cache,"android/host-jni-results.json").writeText(report.toString(2)+"\n")
    }
}
