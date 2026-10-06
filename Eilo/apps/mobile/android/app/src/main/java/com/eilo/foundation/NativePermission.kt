package com.eilo.foundation

enum class MicrophonePermission { NOT_REQUESTED, DENIED, GRANTED, UNAVAILABLE }
interface MicrophonePermissionAdapter {
    fun cancelPendingRequests() {}
    fun status(): MicrophonePermission
    fun request(completion: (MicrophonePermission) -> Unit)
}
class UnavailablePermissionAdapter : MicrophonePermissionAdapter {
    override fun status() = MicrophonePermission.UNAVAILABLE
    override fun request(completion: (MicrophonePermission) -> Unit) { completion(status()) }
}
