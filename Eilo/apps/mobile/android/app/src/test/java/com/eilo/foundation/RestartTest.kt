package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class RestartTest {
    @Test fun freshProcessCannotRestoreListeningFromPriorControllerOrGrantedPermission() {
        val prior=testController(); prior.dispatch(ControllerEvent.START); val old=prior.token()!!
        for (launchKind in listOf("relaunch", "reboot", "restored installation")) {
            val spy=EffectsSpy(); val permission=FakePermission(); val fresh=testController(effects=spy,permission=permission)
            assertEquals(launchKind,ControllerState.STOPPED,fresh.state()); assertEquals(0,spy.started); assertEquals(0,permission.requests)
            assertFalse(fresh.releaseSpeech(old,"old process")); assertNull(fresh.token())
            fresh.bindPermissionAdapter(permission); assertEquals(0,spy.started); assertEquals(ControllerState.STOPPED,fresh.state())
        }
    }
    @Test fun snapshotHasOnlyOpaqueMetadataAndTypedErrors() {
        val c=testController(); val snapshot=c.snapshot()
        assertEquals(setOf("version","state","sessionId","operationId","generation","privacyEpoch"),snapshot.keys)
        assertEquals("stopped",snapshot["state"]); java.util.UUID.fromString(snapshot["sessionId"] as String)
        c.dispatch(ControllerEvent.START); c.dispatch(ControllerEvent.FAILURE,SafeError.TIMEOUT,c.token())
        assertEquals("timeout",c.snapshot()["errorCode"])
    }
}
