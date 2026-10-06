package com.eilo.foundation

import android.content.Context
import android.media.*
import android.os.Handler
import android.os.Looper

internal class AndroidAudioFocus(context: Context, private val interrupted: () -> Unit) {
    private val manager=context.getSystemService(AudioManager::class.java)
    private val request=AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN)
        .setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build())
        .setWillPauseWhenDucked(true)
        .setOnAudioFocusChangeListener({ change ->
            if (change == AudioManager.AUDIOFOCUS_LOSS || change == AudioManager.AUDIOFOCUS_LOSS_TRANSIENT || change == AudioManager.AUDIOFOCUS_LOSS_TRANSIENT_CAN_DUCK) interrupted()
            // AUDIOFOCUS_GAIN deliberately does not restart capture.
        },Handler(Looper.getMainLooper())).build()
    fun acquire() { check(manager.requestAudioFocus(request) == AudioManager.AUDIOFOCUS_REQUEST_GRANTED) }
    fun release() { manager.abandonAudioFocusRequest(request) }
}
