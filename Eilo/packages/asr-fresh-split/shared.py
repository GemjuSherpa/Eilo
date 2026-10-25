"""Existing local evaluation primitives; no downloads, hardware audio or activation."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CORPUS = HERE.parent / 'asr-corpus-score'
SDK = HERE.parent / 'asr-sdk-score-probe'
DATA = HERE.parent / 'dataset-evaluation'
sys.path.insert(0, str(CORPUS))
from diagnostics import SOURCES, REASONS, need, score_response, summarize
# Load the corpus validator explicitly; several experimental packages have a report.py.
spec = importlib.util.spec_from_file_location('fresh_corpus_validator', CORPUS / 'report.py')
corpus_report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(corpus_report)
sys.path.insert(0, str(DATA))
from manifests import canonical_digest, safe_path, verify_receipt
from benchmark import validate_manifest, normalize
from preprocess import opaque
from confidence import unique


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    need(Path(path).stat().st_size <= 4 * 1024 * 1024)
    def reject(_):
        raise ValueError('nonfinite JSON prohibited')
    return json.loads(Path(path).read_text(), object_pairs_hook=unique, parse_constant=reject)


def protocol():
    return read(HERE / 'protocol.json')


def source_pins():
    paths = [HERE / n for n in ('shared.py', 'select_split.py', 'evaluate.py', 'protocol.json')]
    paths += [CORPUS / n for n in ('main.cpp', 'CMakeLists.txt', 'diagnostics.py')]
    paths += [SDK / n for n in ('score_trace.h', 'overlay.py', 'overlay-expected.json')]
    paths += [DATA / n for n in ('extract_subset.py', 'preprocess.py', 'audio.py', 'manifests.py', 'benchmark.py', 'confidence.py')]
    paths += [HERE.parent / 'asr-confidence-probe' / n for n in ('check_android.py', 'source-manifest.json')]
    paths += [HERE.parent / 'asr-runtime/provenance.json']
    return {str(p.relative_to(HERE.parent)): sha(p) for p in paths}
