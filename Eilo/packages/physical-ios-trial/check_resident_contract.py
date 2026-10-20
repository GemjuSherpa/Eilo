"""Offline resident lab ASan/UBSan contracts using an existing verified runtime source cache."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from resident_wrapper import resident_wrapper

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--llm-cache',type=Path,required=True);args=parser.parse_args()
    llm=HERE.parent/'llm-runtime';prov=json.loads((llm/'provenance.json').read_text())
    archive=args.llm_cache/'llama-v0.6.0.tar.gz';source=args.llm_cache/('llama.cpp-'+prov['runtime']['commit'])
    with archive.open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=prov['runtime']['source_archive_sha256']:raise ValueError('runtime archive changed')
    spec=importlib.util.spec_from_file_location('resident_host',llm/'check_host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
    host.verify_tree(archive,source,source.name)
    compiled,_=resident_wrapper((llm/'eilo_llm.cc').read_bytes())
    with tempfile.TemporaryDirectory(prefix='eilo-resident-contract-') as folder:
        folder=Path(folder);adapter=folder/'resident.cc';adapter.write_bytes(compiled)
        backend=(llm/'tests/contract.cc').read_text()
        if backend.count('int main() {')!=1:raise ValueError('scripted backend boundary changed')
        prefix=backend.split('int main() {')[0]
        prefix='static int resident_load_calls=0,resident_context_calls=0,resident_kv_clears=0;\n'+prefix
        for old,new in [('++live; return new llama_model;','++resident_load_calls; ++live; return new llama_model;'),
                        ('context_params = p; ++live;','context_params = p; ++resident_context_calls; ++live;'),
                        ('{ CHECK(zero); }','{ CHECK(zero); ++resident_kv_clears; }')]:
            if prefix.count(old)!=1:raise ValueError('scripted allocation counter boundary changed')
            prefix=prefix.replace(old,new)
        extra=folder/'contract.cc';extra.write_text(prefix+(HERE/'tests/resident_contract.cc').read_text())
        base=['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
              '-I'+str(HERE/'include'),'-I'+str(llm/'include'),'-I'+str(source/'include'),'-I'+str(source/'ggml/include'),str(adapter)]
        for label,contract in [('original',llm/'tests/contract.cc'),('resident',extra)]:
            binary=folder/label;subprocess.run([*base,str(contract),'-o',str(binary)],check=True,timeout=60)
            subprocess.run([str(binary)],check=True,timeout=60)


if __name__=='__main__':main()
