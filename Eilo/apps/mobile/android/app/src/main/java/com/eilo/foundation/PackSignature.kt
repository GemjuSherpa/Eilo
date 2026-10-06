package com.eilo.foundation
import java.security.KeyFactory
import java.security.Signature
import java.security.interfaces.ECPublicKey
import java.security.spec.X509EncodedKeySpec
import java.security.MessageDigest

/** Proof is immutable and can only be produced by verification against configured trust. */
class VerifiedPack private constructor(val manifest: PackManifest, val keyId: String, payload: ByteArray, signature: ByteArray) {
    private val payload=payload.clone(); private val signature=signature.clone()
    fun signedPayload()=payload.clone()
    fun signatureBytes()=signature.clone()
    val digest: String get()=MessageDigest.getInstance("SHA-256").digest(payload).joinToString("") { "%02x".format(it) }
    companion object {
        fun verify(payload: ByteArray, signature: ByteArray, keyId: String, algorithm: String, trust: Map<String,ByteArray>, runtime: String, android: Int=35): VerifiedPack {
            require(algorithm=="ES256" && keyId.matches(Regex("[a-z0-9-]{1,64}")) && payload.size in 1..65536 && signature.size in 8..72)
            val data=payload.clone();val sig=signature.clone()
            val encoded=trust[keyId]?.clone() ?: error("signature")
            val key=KeyFactory.getInstance("EC").generatePublic(X509EncodedKeySpec(encoded)) as ECPublicKey
            require(key.params.order.toString(16)=="ffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551")
            val verifier=Signature.getInstance("SHA256withECDSA");verifier.initVerify(key);verifier.update(data);require(verifier.verify(sig))
            return VerifiedPack(PackManifest.parse(data,runtime,android),keyId,data,sig)
        }
    }
}
