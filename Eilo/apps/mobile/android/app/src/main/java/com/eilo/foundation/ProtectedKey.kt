package com.eilo.foundation

import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Synchronous native borrower only. This allocation is erased; OS/JCA/hostile copies are not. */
internal class ProtectedKey(input:ByteArray):AutoCloseable {
    private val bytes=input.copyOf()
    private var live=true
    init{require(bytes.size==32)}
    @Synchronized fun borrow(body:(ByteArray)->Unit){check(live);body(bytes)}
    @Synchronized fun active()=live
    @Synchronized override fun close(){bytes.fill(0);live=false}
}
internal class WrappedDatabaseKey(iv:ByteArray,ciphertext:ByteArray) {
    private val nonce=iv.copyOf();private val sealed=ciphertext.copyOf()
    init{require(nonce.size==12 && sealed.size==48)}
    fun iv()=nonce.copyOf()
    fun ciphertext()=sealed.copyOf()
}
/** Explicit native worker API; no caller/UI/persistence installed. API35 floor avoids known
 * unlocked-device Keystore issues on older OS versions; unsupported policy fails closed.
 * OS auth window is five seconds; every app session must separately request explicit OS auth.
 * The wrapped ciphertext must later live in excluded app-private storage, never backup/JS.
 */
internal class AndroidProtectedKeyProvider(private val available:()->Boolean={false}) {
    private val alias="com.eilo.protected-memory.v1"
    private val aad="eilo:database-key:v1".toByteArray(Charsets.UTF_8)
    private fun eligible(){check(available() && Build.VERSION.SDK_INT>=35)}
    fun createWrappingKey() {
        if(Build.VERSION.SDK_INT<35)error("Protected key unavailable")
        eligible();val store=KeyStore.getInstance("AndroidKeyStore").apply{load(null)}
        check(!store.containsAlias(alias)) // Never replace a key protecting existing ciphertext.
        val spec=KeyGenParameterSpec.Builder(alias,KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setKeySize(256).setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).setRandomizedEncryptionRequired(true)
            .setUserAuthenticationRequired(true)
            .setUserAuthenticationParameters(5,KeyProperties.AUTH_BIOMETRIC_STRONG or KeyProperties.AUTH_DEVICE_CREDENTIAL)
            .setUnlockedDeviceRequired(true).build()
        eligible();KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore").apply{init(spec);generateKey()}
    }
    private fun key():SecretKey {
        eligible();val store=KeyStore.getInstance("AndroidKeyStore").apply{load(null)}
        return store.getKey(alias,null) as? SecretKey ?: error("Protected key unavailable")
    }
    fun wrap(raw:ProtectedKey):WrappedDatabaseKey {
        val cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.ENCRYPT_MODE,key());cipher.updateAAD(aad)
        var sealed:ByteArray?=null
        try {
            raw.borrow{eligible();sealed=cipher.doFinal(it)}
            eligible();return WrappedDatabaseKey(cipher.iv,sealed ?: error("Protected key unavailable"))
        }finally{sealed?.fill(0)}
    }
    fun load(wrapped:WrappedDatabaseKey):ProtectedKey {
        val cipher=Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE,key(),GCMParameterSpec(128,wrapped.iv()));cipher.updateAAD(aad)
        val clear=cipher.doFinal(wrapped.ciphertext())
        try {eligible();return ProtectedKey(clear)}finally{clear.fill(0)}
    }
}

/** Native OS-authenticated key result consumes one pre-auth ticket. No store or app caller. */
internal enum class PrivilegedOrigin {AUTHENTICATED_SCREEN,WAKE,VOICE,MODEL}
internal enum class PrivilegedOperation {READ_MEMORY,DELETE_HISTORY,CHANGE_PRIVACY}
internal class MemoryKeySession(private val clock:NativeClock=MonotonicClock(),
    private val scheduler:IdleScheduler=NativeIdleScheduler(),private val unlocked:()->Boolean={false}):PrivateEffectGate {
    class Ticket internal constructor(internal val epoch:java.util.UUID,internal val started:Long)
    private var epoch=java.util.UUID.randomUUID();private var pending=false
    private val copies=mutableListOf<ProtectedKey>()
    private var key:ProtectedKey?=null;private var opened=0L;private var expiry:IdleCancellation?=null
    @Synchronized fun beginAuthentication():Ticket? {
        revoke();if(!unlocked())return null;pending=true;return Ticket(epoch,clock.milliseconds())
    }
    /** Call only with the result of an explicit native OS authentication/provider request. */
    @Synchronized fun complete(ticket:Ticket,candidate:ProtectedKey):Boolean {
        val now=clock.milliseconds()
        if(!pending || ticket.epoch!=epoch || !unlocked() || !candidate.active() || now<ticket.started || now-ticket.started>=30_000){candidate.close();if(ticket.epoch==epoch && pending)revoke();return false}
        pending=false;key=candidate;opened=now;val accepted=epoch
        expiry=scheduler.schedule(60_000){synchronized(this){if(epoch==accepted)revoke()}}
        return true
    }
    @Synchronized override fun allows(effect:PrivateEffect):Boolean {
        val now=clock.milliseconds()
        if(!unlocked() || key?.active()!=true || now<opened || now-opened>=60_000){revoke();return false};return true
    }
    @Synchronized fun copyForNativeUse():ProtectedKey {
        check(allows(PrivateEffect.READ_MEMORY) && copies.size<8)
        var result:ProtectedKey?=null;key!!.borrow{result=ProtectedKey(it)}
        return result!!.also{copies.add(it)}
    }
    /** Origin is selected by trusted native dispatch, never derived from voice/model text. */
    @Synchronized fun allowsPrivilegedRequest(origin:PrivilegedOrigin,operation:PrivilegedOperation):Boolean =
        when(operation) {
            PrivilegedOperation.READ_MEMORY,PrivilegedOperation.DELETE_HISTORY,PrivilegedOperation.CHANGE_PRIVACY ->
                origin==PrivilegedOrigin.AUTHENTICATED_SCREEN && allows(PrivateEffect.READ_MEMORY)
        }
    override fun invalidate(){revoke()}
    @Synchronized fun revoke(){epoch=java.util.UUID.randomUUID();pending=false;expiry?.cancel();expiry=null;copies.forEach{it.close()};copies.clear();key?.close();key=null}
}
