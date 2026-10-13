package com.eilo.foundation

import org.junit.Assert.*
import org.junit.Test

class OfflineVoiceRegistryTest {
    private fun voice(id:String="en-au", installed:Boolean=true, network:Boolean?=false, verified:Boolean=false) = OfflineVoice(id,"en-AU",installed,network,verified)
    @Test fun missingNetworkUnknownAndUninstalledNeverSubstitute() {
        val r=OfflineVoiceRegistry(); val gate=VoiceAwareReadiness(ModelReadinessAdapter{ModelStatus.READY},r)
        for (values in listOf(emptyList(),listOf(voice(network=true)),listOf(voice(installed=false)),listOf(voice(network=null)))) {
            assertFalse(r.refresh(values));assertNull(r.selection());assertEquals(ModelStatus.OFFLINE_VOICE_MISSING,gate.status())
        }
        assertTrue(r.refresh(listOf(voice())));assertEquals(ModelStatus.READY,gate.status())
        assertEquals(ModelStatus.MISSING,VoiceAwareReadiness(MissingModelReadiness(),r).status())
    }
    @Test fun exactSelectionAndRefreshRevokeOldVoice() {
        val r=OfflineVoiceRegistry();assertTrue(r.refresh(listOf(voice("en-us"),voice()),"en-au"));val old=r.selection()!!
        assertTrue(r.current(old));assertFalse(r.refresh(listOf(voice("en-us")),"en-au"));assertFalse(r.current(old))
        assertTrue(r.refresh(listOf(voice())));r.invalidate();assertFalse(r.ready())
    }
    @Test fun unknownRequiresEvidenceButNetworkVoiceStillFails() {
        val r=OfflineVoiceRegistry();assertTrue(r.refresh(listOf(voice(network=null,verified=true))))
        assertFalse(r.refresh(listOf(voice(network=true,verified=true))))
    }
    @Test fun duplicateNonEnglishInvalidAndUnboundedSnapshotsFailClosed() {
        val r=OfflineVoiceRegistry();assertFalse(r.refresh(listOf(voice(),voice())))
        assertFalse(r.refresh(List(129){voice("v-$it")}));assertFalse(r.refresh(listOf(voice("invalid/voice"))))
        assertFalse(r.refresh(listOf(voice().copy(language="fr-FR"))))
    }
}
