"""Independent synthetic tree-delta checks, NOT real Git/Windows isolation."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "windows"))
import dispatcher as d
import publisher as p
from test_windows_dispatcher import approval, BASE, HEAD


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


if __name__ == "__main__":
    unittest.main()
