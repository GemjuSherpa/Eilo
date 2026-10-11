package com.eilo.foundation

import android.app.Instrumentation
import android.os.Bundle
import java.io.File
import java.security.MessageDigest
import org.json.JSONObject

/** Invocation-only Debug instrumentation. Never registered in the normal app manifest. */
class WakeEvaluationInstrumentation:Instrumentation() {
    override fun onCreate(arguments:Bundle?) { super.onCreate(arguments);start() }
    override fun onStart() {
        val context=targetContext
        val work=File(context.filesDir,"wake-evaluation")
        val report=File(context.filesDir,"wake-android-results.json")
        report.delete();work.deleteRecursively()
        val result=Bundle();var passed=false
        try {
            fun copy(path:String) {
                val destination=File(work,path);destination.parentFile!!.mkdirs()
                context.assets.open("wake-evaluation/$path").use { source -> destination.outputStream().use { source.copyTo(it) } }
            }
            fun verify(path:String,hash:String) {
                val digest=MessageDigest.getInstance("SHA-256")
                File(work,path).inputStream().use { input -> val buffer=ByteArray(8192);try { while(true) { val count=input.read(buffer);if(count<0)break;digest.update(buffer,0,count) } } finally {buffer.fill(0)} }
                check(digest.digest().joinToString("") { "%02x".format(it) }==hash)
            }
            copy("provenance.json");copy("tests/fixtures/manifest.json")
            val provenance=JSONObject(File(work,"provenance.json").readText())
            val model=provenance.getJSONObject("model");val directory=model.getString("directory")
            val files=model.getJSONArray("files")
            for(i in 0 until files.length()) {
                val item=files.getJSONObject(i);val path="$directory/${item.getString("path")}"
                copy(path);verify(path,item.getString("sha256"))
            }
            val fixtures=JSONObject(File(work,"tests/fixtures/manifest.json").readText()).getJSONArray("fixtures")
            for(i in 0 until fixtures.length()) {
                val item=fixtures.getJSONObject(i);val path="fixtures/${item.getString("file")}"
                copy(path);verify(path,item.getString("sha256"))
            }
            val runtime=NativeWakeRuntime();val api=runtime.load()
            check(api===NativeWakeJNI && runtime.load()===api && NativeWakeJNI.runtimeCompatible())
            val syntheticController={NativeController(
                effects=object:ControllerEffects {
                    override fun startCapture()=true
                    override fun playClause(clause:String) {}
                    override fun cancelWork() {}
                    override fun releaseCapture() {}
                    override fun clearVolatileContext() {}
                },
                permission=object:MicrophonePermissionAdapter {
                    override fun status()=MicrophonePermission.GRANTED
                    override fun request(completion:(MicrophonePermission)->Unit) { completion(status()) }
                },models=ModelReadinessAdapter { ModelStatus.READY })}
            WakeRuntimeEvaluation.run(work,work,api!!,syntheticController,
                "sherpa-onnx 1.13.8 Android arm64-v8a",
                "Android API35 emulator ART + packaged JNI + Kotlin controller; synthetic capture/readiness only",
                "PASS: Android System.loadLibrary and linked version probe",report)
            result.putString("eilo_wake_evaluation","PASS")
            passed=true
        } catch (_:Throwable) {
            report.delete();result.putString("eilo_wake_evaluation","FAIL")

        } finally {
            if(!work.deleteRecursively()) { passed=false;report.delete();result.putString("eilo_wake_evaluation","FAIL") }
        }
        finish(if(passed)-1 else 0,result)
    }
}
