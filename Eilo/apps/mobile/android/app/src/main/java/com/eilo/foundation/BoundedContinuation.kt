package com.eilo.foundation
import java.util.UUID
import java.lang.ref.WeakReference
import java.util.concurrent.atomic.AtomicBoolean

internal data class ContinuationChunk(val id:UUID,val index:Int,val plan:PromptPlan)
/** Explicit native worker policy, not an automatic generation loop. At most four
 * approved chunks of <=256 generated tokens (<=1024 total); every prompt <=4096.
 * Per-chunk output must already pass non-thinking and S07 policy. No app caller.
 * Stop publishes requestCancellation without a worker join; worker returns clear
 * borrowed references. Stale tokens permanently reject later chunks.
 * Reference release does not certify String/vendor-memory erasure.
 */
internal class BoundedContinuation private constructor(
    private val token:GenerationToken,latest:String,history:List<QwenTurn>,recall:List<String>,
    private val memoryAllowed:Boolean,private val allowed:(GenerationToken)->Boolean,
) {
    private var latest:String?=latest
    private val turns=history.toMutableList()
    private val recall=recall.toMutableList()
    private var pending:ContinuationChunk?=null
    private var completed=0
    var totalGenerated=0;private set
    private var closed=false
    private val cancelled=AtomicBoolean(false)
    companion object {
        fun create(controller:NativeController,token:GenerationToken,latest:String,history:List<QwenTurn> = emptyList(),recall:List<String> = emptyList(),
            requestedLonger:Boolean=false,memoryAllowed:Boolean=false,allowed:(GenerationToken)->Boolean={false}):BoundedContinuation? {
            if(!requestedLonger || token.cancelled || !allowed(token) || history.size>32 || recall.size>32)return null
            val policy=BoundedContinuation(token,latest,history,recall,memoryAllowed,allowed)
            val weak=WeakReference(policy)
            return if(controller.prepareContinuation(token){weak.get()?.requestCancellation()})policy else null
        }
    }
    private fun current():Boolean = !closed && !cancelled.get() && !token.cancelled && allowed(token) && !cancelled.get() && !token.cancelled
    /** The current loaded model tokenizer is supplied afresh for each native chunk. */
    fun next(count:(String)->Int):ContinuationChunk? {
        if(!current()){cancel();return null};if(pending!=null)return null
        if(completed>=4){cancel();return null}
        try {
            val original=latest ?: return null
            val request=if(completed==0)original else original+"\nContinue the requested answer from the previous approved chunk without repeating."
            val plan=PromptBudget.build(request,turns,recall,memoryAllowed=memoryAllowed,count=count)
            if(completed>0 && plan.droppedHistory>=turns.size){cancel();return null}
            repeat(plan.droppedHistory){turns.removeAt(0)};repeat(plan.droppedRecall){recall.removeAt(recall.lastIndex)}
            if(!current()){cancel();return null}
            return ContinuationChunk(UUID.randomUUID(),completed+1,plan).also{pending=it}
        }catch(_:Exception){cancel();return null}
    }
    /** One exact pending ticket, native policy approval, and actual generated count.
     * Returned true means accepted, never an instruction to auto-generate again. */
    fun complete(chunk:ContinuationChunk,text:String,generatedTokens:Int,approved:Boolean=false):Boolean {
        if(!current() || pending!==chunk || !approved || generatedTokens !in 1..256 || text.isBlank() || text.toByteArray(Charsets.UTF_8).size>4096 || text.any{it=='\u0000' || it=='<' || it=='>'}){cancel();return false}
        totalGenerated+=generatedTokens;completed++;pending=null
        if(completed==4){cancel();return true}
        if(turns.size==32)turns.removeAt(0)
        turns.add(QwenTurn(QwenRole.ASSISTANT,text));if(!current()){cancel();return false};return true
    }
    fun requestCancellation(){cancelled.set(true)}
    /** Worker-only cleanup; never join/count from the controller cancellation hook. */
    fun cancel(){requestCancellation();closed=true;latest=null;turns.clear();recall.clear();pending=null}
}
