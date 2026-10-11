package com.eilo.foundation

import org.junit.Assert.*
import org.junit.Test

/** Scripted native integration, not acoustic recognition or a production capture attachment. */
class TurnPipelineIntegrationTest {
    private class Backend : AsrStream {
        val received = mutableListOf<Float>()
        var closes = 0
        var onFinal: () -> Unit = {}
        override fun accept(pcm: FloatArray, count: Int) { repeat(count) { received.add(pcm[it]) } }
        override fun text(finish: Boolean): String { if (finish) onFinal(); return "What time is it?" }
        override fun close() { closes++ }
    }

    @Test fun boundedSuffixAndDuplicateFramesProduceOneFinalThenUnknownConfidenceClarifies() {
        val effects = EffectsSpy()
        val controller = testController(effects = effects)
        controller.dispatch(ControllerEvent.START)
        val handoff = WakeQuestionHandoff()
        repeat(14) { frame ->
            val value: Short = if (frame < 2) -16384 else 16384
            assertTrue(handoff.offer(ShortArray(320) { value }, 320, frame * 320L))
        }
        controller.dispatch(ControllerEvent.SPEECH_DETECTED, token = controller.token())
        val token = controller.token()!!
        val backend = Backend()
        val asr = StreamingAsr(token, { controller.recognitionAllowed(token) }, { backend })
        val endpoint = EndpointDetector()
        var final: AsrText? = null
        assertTrue(handoff.activate(token, 640, { controller.recognitionAllowed(token) }) { pcm, count ->
            for (offset in 0 until count step 320) {
                val frame = pcm.copyOfRange(offset, offset + 320)
                assertTrue(asr.accept(frame, 320))
                // Known synthetic markers supply scripted VAD probabilities only in this test.
                if (endpoint.advance(if (frame[0] == 0.toShort()) .1f else .95f) == EndpointResult.COMPLETE) {
                    final = asr.poll(finish = true)
                }
                frame.fill(0)
            }
        })
        assertEquals(3840, backend.received.size)
        for (frame in 14 until 22) assertTrue(handoff.offer(ShortArray(320) { 16384 }, 320, frame * 320L))
        assertTrue(handoff.offer(ShortArray(320) { 16384 }, 320, 21 * 320L))
        assertEquals(6400, backend.received.size)
        for (frame in 22 until 47) assertTrue(handoff.offer(ShortArray(320), 320, frame * 320L))
        assertEquals(14400, backend.received.size)
        assertTrue(backend.received.take(6400).all { it == .5f })
        assertTrue(backend.received.drop(6400).all { it == 0f })
        assertEquals("What time is it?", final!!.text)
        assertEquals(1, backend.closes)
        assertNull(asr.poll(finish = true))
        assertTrue(controller.finishRecognition(token, final!!, null, active = { true }, accepted = { fail("Unscored text must not reach conversation processing") }))
        assertEquals(listOf(RecognitionPolicy.CLARIFICATION), effects.clauses)
        handoff.close()
        assertEquals(0, handoff.retainedSamples())
    }

    @Test fun stopAndReplacementDuringBackendFinalCannotReleaseOldText() {
        val controller = testController()
        controller.dispatch(ControllerEvent.START)
        controller.dispatch(ControllerEvent.SPEECH_DETECTED, token = controller.token())
        val token = controller.token()!!
        val backend = Backend()
        val asr = StreamingAsr(token, { controller.recognitionAllowed(token) }, { backend })
        assertTrue(asr.accept(ShortArray(320), 320))
        backend.onFinal = { controller.stop(); controller.dispatch(ControllerEvent.START) }
        assertNull(asr.poll(finish = true))
        assertTrue(token.cancelled)
        assertEquals(ControllerState.STANDBY, controller.state())
        assertEquals(1, backend.closes)
    }
}
