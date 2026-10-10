"""Independent synthetic tree-delta checks, NOT real Git/Windows isolation."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "windows"))
import dispatcher as d
import publisher as p
from test_windows_dispatcher import BASE, HEAD, approval


class SyntheticPublisherTests(unittest.TestCase):
    def setUp(self):
        self.a = approval()
        self.path = self.a["paths"][0]
        self.old = {self.path: p.SyntheticBlob("1" * 40)}
        self.new = {self.path: p.SyntheticBlob("2" * 40)}

    def verify(self, **updates):
        params = dict(approval=self.a, old_tree=self.old, new_tree=self.new,
                      main_sha=BASE, expected_base=BASE, pr_head=HEAD,
                      reviewed_head=HEAD, review_status="SYNTHETIC_PASS")
        params.update(updates)
        return p.validate_offline_delta(**params)

    def test_full_delta_return_is_permanently_no_go(self):
        report = self.verify()
        self.assertEqual(report["decision"], "NO_GO")
        self.assertEqual(report["changes"], (self.path,))
        for call in (p.require_publication, p.merge):
            with self.assertRaisesRegex(d.Denied, "NO_GO"):
                call()

    def test_out_of_scope_add_delete_rename(self):
        for tree in ({"another.py": p.SyntheticBlob("3" * 40)},
                     {self.path: p.SyntheticBlob("2" * 40), "bad.py": p.SyntheticBlob("2" * 40)},
                     {"outside.py": p.SyntheticBlob("1" * 40)}):
            with self.assertRaises(d.Denied):
                self.verify(new_tree=tree)
        with self.assertRaises(d.Denied):
            self.verify(new_tree={".gitattributes": p.SyntheticBlob("4" * 40),
                                  self.path: p.SyntheticBlob("2" * 40)})

    def test_git_modes_links_and_path_aliases(self):
        for obj in (p.SyntheticBlob("2" * 40, mode="120000"),
                    p.SyntheticBlob("2" * 40, mode="160000"),
                    p.SyntheticBlob("2" * 40, links=2),
                    p.SyntheticBlob("2" * 40, reparse=True),
                    p.SyntheticBlob("malformed")):
            with self.assertRaises(d.Denied):
                self.verify(new_tree={self.path: obj})
        for path in ("../secret", ".git/config", "NUL.py", "bad\\file.py", "bad:ads.py"):
            with self.assertRaises(d.Denied):
                self.verify(new_tree={self.path: p.SyntheticBlob("2" * 40),
                                      path: p.SyntheticBlob("2" * 40)})

    def test_reject_stale_head_base_and_fake_review(self):
        for edit in (dict(main_sha=HEAD), dict(reviewed_head=BASE),
                     dict(review_status="APPROVED"), dict(pr_head="bad"),
                     dict(expected_base=HEAD)):
            with self.assertRaises(d.Denied):
                self.verify(**edit)
        with self.assertRaises(d.Denied):
            self.verify(old_tree=self.new, new_tree=self.new)

    def test_case_collision_in_full_tree(self):
        other = "automation/windows/EXAMPLE.py"
        with self.assertRaises(d.Denied):
            self.verify(new_tree={self.path: p.SyntheticBlob("2" * 40),
                                  other: p.SyntheticBlob("2" * 40)})


    def test_nested_git_configuration_never_allowed_even_if_approved(self):
        for name in ("automation/.gitattributes", "automation/nested/.gitattributes",
                     "automation/.gitmodules", "frontend/.lfsconfig"):
            with self.subTest(path=name):
                expanded = self.a | {"paths": sorted([self.path, name])}
                edited = self.new | {name: p.SyntheticBlob("4" * 40)}
                with self.assertRaises(d.Denied):
                    self.verify(approval=expanded, new_tree=edited)


# Shared A3 fixtures: disposable RSA keys only, never a production trust root.
# Kept in this approved test file to avoid widening #216's exact write-set.
import atexit
import base64
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zlib
from datetime import timedelta
from unittest.mock import patch

from test_windows_dispatcher import NOW, checks, snapshot


class SyntheticSigner:
    def __init__(self):
        if not shutil.which('openssl'):
            raise unittest.SkipTest('OpenSSL unavailable for disposable RSA signing')
        self.temp = tempfile.TemporaryDirectory(prefix='garden-synthetic-signing-')
        atexit.register(self.temp.cleanup)
        self.key = Path(self.temp.name) / 'synthetic-only.pem'
        generated = subprocess.run(['openssl', 'genpkey', '-algorithm', 'RSA',
            '-pkeyopt', 'rsa_keygen_bits:3072', '-out', str(self.key)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        if generated.returncode:
            raise RuntimeError('synthetic key generation failed')
        value = subprocess.run(['openssl', 'rsa', '-in', str(self.key), '-noout', '-modulus'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        if value.returncode:
            raise RuntimeError('synthetic public root unavailable')
        self.root = int(value.stdout.decode('ascii').strip().split('=', 1)[1], 16)

    def sign(self, record):
        result = subprocess.run(['openssl', 'dgst', '-sha256', '-sign', str(self.key)],
            input=d.canonical(record), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        if result.returncode:
            raise RuntimeError('synthetic signing failed')
        return {'record': json.loads(d.canonical(record)),
                'signature': base64.b64encode(result.stdout).decode('ascii')}


_SIGNER = None


def signer_fixture():
    global _SIGNER
    if _SIGNER is None:
        _SIGNER = SyntheticSigner()
    return _SIGNER


def signed_evidence(signer, event=None, *, a=None, when=NOW, **updates):
    policy = p.SyntheticProviderPolicy()
    event = event if event is not None else snapshot()
    a = a if a is not None else approval()
    head = event['prs'][0]['head']
    record = dict(schema=1, evidence='SYNTHETIC', repo=a['repo'], issue=a['issue'],
        policy=policy.policy, collected=when.isoformat(),
        expires=(when + timedelta(seconds=60)).isoformat(), snapshot=event,
        providers={name: policy.ci_app for name in d.CI},
        review=dict(head=head, app=policy.review_app, reviewer=policy.reviewer,
                    policy=policy.policy, status='SYNTHETIC_PASS', blocking=False))
    record.update(updates)
    return signer.sign(record)


def make_git_fixture(directory, old=None, new=None, a=None, *, canonical_order=True):
    root = Path(directory)
    git = root / '.git'
    git.mkdir()
    (git / 'objects').mkdir()
    a = a if a is not None else approval()
    path = a['paths'][0]
    old = old if old is not None else {path: (b'synthetic-before', '100644')}
    new = new if new is not None else {path: (b'synthetic-after', '100644')}

    def object_(kind, value):
        raw = kind.encode() + b' ' + str(len(value)).encode() + b'\0' + value
        oid = hashlib.sha1(raw).hexdigest()
        target = git / 'objects' / oid[:2] / oid[2:]
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(zlib.compress(raw))
        return oid

    def tree(files):
        nested = {}
        for name, value in files.items():
            current = nested
            parts = name.split('/')
            for part in parts[:-1]:
                current = current.setdefault(part, {})
            current[parts[-1]] = value

        def serialize(node):
            raw = b''
            ordered = sorted(node, key=lambda n: n.encode('ascii') + (b'/' if isinstance(node[n], dict) else b'\0'))
            if not canonical_order:
                ordered.reverse()
            for name in ordered:
                value = node[name]
                if isinstance(value, dict):
                    mode, oid = '40000', serialize(value)
                else:
                    blob, mode = value
                    oid = object_('blob', blob)
                raw += mode.encode() + b' ' + name.encode('ascii') + b'\0' + bytes.fromhex(oid)
            return object_('tree', raw)
        return serialize(nested)

    identity = 'author Synthetic <fixture@example.invalid> 1577836800 +0000\ncommitter Synthetic <fixture@example.invalid> 1577836800 +0000\n'
    base = object_('commit', ('tree ' + tree(old) + '\n' + identity + '\nsynthetic baseline\n').encode())
    head = object_('commit', ('tree ' + tree(new) + '\nparent ' + base + '\n' + identity + '\nsynthetic candidate\n').encode())
    (git / 'HEAD').write_bytes(('ref: refs/heads/' + a['branch'] + '\n').encode())
    branch = git / 'refs/heads' / a['branch']
    branch.parent.mkdir(parents=True)
    branch.write_bytes((head + '\n').encode())
    (git / 'refs/heads/main').write_bytes((base + '\n').encode())
    return a | {'base': base}, head


def put_commit_fixture(directory, content):
    raw = b'commit ' + str(len(content)).encode() + b'\0' + content
    oid = hashlib.sha1(raw).hexdigest()
    path = Path(directory) / '.git/objects' / oid[:2] / oid[2:]
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(zlib.compress(raw))
    return oid


class A3PublisherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.signer = signer_fixture()

    def setUp(self):
        self.a = approval()
        self.event = snapshot()
        self.event['checks'] = checks()
        self.policy = p.SyntheticProviderPolicy()

    def verify(self, first=None, second=None, **kwargs):
        first = first if first is not None else signed_evidence(self.signer, self.event)
        second = second if second is not None else first
        args = dict(approval=self.a, feed=p.SyntheticEvidenceFeed((first, second)),
            evidence_root=self.signer.root, now=NOW, policy=self.policy,
            old_tree={self.a['paths'][0]: p.SyntheticBlob('1' * 40)},
            new_tree={self.a['paths'][0]: p.SyntheticBlob('2' * 40)})
        args.update(kwargs)
        return p.verify_fixture_candidate(**args)

    def test_signed_provider_and_independent_review(self):
        self.assertEqual(self.verify()['decision'], 'NO_GO')
        for update in (dict(evidence='LIVE-WITNESSED'), dict(issue=216), dict(policy='SAM-ACTIVE'),
                       dict(providers={n: 999 for n in d.CI})):
            with self.subTest(update=update), self.assertRaises(d.Denied):
                self.verify(first=signed_evidence(self.signer, self.event, **update))
        for update in (dict(head=BASE), dict(app=999), dict(reviewer='IMPLEMENTER'),
                       dict(blocking=True), dict(status='APPROVED')):
            envelope = signed_evidence(self.signer, self.event)
            record = envelope['record']
            record['review'].update(update)
            with self.assertRaises(d.Denied):
                self.verify(first=self.signer.sign(record))

    def test_forged_stale_missing_duplicate_and_changed_checks(self):
        good = signed_evidence(self.signer, self.event)
        forged = json.loads(d.canonical(good))
        forged['record']['review']['app'] = 999
        with self.assertRaises(d.Denied):
            self.verify(first=forged)
        for when in (NOW - timedelta(seconds=61), NOW + timedelta(seconds=1)):
            with self.assertRaises(d.Denied):
                self.verify(first=signed_evidence(self.signer, self.event, when=when))
        for conclusion in ('skipped', 'neutral', 'failure', 'cancelled', None):
            bad = json.loads(d.canonical(self.event))
            bad['checks'][0]['conclusion'] = conclusion
            with self.assertRaises(d.Denied):
                self.verify(first=signed_evidence(self.signer, bad))
        for bad_checks in (checks()[:-1], checks() + checks()[:1], checks()[:-1] + checks()[:1]):
            with self.assertRaises(d.Denied):
                self.verify(first=signed_evidence(self.signer, self.event | {'checks': bad_checks}))
        changed = json.loads(d.canonical(self.event))
        changed['prs'][0]['head'] = 'd' * 40
        changed['checks'] = checks('d' * 40)
        with self.assertRaises(d.Denied):
            self.verify(first=good, second=signed_evidence(self.signer, changed))
        with self.assertRaises(d.Denied):
            self.verify(feed=p.SyntheticEvidenceFeed((good,)))

    def test_readonly_raw_loose_objects_ignore_hooks_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, head = make_git_fixture(tmp)
            git = Path(tmp) / '.git'
            sentinel = Path(tmp) / 'UNEXECUTED'
            (git / 'config').write_text('[include]\n path = /no-such-config\n[core]\n hooksPath = /bad\n')
            (git / 'hooks').mkdir()
            hook = git / 'hooks/pre-commit'
            hook.write_text('exit 99\n')
            event = snapshot()
            event['main'] = a['base']
            event['prs'][0]['head'] = head
            event['checks'] = checks(head)
            evidence = signed_evidence(self.signer, event, a=a)
            before = {str(f.relative_to(tmp)): f.read_bytes() for f in Path(tmp).rglob('*') if f.is_file()}
            result = p.verify_loose_fixture_candidate(directory=tmp, approval=a,
                feed=p.SyntheticEvidenceFeed((evidence, evidence)), evidence_root=self.signer.root,
                now=NOW, policy=self.policy)
            after = {str(f.relative_to(tmp)): f.read_bytes() for f in Path(tmp).rglob('*') if f.is_file()}
            self.assertEqual(before, after)
            self.assertFalse(sentinel.exists())
            self.assertEqual(result['changes'], tuple(a['paths']))
            self.assertEqual(result['decision'], 'NO_GO')

    def test_corrupt_objects_links_packs_and_indirection(self):
        for attack in ('corrupt', 'symlink', 'hardlink', 'alternates', 'pack', 'gitfile'):
            with self.subTest(attack=attack), tempfile.TemporaryDirectory() as tmp:
                a, head = make_git_fixture(tmp)
                git = Path(tmp) / '.git'
                target = git / 'objects' / head[:2] / head[2:]
                if attack == 'corrupt':
                    target.write_bytes(zlib.compress(b'commit 1\0X'))
                elif attack in ('symlink', 'hardlink'):
                    outside = Path(tmp) / 'other'
                    target.rename(outside)
                    if attack == 'symlink':
                        target.symlink_to(outside)
                    else:
                        os.link(outside, target)
                elif attack == 'alternates':
                    (git / 'objects/info').mkdir()
                    (git / 'objects/info/alternates').write_text('../other\n')
                elif attack == 'pack':
                    (git / 'objects/pack').mkdir()
                    (git / 'objects/pack/fixture.pack').write_bytes(b'not a pack')
                else:
                    shutil.rmtree(git)
                    git.write_text('gitdir: /outside\n')
                with self.assertRaises(d.Denied):
                    p.LooseFixtureGitReader(tmp).tree(head)

    def test_unapproved_rename_deleted_modes_and_static_workflows(self):
        path = self.a['paths'][0]
        static = {'.github/workflows/ci.yml': p.SyntheticBlob('9' * 40),
                  'tools/old.sh': p.SyntheticBlob('8' * 40, mode='100755')}
        old = static | {path: p.SyntheticBlob('1' * 40)}
        new = static | {path: p.SyntheticBlob('2' * 40)}
        self.assertEqual(self.verify(old_tree=old, new_tree=new)['changes'], (path,))
        self.assertEqual(self.verify(old_tree=old, new_tree=static)['changes'], (path,))
        for new in (static | {'outside.py': p.SyntheticBlob('1' * 40)},
                    static | {path: p.SyntheticBlob('2' * 40, mode='100755')},
                    new | {'.github/workflows/ci.yml': p.SyntheticBlob('7' * 40)}):
            with self.assertRaises(d.Denied):
                self.verify(old_tree=old, new_tree=new)

    def test_raw_symlink_gitlink_traversal_and_executable_delta_denied(self):
        for path, mode in (('automation/windows/example.py', '120000'),
                           ('automation/windows/example.py', '160000'),
                           ('automation/windows/example.py', '100755'),
                           ('../outside', '100644'), ('NUL.txt', '100644')):
            with self.subTest(path=path, mode=mode), tempfile.TemporaryDirectory() as tmp:
                a, head = make_git_fixture(tmp, new={path: (b'synthetic', mode)})
                event = snapshot()
                event['main'] = a['base']
                event['prs'][0]['head'] = head
                event['checks'] = checks(head)
                evidence = signed_evidence(self.signer, event, a=a)
                with self.assertRaises(d.Denied):
                    p.verify_loose_fixture_candidate(directory=tmp, approval=a,
                        feed=p.SyntheticEvidenceFeed((evidence, evidence)),
                        evidence_root=self.signer.root, now=NOW, policy=self.policy)

    def test_directory_case_alias_and_prefix_file_collision_denied(self):
        for tree in ({'foo/a.py': p.SyntheticBlob('1' * 40),
                      'FOO/b.py': p.SyntheticBlob('2' * 40)},
                     {'foo': p.SyntheticBlob('1' * 40), 'foo/a.py': p.SyntheticBlob('2' * 40)}):
            with self.assertRaises(d.Denied):
                self.verify(new_tree=tree)

    def test_object_refs_drift_during_collection_fails_readonly(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, head = make_git_fixture(tmp)
            event = snapshot()
            event['main'] = a['base']
            event['prs'][0]['head'] = head
            event['checks'] = checks(head)
            evidence = signed_evidence(self.signer, event, a=a)
            original = p.LooseFixtureGitReader.tree
            def drift(reader, commit):
                result = original(reader, commit)
                (Path(tmp) / '.git/refs/heads/main').write_text('f' * 40 + '\n')
                return result
            with patch.object(p.LooseFixtureGitReader, 'tree', drift), self.assertRaises(d.Denied):
                p.verify_loose_fixture_candidate(directory=tmp, approval=a,
                    feed=p.SyntheticEvidenceFeed((evidence, evidence)),
                    evidence_root=self.signer.root, now=NOW, policy=self.policy)

    def test_oversized_malformed_feed_and_object_headers_denied(self):
        with self.assertRaises(d.Denied):
            p.SyntheticEvidenceFeed(({'data': 'X' * (1024 * 1024)},))
        with tempfile.TemporaryDirectory() as tmp:
            a, head = make_git_fixture(tmp)
            reader = p.LooseFixtureGitReader(tmp)
            with self.assertRaises(d.Denied):
                reader.object(head, 'tree')
            with self.assertRaises(d.Denied):
                reader.verify_ancestry('f' * 40, head)

    def test_hash_valid_unsorted_tree_rejected_including_directory_order_rule(self):
        files = {'a': (b'a', '100644'), 'z': (b'z', '100644')}
        with tempfile.TemporaryDirectory() as tmp:
            a, head = make_git_fixture(tmp, new=files, canonical_order=False)
            with self.assertRaisesRegex(d.Denied, 'noncanonical raw Git tree order'):
                p.LooseFixtureGitReader(tmp).tree(head)
            if shutil.which('git'):
                env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
                env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
                result = subprocess.run(['git', 'fsck', '--strict', '--no-reflogs'],
                    cwd=tmp, env=env, capture_output=True, timeout=10, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'treeNotSorted', result.stderr)
        # Directory foo sorts AFTER blob foo.bar, despite sorting bare names.
        files = {'foo/child.txt': (b'child', '100644'), 'foo.bar': (b'blob', '100644')}
        with tempfile.TemporaryDirectory() as tmp:
            a, head = make_git_fixture(tmp, new=files)
            self.assertEqual(set(p.LooseFixtureGitReader(tmp).tree(head)), set(files))
        with tempfile.TemporaryDirectory() as tmp:
            a, head = make_git_fixture(tmp, new=files, canonical_order=False)
            with self.assertRaisesRegex(d.Denied, 'noncanonical raw Git tree order'):
                p.LooseFixtureGitReader(tmp).tree(head)

    def test_hash_valid_malformed_commit_cannot_reach_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, head = make_git_fixture(tmp)
            valid = p.LooseFixtureGitReader(tmp).object(head, 'commit')
            tree, parent, author, committer = valid.split(b'\n\n', 1)[0].split(b'\n')
            if shutil.which('git'):
                env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
                env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
                canonical = subprocess.run(['git', 'fsck', '--strict', '--no-reflogs'],
                    cwd=tmp, env=env, capture_output=True, timeout=10, check=False)
                self.assertEqual(canonical.returncode, 0, canonical.stderr)
            malformed = {
                'missing_author': valid.replace(author + b'\n', b''),
                'missing_committer': valid.replace(committer + b'\n', b''),
                'duplicate_author': valid.replace(author, author + b'\n' + author),
                'duplicate_committer': valid.replace(committer, committer + b'\n' + committer),
                'identity_order': valid.replace(author + b'\n' + committer, committer + b'\n' + author),
                'duplicate_tree': valid.replace(tree, tree + b'\n' + tree),
                'duplicate_parent': valid.replace(parent, parent + b'\n' + parent),
                'null_tree': valid.replace(tree, b'tree ' + b'0' * 40),
                'null_parent': valid.replace(parent, b'parent ' + b'0' * 40),
                'invalid_parent': valid.replace(parent, b'parent ' + b'X' * 40),
                'optional_header': valid.replace(b'\n\n', b'\nencoding UTF-8\n\n', 1),
                'continuation_header': valid.replace(b'\n\n', b'\n ignored continuation\n\n', 1),
                'invalid_email': valid.replace(b'<fixture@example.invalid>', b'fixture@example.invalid'),
                'nested_email': valid.replace(b'<fixture@example.invalid>', b'<<fixture@example.invalid>>'),
                'padded_date': valid.replace(b'1577836800', b'01577836800'),
                'date_overflow': valid.replace(b'1577836800', b'9223372036854775808'),
                'bad_timezone': valid.replace(b'+0000', b'+2460'),
                'missing_separator': valid.replace(b'\n\n', b'\n', 1),
                'nul_message': valid + b'\0',
                'header_cr': valid.replace(author, author + b'\r'),
            }
            for name, content in malformed.items():
                with self.subTest(name=name):
                    oid = put_commit_fixture(tmp, content)
                    (Path(tmp) / '.git/refs/heads' / a['branch']).write_text(oid + '\n')
                    for action in ('tree', 'ancestry', 'candidate'):
                        with self.subTest(action=action), self.assertRaises(d.Denied):
                            reader = p.LooseFixtureGitReader(tmp)
                            if action == 'tree':
                                reader.tree(oid)
                            elif action == 'ancestry':
                                reader.verify_ancestry(a['base'], oid)
                            else:
                                event = snapshot()
                                event['main'] = a['base']
                                event['prs'][0]['head'] = oid
                                event['checks'] = checks(oid)
                                evidence = signed_evidence(self.signer, event, a=a)
                                p.verify_loose_fixture_candidate(directory=tmp, approval=a,
                                    feed=p.SyntheticEvidenceFeed((evidence, evidence)),
                                    evidence_root=self.signer.root, now=NOW, policy=self.policy)
                    if name == 'missing_author' and shutil.which('git'):
                        result = subprocess.run(['git', 'fsck', '--strict', '--no-reflogs'],
                            cwd=tmp, env=env, capture_output=True, timeout=10, check=False)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn(b'missingAuthor', result.stderr)

    def test_ancestry_validates_baseline_and_intermediate_commit_grammar(self):
        for position in ('baseline', 'intermediate'):
            with self.subTest(position=position), tempfile.TemporaryDirectory() as tmp:
                a, head = make_git_fixture(tmp)
                reader = p.LooseFixtureGitReader(tmp)
                valid = reader.object(head, 'commit')
                target = a['base'] if position == 'baseline' else head
                bad = reader.object(target, 'commit')
                bad = b'\n'.join(line for line in bad.split(b'\n') if not line.startswith(b'author '))
                bad_oid = put_commit_fixture(tmp, bad)
                new_head = put_commit_fixture(tmp, valid.replace(
                    ('parent ' + a['base']).encode(), ('parent ' + bad_oid).encode()))
                if position == 'baseline':
                    a['base'] = bad_oid
                    (Path(tmp) / '.git/refs/heads/main').write_text(bad_oid + '\n')
                (Path(tmp) / '.git/refs/heads' / a['branch']).write_text(new_head + '\n')
                for base, candidate in ((a['base'], new_head), (bad_oid, bad_oid)):
                    with self.assertRaises(d.Denied):
                        p.LooseFixtureGitReader(tmp).verify_ancestry(base, candidate)
                event = snapshot()
                event['main'] = a['base']
                event['prs'][0]['head'] = new_head
                event['checks'] = checks(new_head)
                evidence = signed_evidence(self.signer, event, a=a)
                with self.assertRaises(d.Denied):
                    p.verify_loose_fixture_candidate(directory=tmp, approval=a,
                        feed=p.SyntheticEvidenceFeed((evidence, evidence)),
                        evidence_root=self.signer.root, now=NOW, policy=self.policy)

    def test_refs_drift_and_object_replacement_are_not_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, head = make_git_fixture(tmp)
            reader = p.LooseFixtureGitReader(tmp)
            reader.verify_refs(a['branch'], a['base'], head)
            reader.tree(head)
            target = Path(tmp) / '.git/objects' / head[:2] / head[2:]
            value = target.read_bytes()
            target.unlink()
            target.write_bytes(value)
            with self.assertRaises(d.Denied):
                reader.recheck()
            (Path(tmp) / '.git/refs/heads/main').write_text('f' * 40 + '\n')
            with self.assertRaises(d.Denied):
                reader.verify_refs(a['branch'], a['base'], head)


if __name__ == "__main__":
    unittest.main()
