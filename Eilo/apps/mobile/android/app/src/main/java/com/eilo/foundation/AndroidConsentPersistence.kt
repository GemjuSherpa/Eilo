package com.eilo.foundation
import android.content.Context
internal class AndroidConsentPersistence(context:Context):ConsentPersistence {
 private val preferences=context.getSharedPreferences("local_consent",Context.MODE_PRIVATE)
 override fun load():ConsentRecord? {
  if(preferences.all.keys.any { it !in setOf("version","historyChoice","disclosureVersion","backgroundConsent","volume") }) return null
  val choice=HistoryChoice.entries.firstOrNull { it.wire==preferences.getString("historyChoice","none") } ?: return null
  return ConsentRecord(preferences.getInt("version",1),choice,preferences.getInt("disclosureVersion",0),preferences.getBoolean("backgroundConsent",false),preferences.getInt("volume",100))
 }
 override fun save(record:ConsentRecord)=preferences.edit().putInt("version",record.version).putString("historyChoice",record.historyChoice.wire)
  .putInt("disclosureVersion",record.disclosureVersion).putBoolean("backgroundConsent",record.backgroundConsent).putInt("volume",record.volume).commit()
}
