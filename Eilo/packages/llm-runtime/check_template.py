#!/usr/bin/env python3
"""Compare checked-in native golden fixtures with an existing pinned official template.
Run using the existing model-build Python environment; downloads/installs nothing.
"""
import argparse
import hashlib
import json
from pathlib import Path
from jinja2 import Environment

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--tokenizer-config', type=Path, required=True)
args = parser.parse_args()
source = json.loads(args.tokenizer_config.read_text())['chat_template']
fixtures = json.loads((Path(__file__).parent / 'tests/template-fixtures.json').read_text())
if hashlib.sha256(source.encode()).hexdigest() != fixtures['template_sha256']:
    raise SystemExit('Pinned template mismatch')
for case in fixtures['fixtures']:
    # Fixed privileged content is the first system turn in the native golden.
    rules = case['rendered'].split('<|im_start|>system\n', 1)[1].split('<|im_end|>', 1)[0]
    escape = lambda text: text.replace('<', '＜').replace('>', '＞')
    messages = [{'role': 'system', 'content': rules}]
    messages += [{'role': turn['role'], 'content': escape(turn['text'])} for turn in case['history']]
    messages += [{'role': 'user', 'content': escape(case['latest'])}]
    rendered = Environment().from_string(source).render(messages=messages, add_generation_prompt=True, enable_thinking=False)
    if rendered != case['rendered']:
        raise SystemExit('Official template golden mismatch')
print('Pinned official Qwen3 template: three enable_thinking=false goldens PASS.')
