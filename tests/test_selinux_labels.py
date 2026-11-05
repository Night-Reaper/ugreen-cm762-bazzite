"""Exercise label setup with fake policy tools; never touch host SELinux."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LabelSetupTests(unittest.TestCase):
    def check_setup(self, existing):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            payload = root / 'payload/kernel'
            firmware = payload / 'aic8800D80'
            firmware.mkdir(parents=True)
            (payload / 'aic_load_fw.ko').touch()
            (firmware / 'fw.bin').touch()
            commands = root / 'bin'
            commands.mkdir()
            tools = {
                'id': '#!/bin/sh\necho 0\n',
                'semanage': '''#!/bin/sh
printf '%s\\n' "$*" >> "$TEST_TRACE"
if [ "$1" = fcontext ] && [ "$2" = -l ] && [ "$CTX_EXIST" = 1 ]; then
 printf '%s\\n' '/var/lib/aic8800-ugreen/[^/]+/aic(8800_fdrv|_load_fw)\\.ko  regular file  system_u:object_r:modules_object_t:s0'
 printf '%s\\n' '/var/lib/aic8800-ugreen/[^/]+/aic8800D80/[^/]+  regular file  system_u:object_r:lib_t:s0'
fi
''',
                'restorecon': '#!/bin/sh\nprintf "restorecon %s\\n" "$*" >> "$TEST_TRACE"\n',
            }
            for name, content in tools.items():
                file = commands / name
                file.write_text(content)
                file.chmod(0o755)
            script = (ROOT / 'packaging/selinux-labels.sh').read_text()
            script = script.replace('base=/var/lib/aic8800-ugreen', f'base={root}/payload')
            script = script.replace('/var/tmp/aic8800-selinux-backup.', f'{root}/backup.')
            file = root / 'run.sh'
            file.write_text(script)
            trace = root / 'trace'
            env = dict(os.environ, PATH=f'{commands}:' + os.environ['PATH'],
                       TEST_TRACE=str(trace), CTX_EXIST=str(int(existing)))
            subprocess.run(['bash', str(file)], env=env, check=True, capture_output=True, text=True)
            calls = trace.read_text()
            action = '-m' if existing else '-a'
            self.assertIn(f'fcontext {action} -f f -t modules_object_t ', calls)
            self.assertIn(f'fcontext {action} -f f -t lib_t ', calls)
            self.assertIn('restorecon -RFv ', calls)
            self.assertNotIn('setenforce', calls)
            self.assertTrue(list(root.glob('backup.*/semanage-before.txt')))

    def test_new_rules(self):
        self.check_setup(False)

    def test_existing_rules(self):
        self.check_setup(True)


if __name__ == '__main__':
    unittest.main()
