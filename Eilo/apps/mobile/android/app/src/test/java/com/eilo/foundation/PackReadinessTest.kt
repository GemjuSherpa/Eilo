package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
import java.nio.file.Files
class PackReadinessTest {
 @Test fun everyMissingUnsupportedReasonPreventsPromptAndCapture() {
  for(status in ModelStatus.entries.filter { it!=ModelStatus.READY }) {
   val spy=EffectsSpy();val permission=FakePermission(MicrophonePermission.NOT_REQUESTED);val c=NativeController(effects=spy,permission=permission,models=ModelReadinessAdapter { status })
   assertFalse(c.dispatch(ControllerEvent.START));assertEquals(0,spy.started);assertEquals(0,permission.requests);assertEquals(ControllerState.SETUP,c.state());assertEquals(status.wireValue,c.snapshot()["modelStatus"])
  }
 }
 @Test fun modelLossDuringPromptAndCaptureCannotStartOrPublish() {
  var status=ModelStatus.READY;val spy=EffectsSpy();val p=FakePermission(MicrophonePermission.NOT_REQUESTED);val c=NativeController(effects=spy,permission=p,models=ModelReadinessAdapter { status })
  c.dispatch(ControllerEvent.START);status=ModelStatus.CORRUPT;p.complete(MicrophonePermission.GRANTED);assertEquals(0,spy.started)
  status=ModelStatus.READY;c.modelsChanged();assertEquals(0,spy.started);spy.onStart={ status=ModelStatus.MISSING };assertFalse(c.dispatch(ControllerEvent.START));assertNull(c.token())
  spy.onStart=null;status=ModelStatus.READY;c.modelsChanged();c.dispatch(ControllerEvent.START);c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token());c.dispatch(ControllerEvent.ENDPOINT,token=c.token());val old=c.token()!!;status=ModelStatus.MISSING;assertFalse(c.releaseSpeech(old,"synthetic"));assertTrue(spy.clauses.isEmpty())
 }
 @Test fun signedLlmAloneCannotClaimCompletePipeline() {
  val root=Files.createTempDirectory("eilo-pack").toFile();val (p,trust)=PackFixtures.signed();val s=PackStore(java.io.File(root,"store"),trust,PackFixtures.runtime,setOf("c".repeat(64)));val gate=PackReadiness(s)
  try { assertEquals(ModelStatus.UNSUPPORTED,gate.refresh());assertEquals(ModelStatus.MISSING,gate.refresh(true,true));val f=java.io.File(root,"part");f.writeBytes(byteArrayOf(1,2,3,4));s.activate(p,listOf(VerifiedArtifact.verify(p,0,f)),PackCancellation());assertEquals(ModelStatus.INCOMPLETE,gate.refresh(true,true));s.file(p,0).writeBytes(byteArrayOf(9,9,9,9));assertEquals(ModelStatus.CORRUPT,gate.refresh(true,true)) } finally { root.deleteRecursively() }
 }
 @Test fun completePackRequiresOfflineVoiceAndActivationInvalidatesCachedReady() {
  val root=Files.createTempDirectory("eilo-pack").toFile()
  try {
   val o=org.json.JSONObject(String(PackFixtures.payload));val base=o.getJSONArray("artifacts").getJSONObject(0);val artifacts=org.json.JSONArray()
   for(role in listOf("llm","asr","wake","vad")) artifacts.put(org.json.JSONObject(base.toString()).put("id",role).put("role",role).put("filename","$role.onnx"))
   o.put("artifacts",artifacts);val(p,trust)=PackFixtures.signed(o.toString().toByteArray());val store=PackStore(java.io.File(root,"store"),trust,PackFixtures.runtime,setOf("c".repeat(64)))
   val f=java.io.File(root,"part");f.writeBytes(byteArrayOf(1,2,3,4));val proofs=p.manifest.artifacts.indices.map { VerifiedArtifact.verify(p,it,f) };store.activate(p,proofs,PackCancellation())
   val gate=PackReadiness(store);assertEquals(ModelStatus.OFFLINE_VOICE_MISSING,gate.refresh(true,false));assertEquals(ModelStatus.READY,gate.refresh(true,true))
   store.activate(p,proofs,PackCancellation());assertEquals(ModelStatus.MISSING,gate.status());assertEquals(ModelStatus.READY,gate.refresh(true,true))
   val incompatible=PackReadiness(PackStore(java.io.File(root,"store"),trust,"d".repeat(40),setOf("c".repeat(64))));assertEquals(ModelStatus.INCOMPATIBLE,incompatible.refresh(true,true))
  } finally { root.deleteRecursively() }
 }

}
