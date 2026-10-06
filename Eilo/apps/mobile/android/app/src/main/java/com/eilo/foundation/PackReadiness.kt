package com.eilo.foundation
enum class ModelStatus(val wireValue: String) { READY("ready"), MISSING("missing"), INCOMPATIBLE("incompatible"), CORRUPT("corrupt"), INCOMPLETE("incomplete"), UNSUPPORTED("unsupported"), OFFLINE_VOICE_MISSING("offline_voice_missing") }
fun interface ModelReadinessAdapter { fun status(): ModelStatus }
class MissingModelReadiness : ModelReadinessAdapter { override fun status()=ModelStatus.MISSING }
/** Hash/signature checks run on installer worker; status read never does disk/network work. */
class PackReadiness(private val store: PackStore) : ModelReadinessAdapter {
 @Volatile private var value=ModelStatus.MISSING
 @Volatile private var epoch: java.util.UUID?=null
 override fun status()=if(epoch==store.epoch())value else ModelStatus.MISSING
 fun invalidate() { epoch=null;value=ModelStatus.MISSING }
 @Synchronized fun refresh(configurationSupported: Boolean=false,offlineVoice: Boolean=false): ModelStatus {
  val before=store.epoch()
  val result=if(!configurationSupported)ModelStatus.UNSUPPORTED else try {
   val p=store.active()
   when { p==null -> ModelStatus.MISSING; !p.manifest.artifacts.map { it.role }.toSet().containsAll(setOf("llm","asr","wake","vad")) -> ModelStatus.INCOMPLETE; !offlineVoice -> ModelStatus.OFFLINE_VOICE_MISSING; else -> ModelStatus.READY }
  } catch (_: PackIncompatibleException) { ModelStatus.INCOMPATIBLE } catch (_: Exception) { ModelStatus.CORRUPT }
  value=result;epoch=before
  return status()
 }
}
