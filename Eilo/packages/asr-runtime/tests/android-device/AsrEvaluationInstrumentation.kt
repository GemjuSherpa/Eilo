package com.eilo.foundation
import android.app.Instrumentation
import android.os.Bundle
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.MessageDigest
import org.json.JSONArray
import org.json.JSONObject

/** Explicit synthetic Debug runner. Not registered or packaged in normal builds. */
class AsrEvaluationInstrumentation:Instrumentation(){
  override fun onCreate(arguments:Bundle?){super.onCreate(arguments);start()}
  override fun onStart(){
    val context=targetContext;val work=File(context.filesDir,"asr-evaluation");val report=File(context.filesDir,"asr-android-results.json")
    work.deleteRecursively();report.delete();val result=Bundle();var passed=false
    try {
      fun copy(path:String){val destination=File(work,path);destination.parentFile!!.mkdirs();context.assets.open("asr-evaluation/$path").use{input->destination.outputStream().use{input.copyTo(it)}}}
      fun verify(path:String,hash:String){check(MessageDigest.getInstance("SHA-256").digest(File(work,path).readBytes()).joinToString(""){"%02x".format(it)}==hash)}
      copy("provenance.json");copy("fixtures.json")
      val p=JSONObject(File(work,"provenance.json").readText());val model=p.getJSONObject("model");val directory=model.getString("directory");val files=model.getJSONArray("files")
      for(i in 0 until files.length()){val item=files.getJSONObject(i);val path="$directory/${item.getString("file")}";copy(path);verify(path,item.getString("local_sha256"))}
      val fixtures=JSONObject(File(work,"fixtures.json").readText()).getJSONArray("cases")
      val api=NativeAsrJni.loadVerified(listOf("onnxruntime","moonshine","eilo_asr_jni").map{File(context.applicationInfo.nativeLibraryDir,System.mapLibraryName(it)).absolutePath},{true})
      check(api.accept(0, floatArrayOf(0f),1)==-1 && api.text(0,false)==null);api.destroy(0)
      fun controller()=NativeController(effects=object:ControllerEffects{override fun startCapture()=true;override fun playClause(clause:String){};override fun cancelWork(){};override fun releaseCapture(){};override fun clearVolatileContext(){}},permission=object:MicrophonePermissionAdapter{override fun status()=MicrophonePermission.GRANTED;override fun request(completion:(MicrophonePermission)->Unit){completion(status())}},models=ModelReadinessAdapter{ModelStatus.READY})
      val cases=JSONArray()
      for(i in 0 until fixtures.length()){
        val item=fixtures.getJSONObject(i);val path="fixtures/${item.getString("file")}";copy(path);verify(path,item.getString("sha256"))
        val raw=File(work,path).readBytes();val bytes=ByteBuffer.wrap(raw).order(ByteOrder.LITTLE_ENDIAN)
        check(bytes.int==0x46464952);bytes.int;check(bytes.int==0x45564157)
        var offset=-1;var length=0
        while(bytes.remaining()>=8){val kind=bytes.int;val size=bytes.int;check(size>=0 && size<=bytes.remaining());if(kind==0x20746d66){check(size>=16 && bytes.short.toInt()==1 && bytes.short.toInt()==1 && bytes.int==16000);bytes.int;bytes.short;check(bytes.short.toInt()==16);bytes.position(bytes.position()+size-16)}else if(kind==0x61746164){offset=bytes.position();length=size;break}else bytes.position(bytes.position()+size);if(size%2==1)bytes.get()}
        check(offset>=0 && length%2==0 && length/2==item.getInt("samples") && length/2<=480000)
        val c=controller();check(c.dispatch(ControllerEvent.START));check(c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token()));val token=c.token()!!
        val a=StreamingAsr(token,{!token.cancelled},{NativeAsrStream(File(work,directory).absolutePath,{true},api)})
        val scratch=ShortArray(320);var frames=0;bytes.position(offset)
        while(bytes.position()<offset+length){val count=minOf(320,(offset+length-bytes.position())/2);repeat(count){scratch[it]=bytes.short};check(a.accept(scratch,count));scratch.fill(0);if(++frames%10==0)check(a.poll()!=null)}
        val final=a.poll(true);check(final!=null && final.final);check(a.poll(true)==null)
        val cancelled=StreamingAsr(token,{!token.cancelled},{NativeAsrStream(File(work,directory).absolutePath,{true},api)});check(cancelled.accept(ShortArray(320),320));c.stop();check(cancelled.poll(true)==null)
        cases.put(JSONObject().put("id",item.getString("id")).put("slice",item.getString("slice")).put("reference",item.getString("reference")).put("transcript",final!!.text).put("stale_final_rejected",true));raw.fill(0)
      }
      report.writeText(JSONObject().put("platform","Android API35 ARM64 emulator / ART JNI / synthetic only").put("cases",cases).put("physical","NOT RUN").toString(2))
      result.putString("eilo_asr_evaluation","PASS");passed=true
    }catch(_:Throwable){report.delete();result.putString("eilo_asr_evaluation","FAIL")}
    finally{if(!work.deleteRecursively()){passed=false;report.delete();result.putString("eilo_asr_evaluation","FAIL")}}
    finish(if(passed)-1 else 0,result)
  }
}
