package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class SafeDiagnosticsTest {
    @Test fun boundedVolatileCodesHaveNoContentFields() {
        val diagnostics = SafeDiagnostics()
        repeat(100) { diagnostics.record(SafeComponent.MODEL, SafeError.UNEXPECTED, SafeSeverity.ERROR) }
        assertEquals(32, diagnostics.snapshot().size)
        assertEquals(setOf("component", "code", "severity"), SafeDiagnostic::class.java.declaredFields.filterNot { it.isSynthetic }.map { it.name }.toSet())
        diagnostics.clear()
        assertTrue(diagnostics.snapshot().isEmpty())
        assertTrue(SafeDiagnostics().snapshot().isEmpty())
    }
}
