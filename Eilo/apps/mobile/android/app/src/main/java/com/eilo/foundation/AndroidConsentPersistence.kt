package com.eilo.foundation
import android.content.Context
internal class AndroidConsentPersistence(context:Context):ConsentPersistence {
 private val preferences=context.getSharedPreferences("local_consent",Context.MODE_PRIVATE)
 override fun load():ConsentRecord? {
  val version=preferences.getInt("version",1)
  val legacy=setOf("version","historyChoice","disclosureVersion","backgroundConsent","volume")
  val allowed=if(version==1)legacy else if(version==2)legacy+setOf("displayText","displayImages","displayVideo","voiceOnly") else return null
  if(preferences.all.keys.any { it !in allowed }) return null
  val choice=HistoryChoice.entries.firstOrNull { it.wire==preferences.getString("historyChoice","none") } ?: return null
  return ConsentRecord(preferences.getInt("version",1),choice,preferences.getInt("disclosureVersion",0),preferences.getBoolean("backgroundConsent",false),preferences.getInt("volume",100),DisplayPreferences(preferences.getBoolean("displayText",true),preferences.getBoolean("displayImages",false),preferences.getBoolean("displayVideo",false),preferences.getBoolean("voiceOnly",false)))
 }
 override fun save(record:ConsentRecord)=preferences.edit().putInt("version",record.version).putString("historyChoice",record.historyChoice.wire)
  .putInt("disclosureVersion",record.disclosureVersion).putBoolean("backgroundConsent",record.backgroundConsent).putInt("volume",record.volume).putBoolean("displayText",record.display.text).putBoolean("displayImages",record.display.images).putBoolean("displayVideo",record.display.video).putBoolean("voiceOnly",record.display.voiceOnly).commit()
}
