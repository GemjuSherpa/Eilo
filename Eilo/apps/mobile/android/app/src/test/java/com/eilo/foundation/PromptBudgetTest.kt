package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class PromptBudgetTest {
    private fun count(text:String)=text.toByteArray(Charsets.UTF_8).size
    @Test fun trimsOldestContextAndRecallWithoutChangingRulesOrLatest(){val p=PromptBudget.build("Latest request.",listOf(QwenTurn(QwenRole.USER,"old".repeat(1800)),QwenTurn(QwenRole.ASSISTANT,"Recent answer.")),listOf("r".repeat(300),"s".repeat(300)),count=::count)
        assertEquals(1,p.droppedHistory);assertEquals(1,p.droppedRecall);assertTrue(p.promptTokens+p.outputLimit<=4096);assertTrue(p.recalledTokens<=512);assertTrue(p.text.contains(QwenTemplate.RULES));assertTrue(p.text.contains("Latest request."));assertTrue(p.text.contains("Recent answer."));assertFalse(p.text.contains("oldold"))
    }
    @Test fun exactLimitsAndIrreducibleLatestAreEnforced(){val p=PromptBudget.build("Latest.",recall=listOf("Recall."),count={if(it.startsWith("Quoted context:"))512 else 3840});assertEquals(512,p.recalledTokens);assertEquals(4096,p.promptTokens+p.outputLimit)
        assertThrows(IllegalStateException::class.java){PromptBudget.build("x".repeat(4000),count=::count)};assertThrows(IllegalArgumentException::class.java){PromptBudget.build("Latest.",outputLimit=257,count=::count)}
    }
    @Test fun unavailableInvalidAndOversizedRecallFailOrTrim(){assertThrows(IllegalStateException::class.java){PromptBudget.build("Latest.")};assertThrows(IllegalStateException::class.java){PromptBudget.build("Latest.",count={0})};val p=PromptBudget.build("Latest.",recall=List(32){"r".repeat(600)},count=::count);assertEquals(32,p.droppedRecall);assertEquals(0,p.recalledTokens)}
    @Test fun loadedTokenizerGateAndScratchClear(){var borrowed:ByteArray?=null;val api=object:NativeLlmApi{
        override fun create()=7L;override fun load(handle:Long,descriptor:Int,threads:Int)=0;override fun countTokens(handle:Long,text:ByteArray,count:Int):Int{borrowed=text;return 12};override fun begin(handle:Long,prompt:ByteArray,count:Int,outputLimit:Int)=0;override fun next(handle:Long,output:ByteArray,count:IntArray)=0;override fun cancel(handle:Long){};override fun destroy(handle:Long){}
    };NativeLlmStream({true},api).use{it.load(31);assertEquals(12,it.countTokens("Generic fixture."));assertTrue(borrowed!!.all{b->b==0.toByte()});it.requestCancellation();assertThrows(LlmFailure::class.java){it.countTokens("Late.")}}
    }
}
