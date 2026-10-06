package com.eilo.foundation

import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder

/** Platform-owned buffers are released; application samples never leave ForegroundCapture. */
internal class AndroidCaptureDevice(context: android.content.Context) : CaptureDevice {
    private val record: AudioRecord
    private var closed = false
    init {
        if (context.checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) != android.content.pm.PackageManager.PERMISSION_GRANTED) throw SecurityException()
        val minimum = AudioRecord.getMinBufferSize(16_000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        check(minimum > 0 && minimum <= 65_536)
        record = AudioRecord.Builder()
            .setAudioSource(MediaRecorder.AudioSource.VOICE_RECOGNITION)
            .setAudioFormat(AudioFormat.Builder().setSampleRate(16_000)
                .setChannelMask(AudioFormat.CHANNEL_IN_MONO).setEncoding(AudioFormat.ENCODING_PCM_16BIT).build())
            .setBufferSizeInBytes(maxOf(minimum, 1_280)).build()
        if (record.state != AudioRecord.STATE_INITIALIZED) {
            record.release()
            throw IllegalStateException()
        }
    }
    @Synchronized override fun start() {
        check(!closed)
        record.startRecording()
        check(record.recordingState == AudioRecord.RECORDSTATE_RECORDING)
    }
    @Synchronized override fun read(samples: ShortArray): Int {
        check(!closed)
        return record.read(samples, 0, samples.size, AudioRecord.READ_NON_BLOCKING)
    }
    @Synchronized override fun close() {
        if (closed) return
        closed = true
        // Always attempt release even if stop fails; propagate so the controller cannot fake success.
        try { if (record.recordingState == AudioRecord.RECORDSTATE_RECORDING) record.stop() }
        finally { record.release() }
    }
}
