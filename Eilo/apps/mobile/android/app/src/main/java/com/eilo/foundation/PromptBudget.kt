package com.eilo.foundation

internal data class PromptPlan(val text:String,val promptTokens:Int,val recalledTokens:Int,val outputLimit:Int,val droppedHistory:Int,val droppedRecall:Int)
/** Native worker builder; the counter must be the current loaded model vocabulary.
 * Defaults fail closed. Fixed rules/latest utterance are never truncated. Oldest
 * conversation turns trim first; lowest-priority recall units trim from the end.
 */
internal object PromptBudget {
    fun recallText(units:List<String>):String = UntrustedMemory.section(units)
    fun build(latest:String,history:List<QwenTurn> = emptyList(),recall:List<String> = emptyList(),outputLimit:Int=256,memoryAllowed:Boolean=false,
        count:(String)->Int={throw IllegalStateException("tokenizer unavailable")}):PromptPlan {
        require(outputLimit in 1..256 && history.size<=32 && recall.size<=32 && latest.isNotBlank())
        QwenTemplate.data(latest);history.forEach{QwenTemplate.data(it.text)};recall.forEach{QwenTemplate.data(it)}
        val turns=history.toMutableList();val units=if(memoryAllowed)recall.toMutableList() else mutableListOf()
        fun measured(text:String):Int { val n=count(text);check(n in 1..32768);return n }
        fun recallCount():Int { if(units.isEmpty())return 0;val text=try{QwenTemplate.data(recallText(units))}catch(_:IllegalArgumentException){return 32768};return if(text.toByteArray(Charsets.UTF_8).size>16384)32768 else measured(text) }
        while(units.isNotEmpty() && recallCount()>512)units.removeAt(units.lastIndex)
        while(true){
            val context=turns + if(units.isEmpty())emptyList() else listOf(QwenTurn(QwenRole.USER,recallText(units)))
            val text=try{QwenTemplate.render(latest,context)}catch(_:IllegalArgumentException){null}
            val n=if(text==null)32768 else measured(text)
            if(text!=null && n+outputLimit<=4096)return PromptPlan(text,n,recallCount(),outputLimit,history.size-turns.size,recall.size-units.size)
            if(turns.isNotEmpty())turns.removeAt(0) else if(units.isNotEmpty())units.removeAt(units.lastIndex) else throw IllegalStateException("latest utterance exceeds context")
        }
    }
}
