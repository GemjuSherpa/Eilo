package com.eilo.foundation

enum class HistoryChoice(val wire:String) { NONE("none"), PRIVATE("private"), HISTORY("history") }
data class ConsentRecord(val version:Int=1,val historyChoice:HistoryChoice=HistoryChoice.NONE,val disclosureVersion:Int=0,val backgroundConsent:Boolean=false,val volume:Int=100)
interface ConsentPersistence { fun load():ConsentRecord?; fun save(record:ConsentRecord):Boolean }
/** Stores only versioned local choices; no account, transcript, key or audio content. */
class NativeConsentPolicy(private val persistence:ConsentPersistence,private val historyAvailable:()->Boolean={false}) {
 private var record:ConsentRecord = try { persistence.load()?.takeIf { it.version==1 && it.disclosureVersion in 0..1 && it.volume in 0..100 } ?: ConsentRecord() } catch (_:Exception) { ConsentRecord() }
 private var privateMode=true
 private var privateExplicit=false
 @Synchronized private fun save(value:ConsentRecord):Boolean = try { if(persistence.save(value)) { record=value;true } else false } catch (_:Exception) { false }
 @Synchronized fun chooseHistory(choice:HistoryChoice):Boolean {
  if(choice==HistoryChoice.NONE) return false
  if(!save(record.copy(historyChoice=choice))) return false
  privateMode=true;privateExplicit=choice==HistoryChoice.PRIVATE;return true
 }
 @Synchronized fun completeOnboarding():Boolean = record.historyChoice!=HistoryChoice.NONE && save(record.copy(disclosureVersion=1))
 @Synchronized fun canStart()=record.disclosureVersion==1 && record.historyChoice!=HistoryChoice.NONE && (record.historyChoice==HistoryChoice.PRIVATE || privateExplicit || (historyAvailable() && !privateMode))
 @Synchronized fun personalWritesAllowed()=record.historyChoice==HistoryChoice.HISTORY && !privateMode && historyAvailable()
 @Synchronized fun snapshot():Map<String,Any> = mapOf("version" to 1,"historyChoice" to record.historyChoice.wire,"onboardingComplete" to (record.disclosureVersion==1 && record.historyChoice!=HistoryChoice.NONE),"historyAvailable" to historyAvailable(),"historyEnabled" to personalWritesAllowed(),"backgroundConsent" to record.backgroundConsent,"privateSession" to privateMode,"volume" to record.volume)
}
