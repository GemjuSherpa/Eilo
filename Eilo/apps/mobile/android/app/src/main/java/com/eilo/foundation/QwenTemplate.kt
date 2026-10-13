package com.eilo.foundation

internal enum class QwenRole(val value:String){USER("user"),ASSISTANT("assistant")}
internal data class QwenTurn(val role:QwenRole,val text:String)
/** Restricted no-tools subset of the pinned Qwen3 template, enable_thinking=false.
 * Only native fixed rules can become system content. No caller-supplied role strings.
 */
internal object QwenTemplate {
    const val RULES=PersonaPolicy.RULES
    const val SUFFIX="<|im_start|>assistant\n<think>\n\n</think>\n\n"
    fun data(text:String):String { require(!text.contains('\u0000') && text.toByteArray(Charsets.UTF_8).size<=16384);return text.replace("<","＜").replace(">","＞") }
    fun render(latest:String,history:List<QwenTurn> = emptyList()):String {
        require(latest.isNotBlank() && history.size<=32)
        val text=buildString {
            append("<|im_start|>system\n");append(RULES);append("<|im_end|>\n")
            for(turn in history){append("<|im_start|>");append(turn.role.value);append('\n');append(data(turn.text));append("<|im_end|>\n")}
            append("<|im_start|>user\n");append(data(latest));append("<|im_end|>\n");append(SUFFIX)
        }
        require(text.toByteArray(Charsets.UTF_8).size<=16384);return text
    }
}
/** Worker-confined raw-piece guard. Rejects all angle-markup (including split thinking,
 * role/tool tags), malformed UTF-8, NUL, revoked leases and oversized output. It grants
 * no speech rights: S07 still authorizes every emitted plain-text fragment.
 */
internal class NonThinkingOutput(private val current:()->Boolean={false},private val emit:(String)->Unit){
    private var pending=byteArrayOf();private var total=0;private var closed=false
    fun append(piece:ByteArray,count:Int=piece.size){
        try {
            check(!closed && current() && count in 1..1024 && count<=piece.size && total+count<=16384)
            total+=count;val bytes=pending+piece.copyOf(count);pending.fill(0);pending=byteArrayOf();var i=0
            try {
                while(i<bytes.size){
                    val lead=bytes[i].toInt() and 255
                    check(lead!=0 && lead!=60 && lead!=62)
                    val width=when(lead){in 1..127->1;in 194..223->2;in 224..239->3;in 240..244->4;else->error("invalid UTF-8")}
                    if(i+width>bytes.size){pending=bytes.copyOfRange(i,bytes.size);break}
                    val decoder=Charsets.UTF_8.newDecoder().onMalformedInput(java.nio.charset.CodingErrorAction.REPORT).onUnmappableCharacter(java.nio.charset.CodingErrorAction.REPORT)
                    decoder.decode(java.nio.ByteBuffer.wrap(bytes,i,width));i+=width
                }
                if(i>0){check(current());emit(String(bytes,0,i,Charsets.UTF_8));check(current())}
            }finally{bytes.fill(0)}
        }catch(_:Exception){cancel();throw IllegalStateException("output unavailable")}
    }
    fun finish(){try{check(!closed && current() && pending.isEmpty());closed=true}catch(_:Exception){cancel();throw IllegalStateException("output unavailable")}}
    fun cancel(){closed=true;pending.fill(0);pending=byteArrayOf()}
}
