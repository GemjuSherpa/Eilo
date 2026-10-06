package com.eilo.foundation

import org.json.JSONObject
import org.json.JSONTokener
import java.net.URI

/** Generic assets only. No request accepts conversation, identity or device identifiers. */
data class PackArtifact(val id: String, val filename: String, val role: String, val url: String, val sha256: String, val bytes: Long, val license: String, val licenseEvidence: String)
data class PackManifest(val packId: String, val revision: Long, val runtimeRevision: String, val minAndroid: Int, val minIos: Int, val artifacts: List<PackArtifact>) {
    companion object {
        private val header = setOf("schema", "packId", "revision", "runtimeRevision", "minAndroid", "minIos", "artifacts")
        private val fields = setOf("id", "filename", "role", "url", "sha256", "bytes", "license", "licenseEvidence")
        private fun keys(o: JSONObject) = o.keys().asSequence().toSet()
        private fun text(o: JSONObject, k: String): String { val v=o.get(k); require(v is String); return v }
        private fun integer(o: JSONObject,k: String): Long { val v=o.get(k); require(v is Int || v is Long); return (v as Number).toLong() }
        private fun matches(s: String, pattern: String) = s.matches(Regex(pattern))
        fun parse(payload: ByteArray, runtime: String, android: Int=35): PackManifest {
            require(payload.size in 1..65536)
            val raw=String(payload,Charsets.UTF_8)
            require(raw.toByteArray(Charsets.UTF_8).contentEquals(payload))
            require(Regex("""(?:[{}\[\]:,]|"[\x20-\x21\x23-\x5b\x5d-\x7e]*"|[0-9]+|[ \t\r\n])+""").matches(raw) && !Regex(""",\s*[}\]]""").containsMatchIn(raw))
            val tokener=JSONTokener(raw);val o=tokener.nextValue() as? JSONObject ?: error("manifest");require(tokener.nextClean()=='\u0000'); require(keys(o)==header && integer(o,"schema")==1L)
            val pack=text(o,"packId");require(matches(pack,"[a-z0-9][a-z0-9-]{0,63}"))
            val revision=integer(o,"revision");require(revision in 1..9007199254740991L)
            val rr=text(o,"runtimeRevision");require(matches(rr,"[a-f0-9]{40}"));if(rr!=runtime)throw PackIncompatibleException()
            val a=integer(o,"minAndroid");val i=integer(o,"minIos");require(a in 35..99 && i in 18..99);if(a>android)throw PackIncompatibleException()
            val list=o.getJSONArray("artifacts");require(list.length() in 1..16)
            val artifacts=(0 until list.length()).map { n ->
                val f=list.getJSONObject(n); require(keys(f)==fields)
                val id=text(f,"id");val name=text(f,"filename");val role=text(f,"role")
                require(matches(id,"[a-z0-9][a-z0-9-]{0,63}") && matches(name,"[a-z0-9][a-z0-9_-]{0,95}\\.(gguf|onnx|json|txt)"))
                require(role in setOf("llm","asr","wake","vad","license","tokenizer"))
                val url=text(f,"url");val u=URI(url)
                require(url.length<=2048 && u.scheme=="https" && u.host!=null && u.rawUserInfo==null && u.rawQuery==null && u.rawFragment==null && u.port in setOf(-1,443) && u.normalize()==u && !u.rawPath.contains('%') && !u.rawPath.contains('\\'))
                val hash=text(f,"sha256");val evidence=text(f,"licenseEvidence");require(matches(hash,"[a-f0-9]{64}") && matches(evidence,"[a-f0-9]{64}"))
                val size=integer(f,"bytes");require(size in 1..8_000_000_000L)
                val license=text(f,"license");require(license in setOf("Apache-2.0","MIT","BSD-3-Clause","CC0-1.0"))
                PackArtifact(id,name,role,url,hash,size,license,evidence)
            }
            require(artifacts.map { it.id }.toSet().size==artifacts.size && artifacts.map { it.filename }.toSet().size==artifacts.size)
            require(artifacts.sumOf { it.bytes }<=12_000_000_000L)
            // Reject duplicate/escaped keys identically on Android and Foundation parsers.
            val keyTokens=Regex("\"([^\"\\\\]*)\"\\s*:").findAll(raw).map { it.groupValues[1] }.toList()
            require(keyTokens.size==header.size+fields.size*artifacts.size)
            require(header.all { key -> keyTokens.count { it==key }==1 })
            require(fields.all { key -> keyTokens.count { it==key }==artifacts.size })
            return PackManifest(pack,revision,rr,a.toInt(),i.toInt(),java.util.Collections.unmodifiableList(artifacts.toList()))
        }
    }
}

class PackIncompatibleException : Exception()
