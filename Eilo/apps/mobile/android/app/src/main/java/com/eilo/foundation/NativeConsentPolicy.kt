package com.eilo.foundation

enum class HistoryChoice(val wire:String) { NONE("none"), PRIVATE("private"), HISTORY("history") }
data class DisplayPreferences(val text:Boolean=true,val images:Boolean=false,val video:Boolean=false,val voiceOnly:Boolean=false)
data class ConsentRecord(val version:Int=2,val historyChoice:HistoryChoice=HistoryChoice.NONE,val disclosureVersion:Int=0,val backgroundConsent:Boolean=false,val volume:Int=100,val display:DisplayPreferences=DisplayPreferences())
interface ConsentPersistence { fun load():ConsentRecord?; fun save(record:ConsentRecord):Boolean }
/** Stores only versioned local choices; no account, transcript, key or audio content. */
class NativeConsentPolicy(private val persistence:ConsentPersistence,private val historyAvailable:()->Boolean={false}) {
 private var record:ConsentRecord = try { persistence.load()?.takeIf { it.version in 1..2 && it.disclosureVersion in 0..1 && it.volume in 0..100 } ?.copy(version=2) ?: ConsentRecord() } catch (_:Exception) { ConsentRecord() }
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
 @Synchronized fun choosePrivateSession(enabled:Boolean):Boolean {
  if(!enabled) return false // Protected history and its authentication are not available yet.
  privateMode=true;privateExplicit=true;return true
 }
 @Synchronized fun chooseVolume(volume:Int):Boolean = volume in 0..100 && save(record.copy(volume=volume))
 @Synchronized fun chooseBackground(enabled:Boolean,authenticated:Boolean):Boolean {
  if(enabled && (!authenticated || record.disclosureVersion!=1 || record.historyChoice==HistoryChoice.NONE)) return false
  return save(record.copy(backgroundConsent=enabled))
 }
 @Synchronized fun backgroundRequested()=record.backgroundConsent && record.disclosureVersion==1 && record.historyChoice!=HistoryChoice.NONE
 @Synchronized fun personalWritesAllowed()=record.historyChoice==HistoryChoice.HISTORY && !privateMode && historyAvailable()
 @Synchronized fun chooseDisplay(name:String,enabled:Boolean,authorized:Boolean):Boolean {
  if(!authorized) return false
  val d=record.display
  val next=when(name) { "displayText"->d.copy(text=enabled);"displayImages"->d.copy(images=enabled);"displayVideo"->d.copy(video=enabled);"voiceOnly"->d.copy(voiceOnly=enabled);else->return false }
  return save(record.copy(display=next))
 }
 @Synchronized fun snapshot():Map<String,Any> = mapOf("version" to 2,"display" to mapOf("text" to record.display.text,"images" to record.display.images,"video" to record.display.video,"voiceOnly" to record.display.voiceOnly),"historyChoice" to record.historyChoice.wire,"onboardingComplete" to (record.disclosureVersion==1 && record.historyChoice!=HistoryChoice.NONE),"historyAvailable" to historyAvailable(),"historyEnabled" to personalWritesAllowed(),"backgroundConsent" to record.backgroundConsent,"privateSession" to privateMode,"volume" to record.volume)
}
