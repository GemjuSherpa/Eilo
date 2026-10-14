package com.eilo.foundation

/** Bounded English lexical screen; not semantic safety certification. */
internal class NativeSpeechPolicy(private val controller:NativeController,private val token:GenerationToken,private val configured:Boolean=false) {
    companion object { const val VERSION="eilo-speech-1" }
    fun allows(expected:GenerationToken,text:String):Boolean = synchronized(controller) {
        if(!configured || expected!==token || !controller.canApproveSpeech(token) || controller.speakerConfirmationRequired() || controller.snapshot()["state"] !in listOf(ControllerState.THINKING.wireValue,ControllerState.SPEAKING.wireValue) || text.isEmpty() || text.toByteArray(Charsets.UTF_8).size>1024 || text.any{it.code !in 32..126 && it.code !in listOf(10,13,8216,8217,8220,8221)})return@synchronized false
        val fixed=listOf(CapabilityPolicy.LIVE,CapabilityPolicy.ACTION,CapabilityPolicy.HEALTH,DangerPolicy.RESPONSE,RecognitionPolicy.CLARIFICATION,"I am Eilo, an AI companion.","Okay, take care.")
        val canonicalRefusals=listOf("I cannot pretend to be human or promise secrecy.","I cannot diagnose or assess your mental condition.","I do not have feelings, but I can offer support and companionship.","I cannot promise secrecy.","I am Eilo, an AI companion. I cannot pretend to be human or promise secrecy.","I am Eilo, an AI companion. I cannot diagnose or assess your mental condition.","I am Eilo, an AI companion. I do not have feelings, but I can offer support and companionship.","I am Eilo, an AI companion. I cannot promise secrecy.")
        if(text in fixed+canonicalRefusals)return@synchronized controller.canApproveSpeech(token)
        val words=text.lowercase(java.util.Locale.ROOT).split(Regex("[^a-z0-9]+"))
        val risks=setOf("diagnose", "diagnosis", "symptoms", "prescribe", "medicine", "medication", "pills", "overdose", "suicide", "suicidal", "kill", "weapon", "poison", "bleach", "hurt", "harm", "emergency", "monitor", "monitoring", "ambulance", "photo", "camera", "call", "called", "calling", "browse", "browsed", "browsing", "searched", "news", "confidential", "confidentiality", "secret", "secrecy", "human", "conscious", "consciousness", "feelings", "love")
        if(words.any{it in risks})return@synchronized false
        val normalized=" "+words.joinToString(" ")+" "
        if(listOf("only support", "only need me", "depend on me", "trust only me", "do not tell anyone", "don t tell anyone", "promise", "guarantee", "i have feelings", "i feel your", "i will always", "i am your therapist").any{normalized.contains(it)})return@synchronized false
        controller.canApproveSpeech(token)
    }
}
