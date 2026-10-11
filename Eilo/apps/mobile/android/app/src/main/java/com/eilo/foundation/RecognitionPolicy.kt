package com.eilo.foundation

internal sealed class RecognitionDecision {
    object Clarify:RecognitionDecision()
    /** Conversational input only. This never confirms a personal memory fact. */
    class Conversation(val text:String):RecognitionDecision()
}
internal object RecognitionPolicy {
    const val CLARIFICATION="Could you say that again?"
    fun decide(text:String,confidence:Float?,ambiguous:Boolean=false,overlap:Boolean=false):RecognitionDecision {
        val trimmed=text.trim()
        return if(trimmed.isEmpty() || trimmed.toByteArray(Charsets.UTF_8).size>4096 ||
            trimmed.any{it=='\u0000' || (it.isISOControl() && it!='\n' && it!='\t')} ||
            confidence==null || !confidence.isFinite() || confidence !in .85f..1f || ambiguous || overlap)
            RecognitionDecision.Clarify else RecognitionDecision.Conversation(trimmed)
    }
}
