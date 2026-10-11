package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class NativeAsrStreamTest {
    private class Api:NativeAsrApi {
        var closes=0;var bytes="hello".toByteArray();var after:()->Unit={}
        override fun create(directory:String)=1L
        override fun accept(handle:Long,pcm:FloatArray,count:Int):Int{after();return 0}
        override fun text(handle:Long,finish:Boolean):ByteArray{after();return bytes}
        override fun destroy(handle:Long){closes++}
    }
    @Test fun verifiedNativeTextIsDecodedAndBorrowedOutputIsErased(){val p=Api();val s=NativeAsrStream("/synthetic",{true},p);assertEquals("hello",s.text(false));assertTrue(p.bytes.all{it==0.toByte()});s.close();s.close();assertEquals(1,p.closes)}
    @Test fun revokeDuringDecodeCannotReleaseTextAndInvalidUtf8Closes(){val p=Api();var valid=true;val s=NativeAsrStream("/synthetic",{valid},p);p.after={valid=false};try{s.text(true);fail()}catch(_:IllegalStateException){};assertEquals(1,p.closes);assertTrue(p.bytes.all{it==0.toByte()})
        val invalid=Api();invalid.bytes=byteArrayOf(0xc0.toByte(),0x80.toByte());val other=NativeAsrStream("/synthetic",{true},invalid);try{other.text(false);fail()}catch(_:IllegalStateException){};assertEquals(1,invalid.closes)
    }
    @Test fun defaultsCannotOpenAndInvalidSampleRevokes(){try{NativeAsrStream("/synthetic",{true});fail()}catch(_:IllegalStateException){};val p=Api();val s=NativeAsrStream("/synthetic",{true},p);try{s.accept(floatArrayOf(Float.NaN),1);fail()}catch(_:IllegalStateException){};assertEquals(1,p.closes)}
}
