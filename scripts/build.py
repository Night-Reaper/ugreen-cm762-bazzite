#!/usr/bin/env python3
"""Build the exact vendor archive with local compatibility patches. No sudo/network."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tarfile
import zipfile

ARCHIVE_SHA256 = '85d3e0d62d82f874ad3aa3fe12061658aeca570adfeccff526c055a5e6218bd6'
ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def manifest(folder):
    lines = [f'{digest(p)}  {p.relative_to(folder)}' for p in sorted(folder.rglob('*'))
             if p.is_file() and p.name != 'SHA256SUMS']
    (folder / 'SHA256SUMS').write_text('\n'.join(lines) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path, help='Official UGREEN AX900 LinuxDriver V1.1 zip')
    parser.add_argument('--kernel', default=os.uname().release)
    parser.add_argument('--output', type=Path, default=ROOT / 'build')
    parser.add_argument('--prepare-only', action='store_true', help='Verify, extract and apply patch without compiling')
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error('Build as your normal user, not root.')
    if '/' in args.kernel or args.kernel in {'.', '..'}:
        parser.error('Invalid kernel release')
    for tool in ['git'] + ([] if args.prepare_only else ['make', 'modinfo']):
        if not shutil.which(tool):
            parser.error(f'Missing build dependency: {tool}')
    if digest(args.archive) != ARCHIVE_SHA256:
        parser.error('Archive SHA256 mismatch. This patch is only reviewed for the documented V1.1 archive.')
    output = args.output.resolve()
    if output.exists():
        parser.error(f'{output} already exists. Choose a new --output directory; existing files are preserved.')
    headers = Path('/lib/modules') / args.kernel / 'build'
    if not args.prepare_only and not (headers / 'Makefile').is_file():
        parser.error(f'Missing matching kernel development files: {headers}')
    with zipfile.ZipFile(args.archive) as archive:
        for entry in archive.infolist():
            path = Path(entry.filename)
            mode = entry.external_attr >> 16
            if path.is_absolute() or '..' in path.parts or stat.S_ISLNK(mode):
                parser.error('Unsafe archive member')
        output.mkdir(parents=True)
        archive.extractall(output / 'vendor')
    source = output / 'vendor/aic8800_linux_driver'
    subprocess.run(['git', 'apply', '--unsafe-paths', f'--directory={source}',
                    str(ROOT / 'patches/linux-7.2.patch')], check=True)
    if args.prepare_only:
        print(f'Archive verified and patch applied: {source}')
        return
    driver = source / 'drivers/aic8800'
    with (output / 'build.log').open('w') as log:
        result = subprocess.run(['make', '-C', str(headers), f'M={driver}', '-j4', 'modules'],
                                stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise SystemExit(f'Build failed. Inspect {output / "build.log"}; nothing was installed.')
    bundle = output / 'install'
    payload = bundle / 'payload'
    payload.mkdir(parents=True)
    for name in ['aic_load_fw', 'aic8800_fdrv']:
        module = driver / name / f'{name}.ko'
        vermagic = subprocess.check_output(['modinfo', '-F', 'vermagic', str(module)], text=True)
        if vermagic.split()[0] != args.kernel:
            raise SystemExit(f'Kernel mismatch in {module}')
        shutil.copy2(module, payload / module.name)
    shutil.copytree(source / 'fw/aic8800D80', payload / 'aic8800D80')
    shutil.copy2(ROOT / 'patches/linux-7.2.patch', payload / 'ugreen-linux72.patch')
    with tarfile.open(payload / 'patched-source.tar.gz', 'w:gz') as archive:
        for path in sorted(source.rglob('*')):
            if path.is_file() and (path.suffix in {'.c', '.h', '.mk', '.ini', '.txt'}
                                   or path.name in {'Makefile', 'Kconfig'}):
                archive.add(path, arcname=str(Path('ugreen-source') / path.relative_to(source)))
    for path in (ROOT / 'packaging').iterdir():
        shutil.copy2(path, bundle / path.name)
    shutil.copy2(ROOT / 'README.md', bundle / 'README.md')
    for path in ROOT.glob('LICENSE*'):
        shutil.copy2(path, bundle / path.name)
    (bundle / 'KERNEL').write_text(args.kernel + '\n')
    manifest(payload)
    manifest(bundle)
    print(f'Build successful for {args.kernel}. Review {output / "build.log"}.')
    print(f'Install: sudo bash {bundle / "install.sh"}')
    print('No system changes or reboot were performed by this build.')


if __name__ == '__main__':
    main()
