"""Exact lab-only descriptor size specialization; shipping/native audited source stays unchanged."""
import hashlib

BASE_SHA256 = 'caca29fa8706736a0af5e25a3b36b0343093cc2857bcd66ff135e8571f039eb9'
PINS = {
    'Qwen3-1.7B-Q4_K_M': (1282439424, 'c0efea3254c2363a9559e32ac76e9987aff3a68c31b84a3e65c12aa5c01bd120'),
    'Qwen3-0.6B-Q4_K_M': (484219808, '9b1a69f90cc7b7404ffeabd12f58391a6323ea08ae6e517f6cfd56bbb2caf5ca'),
}


def wrapper(source, pin):
    if hashlib.sha256(source).hexdigest() != BASE_SHA256:
        raise ValueError('Unreviewed base loader source')
    expected = PINS.get(pin.get('model'))
    if expected is None or type(pin.get('bytes')) is not int or (pin['bytes'], pin.get('sha256')) != expected:
        raise ValueError('Unreviewed lab model pin')
    original = b'constexpr int64_t kModelBytes = 1282439424;'
    replacement = ('constexpr int64_t kModelBytes = '+str(expected[0])+';').encode()
    if source.count(original) != 1:
        raise ValueError('Loader guard changed')
    compiled = source.replace(original, replacement)
    return compiled, dict(scope='LAB_ONLY_EXACT_MODEL_FILE_SIZE', base_source_sha256=BASE_SHA256,
                          compiled_source_sha256=hashlib.sha256(compiled).hexdigest(), model_sha256=expected[1],
                          required_model_bytes=expected[0], change='Only kModelBytes literal; descriptor SHA-256 verified by existing Swift lease; all other C++ checks retained')
