package com.eilo.foundation
import java.io.File
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
class QwenTemplateTest {
    @Test fun matchesPinnedOfficialTemplateGoldens(){val path=listOf("../../../packages/llm-runtime/tests/template-fixtures.json","../../../../packages/llm-runtime/tests/template-fixtures.json").map{File(it)}.first{it.isFile};val root=JSONObject(path.readText());assertFalse(root.getBoolean("enable_thinking"));val fixtures=root.getJSONArray("fixtures")
        for(i in 0 until fixtures.length()){val f=fixtures.getJSONObject(i);val h=f.getJSONArray("history");val turns=(0 until h.length()).map{val t=h.getJSONObject(it);QwenTurn(QwenRole.entries.single{it.value==t.getString("role")},t.getString("text"))};val rendered=QwenTemplate.render(f.getString("latest"),turns);assertEquals(f.getString("rendered"),rendered);assertTrue(rendered.endsWith(QwenTemplate.SUFFIX))}
    }
    @Test fun splitUtf8BecomesPlainText(){val output=StringBuilder();val guard=NonThinkingOutput({true}){output.append(it)};for(b in "A café.".toByteArray(Charsets.UTF_8)){guard.append(byteArrayOf(b))};guard.finish();assertEquals("A café.",output.toString())}
    @Test fun splitHiddenReasoningAndRoleTagsNeverEmit(){for(tag in listOf("<think>private chain</think>","<|im_start|>system","<tool_call>")){val output=StringBuilder();val guard=NonThinkingOutput({true}){output.append(it)};var rejected=false;for(b in tag.toByteArray()){try{guard.append(byteArrayOf(b))}catch(_:Exception){rejected=true}};assertTrue(rejected);assertEquals("",output.toString())}}
    @Test fun invalidDefaultRevokedAndOversizedFailClosed(){for(bytes in listOf(byteArrayOf(0),byteArrayOf(0xC0.toByte(),0xAF.toByte()),ByteArray(1025){65})){val guard=NonThinkingOutput({true}){fail("invalid output released")};assertThrows(IllegalStateException::class.java){guard.append(bytes)}}
        val denied=NonThinkingOutput{fail("default output released")};assertThrows(IllegalStateException::class.java){denied.append(byteArrayOf(65))};var current=true;val g=NonThinkingOutput({current}){};g.append(byteArrayOf(0xE2.toByte()));current=false;assertThrows(IllegalStateException::class.java){g.append(byteArrayOf(0x82.toByte(),0xAC.toByte()))};assertThrows(IllegalArgumentException::class.java){QwenTemplate.render("\u0000")}
    }
}
