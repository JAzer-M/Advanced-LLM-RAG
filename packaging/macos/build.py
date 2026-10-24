"""在专用 Python 3.11 环境执行；生成 .app、许可清单和带校验值的预览 ZIP。"""
import hashlib
from importlib.metadata import distributions
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    if sys.platform != 'darwin' or platform.machine() != 'arm64' or sys.version_info[:2] != (3, 11):
        raise SystemExit('请在 Apple Silicon macOS 的独立 Python 3.11 环境构建。')
    work = ROOT/'build/macos'; work.mkdir(parents=True, exist_ok=True)
    os.environ['PYINSTALLER_CONFIG_DIR'] = str(work/'cache')
    notices = ['PaperLens 0.1.0 preview — third-party package notices',
               'Weights are downloaded separately from their pinned upstream repositories.']
    for dist in sorted(distributions(), key=lambda d:d.metadata['Name'].lower()):
        notices += ['\n'+'='*72, dist.metadata['Name']+' '+dist.version,
                    'License: '+(dist.metadata.get('License-Expression') or dist.metadata.get('License') or 'See below')]
        for file in dist.files or []:
            if file.name.lower().startswith(('license', 'copying', 'notice')):
                path = Path(dist.locate_file(file))
                if path.is_file():
                    notices += [str(file), path.read_text(encoding='utf-8', errors='replace')]
    (work/'THIRD_PARTY_NOTICES.txt').write_text('\n'.join(notices), encoding='utf-8')
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
                    '--distpath', str(ROOT/'dist'), '--workpath', str(work/'pyinstaller'),
                    str(ROOT/'packaging/macos/PaperLens.spec')], cwd=ROOT, check=True)
    app = ROOT/'dist/PaperLens.app'
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    # 冻结包必须从源码目录之外加载成功，再生成分发文件。
    with tempfile.TemporaryDirectory(prefix='paperlens-build-check-') as folder:
        env = {**os.environ, 'PAPERLENS_DATA_DIR':str(Path(folder)/'data'),
               'HF_HOME':str(Path(folder)/'hf'), 'HF_HUB_OFFLINE':'1', 'TRANSFORMERS_OFFLINE':'1'}
        subprocess.run([str(app/'Contents/MacOS/PaperLens'), '--self-check'],
                       cwd=folder, env=env, check=True)
    releases = ROOT/'releases'; releases.mkdir(exist_ok=True)
    archive = releases/'PaperLens-0.1.0-macos-arm64-preview.zip'
    subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(app), str(archive)], check=True)
    with archive.open('rb') as stream: digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    (releases/(archive.name+'.sha256')).write_text(digest+'  '+archive.name+'\n')
    print(json.dumps({'archive':str(archive), 'bytes':archive.stat().st_size, 'sha256':digest}))


if __name__ == '__main__': main()
