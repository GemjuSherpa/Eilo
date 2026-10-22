package com.eilo.foundation
import java.util.concurrent.Executor

/** Queued request references clear immediately on cancellation; not forensic erasure. */
internal class GenericReplyRequest(latest:String,history:List<QwenTurn> = emptyList()) {
    private var input=latest;private var turns=history.toList()
    val latest:String @Synchronized get()=input
    val history:List<QwenTurn> @Synchronized get()=turns.toList()
    @Synchronized fun cancel(){input="";turns=emptyList()}
}
internal fun interface GenericReplyStarter {fun start(token:GenerationToken,request:GenericReplyRequest,consume:(ByteArray,Int)->Unit,complete:(LlmJobResult)->Unit):Boolean}
/** Native asynchronous seam; no JS/history storage, microphone or readiness override. */
internal class GenericSpokenTurn(private val controller:NativeController,private val token:GenerationToken,private val sink:NativeClauseSink,private val configured:Boolean=false,private val starter:GenericReplyStarter=GenericReplyStarter{_,_,_,_->false}) {
    private var user="";private var reply=""
    private var submitted=false
    private var queue:NativeClauseQueue?=null
    private var output:NonThinkingOutput?=null
    private var pendingRequest:GenericReplyRequest?=null
    fun submit(final:AsrText,confidence:Float?,ambiguous:Boolean=false,overlap:Boolean=false):Boolean = synchronized(controller) {
        if(!configured || submitted || !final.final || !controller.recognitionAllowed(token))return@synchronized false
        submitted=true
        val request=when(val decision=RecognitionPolicy.decide(final.text,confidence,ambiguous,overlap)){is RecognitionDecision.Conversation->decision.text;RecognitionDecision.Clarify->RecognitionPolicy.CLARIFICATION}
        val history=controller.genericContext(token) ?: return@synchronized false
        user=if(request==RecognitionPolicy.CLARIFICATION)"" else request
        if(!controller.dispatch(ControllerEvent.ENDPOINT,token=token))return@synchronized false
        val policy=NativeSpeechPolicy(controller,token,true)
        val q=NativeClauseQueue.create(controller,token,sink,completed={t->controller.recordGenericTurn(t,user,reply);user="";reply=""},cleared={user="";reply="";output?.cancel();pendingRequest?.cancel();pendingRequest=null},authorized=policy::allows) ?: return@synchronized false
        queue=q
        val fixed=if(request==RecognitionPolicy.CLARIFICATION)request else if(DangerPolicy.recognizes(request))DangerPolicy.RESPONSE else CapabilityPolicy.response(request)
        if(fixed!=null){reply=fixed;return@synchronized q.enqueue(fixed) && q.seal()}
        val guardOutput=NonThinkingOutput({!token.cancelled}){check(reply.toByteArray().size+it.toByteArray().size<=4096);reply+=it;if(!q.append(it))throw IllegalStateException("speech unavailable")};output=guardOutput
        val ownedRequest=GenericReplyRequest(request,history);pendingRequest=ownedRequest
        val accepted=try{starter.start(token,ownedRequest,{bytes,count->guardOutput.append(bytes,count)},{result->synchronized(controller){
            ownedRequest.cancel();if(pendingRequest===ownedRequest)pendingRequest=null
            if(token.cancelled){guardOutput.cancel()}else try{check(result==LlmJobResult.COMPLETED);guardOutput.finish();check(q.seal())}catch(_:Exception){guardOutput.cancel();controller.dispatch(ControllerEvent.FAILURE,failure=SafeError.UNAVAILABLE,token=token)}
            output=null
        }})}catch(_:Exception){false}
        if(!accepted){ownedRequest.cancel();if(pendingRequest===ownedRequest)pendingRequest=null;guardOutput.cancel();output=null;controller.dispatch(ControllerEvent.FAILURE,failure=SafeError.UNAVAILABLE,token=token)}
        accepted
    }
    companion object {
        /** Only a confirmed activation and current native separation lease replace speech. */
        fun replacing(activation:InterruptionActivation,controller:NativeController,sink:NativeClauseSink,configured:Boolean=false,verified:()->Boolean={false},starter:GenericReplyStarter=GenericReplyStarter{_,_,_,_->false}):GenericSpokenTurn? {
            if(!configured)return null
            val token=try{activation.apply(controller,verified)}catch(_:Exception){controller.stop();null} ?: return null
            return GenericSpokenTurn(controller,token,sink,true,starter)
        }
        fun localReply(controller:NativeController,worker:Executor,store:PackStore,selection:LlmPackSelection,api:NativeLlmApi=UnavailableLlmApi,limit:Int=96)=GenericReplyStarter{token,request,consume,complete->
            LlmControllerJob.submit(controller,token,worker,store,selection,"Native generic request".toByteArray(),outputLimit=limit,api=api,request=request,completion=complete,consume=consume)!=null
        }
    }
}
