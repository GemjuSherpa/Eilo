"""Deterministic offline PCM conversion, with explicit bounded decoder provenance."""
import hashlib
from pathlib import Path
import struct
import subprocess
import tempfile
import wave
from manifests import require, sha256

RATE = 16000
MAX_SECONDS = 30
RECIPE = 'pcm16-mono-area-downsample-linear-upsample-v1'


def divide(value, divisor):
    # Symmetric integer rounding, independent of Python's float rounding.
    return (value + divisor // 2) // divisor if value >= 0 else -((-value + divisor // 2) // divisor)


def resample(samples, source_rate, target_rate=RATE):
    require(type(source_rate) is int and 8000 <= source_rate <= 192000, 'invalid sample rate')
    require(type(target_rate) is int and 8000 <= target_rate <= 192000, 'invalid target rate')
    require(samples, 'empty audio')
    count = len(samples) * target_rate // source_rate
    require(count > 0, 'audio too short')
    if source_rate == target_rate:
        return list(samples)
    result = []
    for i in range(count):
        start = i * source_rate
        if source_rate > target_rate:
            # Average exact rational input-cell overlaps. Box filter, not production SRC.
            end = start + source_rate
            first, last = start // target_rate, (end - 1) // target_rate
            total = sum(samples[j] * (min(end, (j + 1) * target_rate)
                                      - max(start, j * target_rate))
                        for j in range(first, last + 1))
            result.append(divide(total, source_rate))
        else:
            j, fraction = divmod(start, target_rate)
            right = samples[min(j + 1, len(samples) - 1)]
            result.append(divide(samples[j] * (target_rate - fraction) + right * fraction,
                                 target_rate))
    return result


def read_wav(path, max_seconds=MAX_SECONDS):
    require(Path(path).stat().st_size <= 64 * 1024 * 1024, 'oversized WAV')
    with wave.open(str(path), 'rb') as stream:
        channels, width, rate, count = (stream.getnchannels(), stream.getsampwidth(),
                                        stream.getframerate(), stream.getnframes())
        require(stream.getcomptype() == 'NONE', 'compressed WAV unsupported')
        require(channels in (1, 2) and width in (1, 2, 3, 4), 'unsupported PCM format')
        require(8000 <= rate <= 192000 and 0 < count <= rate * max_seconds, 'invalid duration/rate')
        raw = stream.readframes(count)
        require(len(raw) == count * channels * width, 'truncated WAV')
    mono = []
    for offset in range(0, len(raw), width * channels):
        values = []
        for channel in range(channels):
            chunk = raw[offset + channel * width:offset + (channel + 1) * width]
            sample = (chunk[0] - 128) * 256 if width == 1 else int.from_bytes(chunk, 'little', signed=True)
            if width > 2:
                sample = divide(sample, 1 << (8 * (width - 2)))
            values.append(max(-32768, min(32767, sample)))
        mono.append(divide(sum(values), channels))
    return resample(mono, rate)


def pcm_bytes(samples):
    require(samples and all(type(x) is int and -32768 <= x <= 32767 for x in samples), 'invalid PCM16')
    return struct.pack('<' + 'h' * len(samples), *samples)


def write_wav(path, samples):
    raw = pcm_bytes(samples)
    with wave.open(str(path), 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(RATE)
        stream.writeframes(raw)
    return hashlib.sha256(raw).hexdigest()


def decode_mp3(path, decoder, expected_sha256, kind='ffmpeg'):
    # Caller provisions/approves ffmpeg; no lookup, install or network input.
    require(sha256(decoder) == expected_sha256, 'decoder binary changed')
    require(Path(path).is_file() and Path(path).stat().st_size <= 16 * 1024 * 1024, 'oversized MP3')
    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp) / 'decoded.wav'
        if kind == 'ffmpeg':
            command = [str(Path(decoder).resolve()), '-nostdin', '-v', 'error', '-threads', '1',
                       '-protocol_whitelist', 'file', '-f', 'mp3', '-i', str(Path(path).resolve()),
                       '-t', '30', '-ac', '1', '-ar', '16000', '-acodec', 'pcm_s16le',
                       '-fflags', '+bitexact', '-flags:a', '+bitexact', str(output)]
        elif kind == 'afconvert':
            command = [str(Path(decoder).resolve()), '-f', 'WAVE', '-d', 'LEI16@16000',
                       '-c', '1', '--mix', '-r', '127', '--src-complexity', 'norm',
                       str(Path(path).resolve()), str(output)]
        else:
            raise ValueError('unreviewed decoder kind')
        subprocess.run(command, check=True, capture_output=True, timeout=60)
        # Reject potentially truncated long clips rather than changing the transcript.
        samples = read_wav(output)
        require(len(samples) < RATE * MAX_SECONDS, 'MP3 at duration limit; reject possible truncation')
        return samples
