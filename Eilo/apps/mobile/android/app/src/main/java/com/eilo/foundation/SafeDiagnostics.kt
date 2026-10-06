package com.eilo.foundation

/** Volatile, bounded metadata only. There is no message/Throwable/content input or sink. */
enum class SafeError { PERMISSION_DENIED, UNAVAILABLE, TIMEOUT, QUOTA, UNEXPECTED }
enum class SafeComponent { CONTROLLER, CAPTURE, ASR, MODEL, SPEECH, MEMORY }
enum class SafeSeverity { INFO, WARNING, ERROR }
data class SafeDiagnostic(val component: SafeComponent, val code: SafeError, val severity: SafeSeverity)
class SafeDiagnostics {
    private val entries = ArrayDeque<SafeDiagnostic>()
    @Synchronized fun record(component: SafeComponent, code: SafeError, severity: SafeSeverity) {
        if (entries.size == 32) entries.removeFirst()
        entries.addLast(SafeDiagnostic(component, code, severity))
    }
    @Synchronized fun snapshot(): List<SafeDiagnostic> = entries.toList()
    @Synchronized fun clear() { entries.clear() }
}
