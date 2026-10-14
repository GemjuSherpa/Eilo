package com.eilo.foundation

/** Narrow English routing; no action, permission or network interfaces. */
internal object CapabilityPolicy {
    const val VERSION = "eilo-capabilities-1"
    const val RULES = " Be honest about uncertainty; ask a short clarification when needed. You cannot browse live news, make calls, take photos, control other apps, diagnose conditions, monitor danger or contact emergency services. Never claim you performed these actions or request new permissions. For current facts explain that you cannot verify live information. For health concerns encourage qualified professional help without a diagnosis."
    const val LIVE = "I cannot verify live information or browse current news. Please check a trusted current source."
    const val ACTION = "I cannot make calls, take photos or control other apps. You can use your phone's controls yourself."
    const val HEALTH = "I cannot diagnose a condition. A qualified health professional can help with health concerns."
    fun response(input:String):String? {
        val text=" "+input.lowercase(java.util.Locale.ROOT).split(Regex("[^\\p{L}\\p{N}]+")).filter{it.isNotEmpty()}.joinToString(" ")+" "
        if(listOf(" diagnose "," diagnosis "," symptoms ").any{text.contains(it)})return HEALTH
        if(listOf(" call "," phone "," photograph "," photo "," camera "," open app "," launch app ").any{text.contains(it)})return ACTION
        if(listOf(" latest "," current news "," news today "," live news "," browse "," search the web ").any{text.contains(it)})return LIVE
        return null
    }
}
