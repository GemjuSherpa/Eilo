#!/usr/bin/env python3
"""Local Moonshine host adapter. Config via EILO_DATA_ASR_CONFIG, no downloads."""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from audio import RATE, read_wav
from benchmark import normalize
from manifests import canonical_digest, require, safe_path, sha256
from preprocess import COMMANDS


def verified_config(path):
    require(sha256(path) == os.environ['EILO_DATA_ADAPTER_CONFIG_SHA256'], 'adapter config changed')
    config = json.loads(Path(path).read_text())
    executable = Path(config['executable'])
    require(sha256(executable) == config['executable_sha256'], 'native executable changed')
    source = Path(config['provenance'])
    require(sha256(source) == config['provenance_sha256'], 'runtime provenance changed')
    record = json.loads(source.read_text())
    cache = Path(config['cache'])
    host = record['host']
    require(sha256(safe_path(cache, host['archive'])) == host['publisher_sha256'], 'vendor archive changed')
    for item in host['files']:
        require(sha256(safe_path(cache, item['path'])) == item['sha256'], 'vendor file changed')
    model = cache / record['model']['directory']
    for item in record['model']['files']:
        path = safe_path(model, item['file'])
        require(path.stat().st_size == item['bytes'] and sha256(path) == item['local_sha256'], 'model changed')
    require(config['model_sha256'] == canonical_digest(record['model'])
            == os.environ['EILO_DATA_ADAPTER_MODEL_SHA256'], 'model manifest changed')
    return config, executable, model


def infer(request, config_path):
    require(request['schema_version'] == 1 and request['rate'] == RATE, 'invalid request')
    require(request['task'] in ('asr', 'commands'), 'native VAD adapter unavailable')
    _, executable, model = verified_config(config_path)
    samples = read_wav(request['audio'])
    with tempfile.TemporaryDirectory(prefix='eilo-public-corpus-asr-') as temp:
        raw = Path(temp) / 'input.f32'
        raw.write_bytes(struct.pack('<' + 'f' * len(samples), *(x / 32768 for x in samples)))
        try:
            result = subprocess.run([str(executable), str(model), str(raw)],
                                    check=True, capture_output=True, timeout=120)
            require(len(result.stdout) <= 4097, 'unbounded transcript')
            transcript = result.stdout.decode('utf-8').strip()
        finally:
            raw.write_bytes(bytes(raw.stat().st_size))
    output = {'id': request['id'], 'transcript': transcript}
    if request['task'] == 'commands':
        word = normalize(transcript)
        output['command'] = word if word in COMMANDS else 'unknown'
    return output


if __name__ == '__main__':
    require(len(sys.argv) == 3, 'request/response paths required')
    request = json.loads(Path(sys.argv[1]).read_text())
    response = infer(request, os.environ['EILO_DATA_ASR_CONFIG'])
    Path(sys.argv[2]).write_text(json.dumps(response) + '\n')
