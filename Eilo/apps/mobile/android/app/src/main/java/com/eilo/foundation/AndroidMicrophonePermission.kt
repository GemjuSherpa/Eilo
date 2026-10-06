package com.eilo.foundation
import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import com.facebook.react.modules.core.PermissionAwareActivity
import com.facebook.react.modules.core.PermissionListener

/** OS permission adapter; request is only invoked by an explicit native Start intent. */
class AndroidMicrophonePermission(private val activity: Activity) : MicrophonePermissionAdapter {
    private val revision=java.util.concurrent.atomic.AtomicLong(0)
    override fun cancelPendingRequests() { revision.incrementAndGet() }
    @Volatile private var requested = false
    override fun status(): MicrophonePermission {
        if (activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) return MicrophonePermission.GRANTED
        return if (requested || activity.shouldShowRequestPermissionRationale(Manifest.permission.RECORD_AUDIO)) MicrophonePermission.DENIED else MicrophonePermission.NOT_REQUESTED
    }
    override fun request(completion: (MicrophonePermission) -> Unit) {
        val expected=revision.get()
        activity.runOnUiThread {
            if (revision.get() != expected) return@runOnUiThread
            try {
                val before=status()
                if (before != MicrophonePermission.NOT_REQUESTED || activity.isFinishing || activity.isDestroyed) { completion(if (activity.isFinishing || activity.isDestroyed) MicrophonePermission.UNAVAILABLE else before); return@runOnUiThread }
                val host=activity as? PermissionAwareActivity
                if (host == null) { completion(MicrophonePermission.UNAVAILABLE); return@runOnUiThread }
                requested=true
                host.requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO),2701,PermissionListener { requestCode, _, _ ->
                    if (requestCode != 2701) false else { completion(status()); true }
                })
            } catch (_: Exception) { completion(MicrophonePermission.UNAVAILABLE) }
        }
    }
}
