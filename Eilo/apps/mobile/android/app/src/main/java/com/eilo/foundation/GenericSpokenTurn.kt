package com.eilo.foundation
import java.util.concurrent.Executor

internal data class GenericReplyRequest(val latest:String,val history:List<QwenTurn> = emptyList())
internal fun interface GenericReplyStarter {fun start(token:GenerationToken,request:GenericReplyRequest,consume:(ByteArray,Int)->Unit,complete:(LlmJobResult)->Unit):Boolean}
/** Native asynchronous seam; no JS/history storage, microphone or readiness override. */
internal class GenericSpokenTurn(private val controller:NativeController,private val token:GenerationToken,private val sink:NativeClauseSink,private val configured:Boolean=false,private val starter:GenericReplyStarter=GenericReplyStarter{_,_,_,_->false}) {
    private var user="";private var reply=""
    private var submitted=false
    private var queue:NativeClauseQueue?=null
    private var output:NonThinkingOutput?=null
    fun submit(final:AsrText,confidence:Float?,ambiguous:Boolean=false,overlap:Boolean=false):Boolean = synchronized(controller) {
        if(!configured || submitted || !final.final || !controller.recognitionAllowed(token))return@synchronized false
        submitted=true
        val request=when(val decision=RecognitionPolicy.decide(final.text,confidence,ambiguous,overlap)){is RecognitionDecision.Conversation->decision.text;RecognitionDecision.Clarify->RecognitionPolicy.CLARIFICATION}
        val history=controller.genericContext(token) ?: return@synchronized false
        user=if(request==RecognitionPolicy.CLARIFICATION)"" else request
        if(!controller.dispatch(ControllerEvent.ENDPOINT,token=token))return@synchronized false
        val policy=NativeSpeechPolicy(controller,token,true)
        val q=NativeClauseQueue.create(controller,token,sink,completed={t->controller.recordGenericTurn(t,user,reply);user="";reply=""},cleared={user="";reply="";output?.cancel()},authorized=policy::allows) ?: return@synchronized false
        queue=q
        val fixed=if(request==RecognitionPolicy.CLARIFICATION)request else if(DangerPolicy.recognizes(request))DangerPolicy.RESPONSE else CapabilityPolicy.response(request)
        if(fixed!=null){reply=fixed;return@synchronized q.enqueue(fixed) && q.seal()}
        val guardOutput=NonThinkingOutput({!token.cancelled}){check(reply.toByteArray().size+it.toByteArray().size<=4096);reply+=it;if(!q.append(it))throw IllegalStateException("speech unavailable")};output=guardOutput
        val accepted=starter.start(token,GenericReplyRequest(request,history),{bytes,count->guardOutput.append(bytes,count)},{result->synchronized(controller){
            if(token.cancelled){guardOutput.cancel()}else try{check(result==LlmJobResult.COMPLETED);guardOutput.finish();check(q.seal())}catch(_:Exception){guardOutput.cancel();controller.dispatch(ControllerEvent.FAILURE,failure=SafeError.UNAVAILABLE,token=token)}
            output=null
        }})
        if(!accepted){guardOutput.cancel();controller.dispatch(ControllerEvent.FAILURE,failure=SafeError.UNAVAILABLE,token=token)}
        accepted
    }
    companion object {
        fun localReply(controller:NativeController,worker:Executor,store:PackStore,selection:LlmPackSelection,api:NativeLlmApi=UnavailableLlmApi,limit:Int=96)=GenericReplyStarter{token,request,consume,complete->
            LlmControllerJob.submit(controller,token,worker,store,selection,"Native generic request".toByteArray(),outputLimit=limit,api=api,request=request,completion=complete,consume=consume)!=null
        }
    }
}
