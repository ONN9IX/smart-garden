"""Synthetic Oracle ARM64 Free Tier preflight regression tests."""
from pathlib import Path
import importlib.util
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / 'deploy/oracle-a1-preflight.py'
spec = importlib.util.spec_from_file_location('oracle_a1_preflight', MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
GIB = 1024**3


class OracleA1Tests(unittest.TestCase):
    def check(self, arch='aarch64', os_id='ubuntu', release='24.04', cpus=2, ram=12, disk=100):
        return module.check_platform(arch, {'ID': os_id, 'VERSION_ID': release}, cpus,
                                     ram * GIB, disk * GIB)

    def test_approved_profile(self):
        self.assertEqual(self.check(), [])

    def test_rejects_amd_micro_instance(self):
        self.assertTrue(self.check(arch='x86_64', cpus=1, ram=1))

    def test_rejects_wrong_os(self):
        self.assertTrue(self.check(release='22.04'))

    def test_rejects_too_little_ram(self):
        self.assertTrue(self.check(ram=8))

    def test_rejects_too_small_root_volume(self):
        self.assertTrue(self.check(disk=50))

    def test_rejects_too_few_cpus(self):
        self.assertTrue(self.check(cpus=1))

    def test_no_cloud_billing_claim(self):
        source = MODULE_PATH.read_text(encoding='utf-8')
        self.assertIn('only OCI Console can confirm', source)
        self.assertNotIn('ocid1.', source)


if __name__ == '__main__':
    unittest.main()
