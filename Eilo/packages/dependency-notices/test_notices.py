import base64
import hashlib
import io
import json
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest
import zipfile
from notices import scan_archive,parent_declaration,cache_files,npm_exit,strict_json,packaged_notices,sha


def pom(group,artifact,version,parent=None,licensed=False):
    p='' if parent is None else '<parent><groupId>'+parent[0]+'</groupId><artifactId>'+parent[1]+'</artifactId><version>'+parent[2]+'</version></parent>'
    license='<licenses><license><name>Apache 2.0</name><url>https://example.com/license</url></license></licenses>' if licensed else ''
    return ('<project xmlns="urn:test">'+p+'<groupId>'+group+'</groupId><artifactId>'+artifact+'</artifactId><version>'+version+'</version>'+license+'</project>').encode()


def parent_fixture(root):
    cache=root/'cache';child=cache/'g/child/1/hash/child.pom';child.parent.mkdir(parents=True);child.write_bytes(pom('g','child','1',('g','parent','2')))
    parent=cache/'g/parent/2/hash/parent.pom';parent.parent.mkdir(parents=True);parent.write_bytes(pom('g','parent','2',licensed=True))
    artifact=root/'child.jar'
    with zipfile.ZipFile(artifact,'w') as z:z.writestr('META-INF/maven/g/child/pom.xml',child.read_bytes())
    return cache,child,parent,artifact


def npm_fixture(root,link=False):
    raw=io.BytesIO()
    metadata=dict(name='exit',version='0.1.2',licenses=[dict(type='MIT',url='https://github.com/cowboy/node-exit/blob/master/LICENSE-MIT')])
    content={'package/package.json':json.dumps(metadata).encode(),'package/LICENSE-MIT':b'synthetic notice'}
    with tarfile.open(fileobj=raw,mode='w:gz') as archive:
        for name,data in content.items():
            item=tarfile.TarInfo(name);item.size=len(data);archive.addfile(item,io.BytesIO(data))
        if link:
            item=tarfile.TarInfo('package/link');item.type=tarfile.SYMTYPE;item.linkname='/outside';archive.addfile(item)
    body=raw.getvalue();digest=hashlib.sha512(body).digest();hex_digest=digest.hex();cache=root/'npm';path=cache/'content-v2/sha512'/hex_digest[:2]/hex_digest[2:4]/hex_digest[4:];path.parent.mkdir(parents=True);path.write_bytes(body)
    node=root/'node'
    for name,data in content.items():
        target=node/'exit'/name.removeprefix('package/');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    lock=dict(packages={'node_modules/exit':dict(version='0.1.2',integrity='sha512-'+base64.b64encode(digest).decode())})
    return lock,cache,node,path


class NoticeTests(unittest.TestCase):
    def test_nested_notice_hashes_without_text_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            child=io.BytesIO()
            with zipfile.ZipFile(child,'w') as z:z.writestr('META-INF/LICENSE',b'synthetic license')
            path=Path(tmp)/'x.aar'
            with zipfile.ZipFile(path,'w') as z:z.writestr('classes.jar',child.getvalue());z.writestr('NOTICE',b'synthetic attribution')
            rows=scan_archive(path);self.assertEqual([r['path'] for r in rows],['NOTICE','classes.jar!META-INF/LICENSE'])
            self.assertNotIn('synthetic',json.dumps(rows))

    def test_unsafe_duplicate_and_link_members_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'x.jar'
            for name in ['../LICENSE','/LICENSE','a//LICENSE']:
                with zipfile.ZipFile(path,'w') as z:z.writestr(name,b'x')
                with self.assertRaises(ValueError):scan_archive(path)
            with zipfile.ZipFile(path,'w') as z:
                item=zipfile.ZipInfo('LICENSE');item.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(item,b'outside')
            with self.assertRaises(ValueError):scan_archive(path)
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',UserWarning)
                with zipfile.ZipFile(path,'w') as z:z.writestr('LICENSE',b'first');z.writestr('LICENSE',b'second')
            with self.assertRaises(ValueError):scan_archive(path)

    def test_parent_chain_requires_pinned_embedded_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache,child,parent,artifact=parent_fixture(Path(tmp));r=parent_declaration(cache,('g','child','1'),{sha(child)},artifact)
            self.assertEqual(r['status'],'CACHED_PARENT_DECLARATION');self.assertEqual(len(r['chain']),2);self.assertEqual(r['child_embedded_pom_sha256'],sha(child))
            with zipfile.ZipFile(artifact,'w') as z:z.writestr('META-INF/maven/g/child/pom.xml',b'changed')
            with self.assertRaises(ValueError):parent_declaration(cache,('g','child','1'),{sha(child)},artifact)

    def test_missing_parent_is_unresolved_and_cycles_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache,child,parent,artifact=parent_fixture(Path(tmp));original=parent.read_bytes();parent.unlink()
            r=parent_declaration(cache,('g','child','1'),{sha(child)},artifact);self.assertEqual(r['status'],'CACHED_POM_MISSING');self.assertEqual(r['child_embedded_pom_sha256'],sha(child))
            parent.write_bytes(pom('g','parent','2',('g','child','1')))
            with self.assertRaises(ValueError):parent_declaration(cache,('g','child','1'),{sha(child)},artifact)

    def test_unverified_child_and_unsafe_coordinates_cannot_resolve_license(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cache,child,parent,artifact=parent_fixture(root)
            self.assertEqual(parent_declaration(cache,('g','child','1'),{sha(child)},None)['status'],'NO_VERIFIED_CHILD_ARTIFACT')
            for parts in [('..','child','1'),('g','child','${version}'),('g','../child','1')]:
                with self.assertRaises(ValueError):cache_files(cache,parts,'.pom')
            external=root/'outside.pom';external.write_text('private');target=child.parent/'link.pom';target.symlink_to(external)
            with self.assertRaises(ValueError):cache_files(cache,('g','child','1'),'.pom')

    def test_exit_sri_and_installed_bytes_are_both_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock,cache,node,path=npm_fixture(Path(tmp));r=npm_exit(lock,cache,node)
            self.assertTrue(all(x['installed_bytes_match'] for x in r['files']));self.assertEqual(r['legacy_license_declarations'][0]['type'],'MIT')
            (node/'exit/LICENSE-MIT').write_text('changed')
            with self.assertRaises(ValueError):npm_exit(lock,cache,node)
            (node/'exit/LICENSE-MIT').write_bytes(b'synthetic notice');path.write_bytes(path.read_bytes()+b'changed')
            with self.assertRaises(ValueError):npm_exit(lock,cache,node)

    def test_npm_archive_link_and_ambiguous_json_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock,cache,node,path=npm_fixture(Path(tmp),link=True)
            with self.assertRaises(ValueError):npm_exit(lock,cache,node)
        for value in ['{"licenses":1,"licenses":2}','{"value":NaN}']:
            with self.assertRaises(ValueError):strict_json(value)

    def test_packaged_artifact_hash_mismatch_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'app.apk';app=root/'app';app.mkdir();(app/'NOTICE').write_bytes(b'synthetic')
            with zipfile.ZipFile(path,'w') as z:z.writestr('NOTICE',b'synthetic')
            rows=[dict(path='NOTICE',bytes=9,sha256=sha(app/'NOTICE'))]
            tree=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            baseline=dict(android=dict(sha256=sha(path)),ios=dict(tree_sha256=tree))
            self.assertEqual(len(packaged_notices(baseline,path,app)['android']['notices']),1)
            with zipfile.ZipFile(path,'a') as z:z.writestr('new.txt',b'changed')
            with self.assertRaises(ValueError):packaged_notices(baseline,path,app)
            baseline['android']['sha256']=sha(path);(app/'NOTICE').write_bytes(b'changed')
            with self.assertRaises(ValueError):packaged_notices(baseline,path,app)


if __name__=='__main__':unittest.main()
