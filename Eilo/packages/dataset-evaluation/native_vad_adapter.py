#!/usr/bin/env python3
"""Pinned sherpa-onnx 1.13.8 file-only VAD adapter; no microphone or downloads."""
import ctypes as C
import json
import os
from pathlib import Path
import sys
from audio import RATE, read_wav
from manifests import require, sha256


class Model(C.Structure):
    _fields_ = [('model', C.c_char_p), ('threshold', C.c_float),
                ('min_silence_duration', C.c_float), ('min_speech_duration', C.c_float),
                ('window_size', C.c_int32), ('max_speech_duration', C.c_float)]


class Config(C.Structure):
    _fields_ = [('silero_vad', Model), ('sample_rate', C.c_int32),
                ('num_threads', C.c_int32), ('provider', C.c_char_p),
                ('debug', C.c_int32), ('ten_vad', Model)]


class Segment(C.Structure):
    _fields_ = [('start', C.c_int32), ('samples', C.POINTER(C.c_float)), ('n', C.c_int32)]


SETTINGS = {'threshold': 0.5, 'min_silence_duration': 0.5,
            'min_speech_duration': 0.16, 'window_size': 512, 'max_speech_duration': 30,
            'rate': RATE, 'threads': 1, 'provider': 'cpu',
            'tail_policy': 'zero-pad-last-window-flush-clamp-to-original-samples'}


def verified_config(path):
    require(sha256(path) == os.environ['EILO_DATA_ADAPTER_CONFIG_SHA256'], 'config changed')
    value = json.loads(Path(path).read_text())
    require(value['runtime_version'] == '1.13.8' and value['settings'] == SETTINGS, 'unsupported ABI/settings')
    require(value['model']['sha256'] == os.environ['EILO_DATA_ADAPTER_MODEL_SHA256'], 'model pin changed')
    for item in [value['model'], *value['runtime_files']]:
        require(sha256(item['path']) == item['sha256'], 'runtime/model file changed')
    pinned = json.loads(Path(__file__).with_name('vad-provenance.json').read_text())
    require(value['model']['sha256'] == pinned['model']['sha256'], 'unreviewed model')
    require({x['sha256'] for x in value['runtime_files']} ==
            {x['sha256'] for x in pinned['runtime']['files']}, 'unreviewed runtime')
    require(value['library'] in [x['path'] for x in value['runtime_files']], 'library unpinned')
    return value


def api(library):
    lib = C.CDLL(library)
    signatures = {
        'CreateVoiceActivityDetector': ([C.POINTER(Config), C.c_float], C.c_void_p),
        'DestroyVoiceActivityDetector': ([C.c_void_p], None),
        'VoiceActivityDetectorAcceptWaveform': ([C.c_void_p, C.POINTER(C.c_float), C.c_int32], None),
        'VoiceActivityDetectorEmpty': ([C.c_void_p], C.c_int32),
        'VoiceActivityDetectorFront': ([C.c_void_p], C.POINTER(Segment)),
        'DestroySpeechSegment': ([C.POINTER(Segment)], None),
        'VoiceActivityDetectorPop': ([C.c_void_p], None),
        'VoiceActivityDetectorFlush': ([C.c_void_p], None),
        'VoiceActivityDetectorReset': ([C.c_void_p], None)}
    result = {}
    for name, (args, returns) in signatures.items():
        fn = getattr(lib, 'SherpaOnnx' + name)
        fn.argtypes, fn.restype = args, returns
        result[name] = fn
    return result


def detect(samples, value, functions=None):
    require(0 < len(samples) <= RATE * 30, 'audio outside 30-second bound')
    require(all(type(x) is int and -32768 <= x <= 32767 for x in samples), 'PCM16 required')
    f = functions if functions is not None else api(value['library'])
    config = Config()
    model_path = os.fsencode(value['model']['path'])
    config.silero_vad = Model(model_path, 0.5, 0.5, 0.16, 512, 30)
    config.sample_rate, config.num_threads, config.provider = RATE, 1, b'cpu'
    handle = f['CreateVoiceActivityDetector'](C.byref(config), 32.0)
    require(handle, 'VAD creation failed')
    intervals = []
    drained = 0
    def drain():
        nonlocal drained
        while not f['VoiceActivityDetectorEmpty'](handle):
            drained += 1
            require(drained <= 1000, 'too many VAD segments')
            segment = f['VoiceActivityDetectorFront'](handle)
            require(segment, 'missing VAD segment')
            try:
                start, count = segment.contents.start, segment.contents.n
                require(start >= 0 and count > 0, 'invalid native segment')
                end = min(start + count, len(samples))
                if start < end:
                    require(not intervals or start / RATE >= intervals[-1][1], 'overlapping native segments')
                    intervals.append([start / RATE, end / RATE])
            finally:
                f['DestroySpeechSegment'](segment)
            f['VoiceActivityDetectorPop'](handle)
    try:
        for start in range(0, len(samples), 512):
            frame = samples[start:start + 512]
            buffer = (C.c_float * 512)(*(x / 32768 for x in frame))
            try:
                f['VoiceActivityDetectorAcceptWaveform'](handle, buffer, 512)
                drain()
            finally:
                C.memset(C.addressof(buffer), 0, C.sizeof(buffer))
        f['VoiceActivityDetectorFlush'](handle)
        drain()
        return intervals
    finally:
        try:
            f['VoiceActivityDetectorReset'](handle)
        finally:
            f['DestroyVoiceActivityDetector'](handle)


def infer(request, path):
    require(request['schema_version'] == 1 and request['rate'] == RATE and request['task'] == 'vad',
            'invalid VAD request')
    value = verified_config(path)
    samples = read_wav(request['audio'])
    return {'id': request['id'], 'vad': detect(samples, value)}


if __name__ == '__main__':
    require(len(sys.argv) == 3, 'request/response paths required')
    result = infer(json.loads(Path(sys.argv[1]).read_text()), os.environ['EILO_DATA_VAD_CONFIG'])
    Path(sys.argv[2]).write_text(json.dumps(result, allow_nan=False) + '\n')
