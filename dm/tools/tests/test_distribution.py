import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('pipeline', ROOT / 'dm/tools/distribution_pipeline.py')
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


class DistributionTests(unittest.TestCase):
    def test_paid_profile_and_ios18_keep_identity_without_extra_entitlements(self):
        tools = ROOT / 'dm/ios/tools'
        with tempfile.TemporaryDirectory() as tmp:
            standard, legacy = Path(tmp)/'standard.yml', Path(tmp)/'legacy.yml'
            subprocess.run([sys.executable, tools/'project_distribution.py', ROOT/'dm/ios/project.yml', standard], check=True)
            subprocess.run([sys.executable, tools/'project_m3.py', standard, legacy, 'free'], check=True)
            for path in [standard, legacy]:
                text = path.read_text()
                for forbidden in ['com.apple.developer.icloud', 'com.apple.security.application-groups', 'com.apple.developer.kernel.', 'com.apple.developer.sustained-execution', 'RomfsDownloader:', 'BAUsesAppleHosting:']:
                    self.assertNotIn(forbidden, text)
                self.assertIn('PRODUCT_BUNDLE_IDENTIFIER: ${DM_BUNDLE_ID}', text)
                self.assertIn('DEVELOPMENT_TEAM: ${DM_TEAM_ID}', text)
                self.assertIn('CFBundleDisplayName: D2R 暗黑之旅', text)
                self.assertIn('Network.framework', text)
            self.assertIn('iOS: "18.0"', legacy.read_text())
            self.assertIn('-mcpu=apple-a14 -DDM_NVN_M3=1', legacy.read_text())
            self.assertIn('iOS: "26.0"', standard.read_text())

    def test_resources_use_existing_config_and_reject_other_hosts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            local = root/'源码打包流程/local.env'
            local.parent.mkdir(); local.write_text('DM_FREE_ACCOUNT=0\n')
            base = root/'暗黑2打包工程/full-1.0.4/Payload/SwIOS.app/sw'
            base.mkdir(parents=True)
            for name in ['asset_base.txt', 'astc_pack_base.txt']:
                (base/name).write_text('https://download.a-mini.com/t/test/assets/v1\n')
            before = local.read_bytes()
            env = pipeline.environment(root, True)
            self.assertEqual(env['DM_IOS_M3'], '1')
            self.assertEqual(env['DM_DISTRIBUTION_PROFILE'], '1')
            self.assertEqual(env['DM_ASSET_BASE'], (base/'asset_base.txt').read_text().strip())
            self.assertEqual(env['DM_ASTC_PACK_BASE'], (base/'astc_pack_base.txt').read_text().strip())
            self.assertEqual(before, local.read_bytes())
            (base/'asset_base.txt').write_text('https://other.invalid/assets')
            with self.assertRaises(ValueError): pipeline.environment(root, True)


if __name__ == '__main__': unittest.main()
