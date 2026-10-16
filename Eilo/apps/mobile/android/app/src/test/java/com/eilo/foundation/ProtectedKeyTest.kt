package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class ProtectedKeyTest {
    @Test fun closedKeyDeniesNativeBorrowAndErasesHeldOwnedReference() {
        val input=ByteArray(32){7};val key=ProtectedKey(input);input.fill(8)
        var held:ByteArray?=null;key.borrow{assertEquals(7,it[0].toInt());held=it}
        key.close();assertTrue(held!!.all{it==0.toByte()});assertFalse(key.active());key.close()
        assertThrows(IllegalStateException::class.java){key.borrow{fail("closed")}}
        assertThrows(IllegalArgumentException::class.java){ProtectedKey(ByteArray(31))}
    }
    @Test fun envelopeBoundsAndDefensiveCopies() {
        val iv=ByteArray(12){1};val sealed=ByteArray(48){2};val value=WrappedDatabaseKey(iv,sealed)
        iv.fill(0);sealed.fill(0);val copy=value.iv();copy.fill(0)
        assertEquals(1,value.iv()[0].toInt());assertEquals(2,value.ciphertext()[0].toInt())
        assertThrows(IllegalArgumentException::class.java){WrappedDatabaseKey(ByteArray(11),ByteArray(48))}
    }
    @Test fun deniedProviderNeverCreatesOrLoadsKeystore() {
        val p=AndroidProtectedKeyProvider()
        assertThrows(IllegalStateException::class.java){p.createWrappingKey()}
        assertThrows(IllegalStateException::class.java){p.load(WrappedDatabaseKey(ByteArray(12),ByteArray(48)))}
    }
}
