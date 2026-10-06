"""Inspect pinned converter output; produces content-free generic artifact evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def inspect(path, source):
    sys.path.insert(0, str(source / 'gguf-py'))
    from gguf import GGUFReader
    model = GGUFReader(str(path))
    def value(key):
        field = model.get_field(key)
        if field is None:
            return None
        return field.contents()
    template = value('tokenizer.chat_template')
    return {'filename': path.name, 'sha256': sha256(path), 'bytes': path.stat().st_size,
            'architecture': value('general.architecture'), 'file_type': value('general.file_type'),
            'tensor_count': len(model.tensors),
            'tensor_types': sorted({tensor.tensor_type.name for tensor in model.tensors}),
            'tokenizer_model': value('tokenizer.ggml.model'),
            'vocab_count': len(value('tokenizer.ggml.tokens')),
            'chat_template_sha256': hashlib.sha256(template.encode()).hexdigest(),
            'supports_enable_thinking': 'enable_thinking' in template,
            'tensor_inventory': [{'name': tensor.name, 'shape': tensor.shape.tolist(),
                                  'type': tensor.tensor_type.name} for tensor in model.tensors]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('artifact', type=Path)
    parser.add_argument('--llama-source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(inspect(args.artifact, args.llama_source), indent=2) + '\n')
