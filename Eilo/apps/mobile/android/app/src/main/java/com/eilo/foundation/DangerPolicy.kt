package com.eilo.foundation

/** Conservative English signals; no diagnosis, risk assessment or location. */
internal object DangerPolicy {
    const val VERSION="eilo-danger-1"
    const val RULES=" For explicit immediate danger, prioritize a brief supportive response directing the user to contact local emergency services now and a trusted person nearby. You cannot contact help or monitor safety. Do not ask for location or describe harmful methods. Never offer a safety guarantee."
    const val RESPONSE="I am sorry you are facing this. If you or someone else is in immediate danger, contact your local emergency services now; in Australia, call triple zero. If you can, ask someone you trust nearby to stay with you and help. I cannot contact help or monitor your safety."
    fun recognizes(input:String):Boolean {
        val text=" "+input.lowercase(java.util.Locale.ROOT).split(Regex("[^\\p{L}\\p{N}]+")).filter{it.isNotEmpty()}.joinToString(" ")+" "
        return listOf("kill myself", "end my life", "hurt myself", "harm myself", "suicide", "suicidal", "kill someone", "hurt someone", "immediate danger", "not safe", "being attacked", "overdose", "cannot breathe", "can t breathe").any{text.contains(" $it ")}
    }
}
