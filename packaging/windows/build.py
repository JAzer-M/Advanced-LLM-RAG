"""在 Windows x64 的独立 Python 3.11 环境执行；生成 PaperLens 文件夹、许可清单和带校验值的预览 ZIP。"""
import hashlib
from importlib.metadata import distributions
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.runtime_paths import APP_VERSION  # noqa: E402


def write_notices(path):
    notices = [f'PaperLens {APP_VERSION} preview — third-party package notices',
               'Weights are downloaded separately from their pinned upstream repositories.']
    for dist in sorted(distributions(), key=lambda d:d.metadata['Name'].lower()):
        notices += ['\n'+'='*72, dist.metadata['Name']+' '+dist.version,
                    'License: '+(dist.metadata.get('License-Expression') or dist.metadata.get('License') or 'See below')]
        for file in dist.files or []:
            if file.name.lower().startswith(('license', 'copying', 'notice')):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    notices += [str(file), source.read_text(encoding='utf-8', errors='replace')]
    path.write_text('\n'.join(notices), encoding='utf-8')


def main():
    if sys.platform != 'win32' or platform.machine().lower() not in ('amd64', 'x86_64') or sys.version_info[:2] != (3, 11):
        raise SystemExit('请在 Windows x64 的独立 Python 3.11 环境构建。')
    work = ROOT/'build/windows'; work.mkdir(parents=True, exist_ok=True)
    os.environ['PYINSTALLER_CONFIG_DIR'] = str(work/'cache')
    write_notices(work/'THIRD_PARTY_NOTICES.txt')
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
                    '--distpath', str(ROOT/'dist/windows'), '--workpath', str(work/'pyinstaller'),
                    str(ROOT/'packaging/windows/PaperLens.spec')], cwd=ROOT, check=True)
    app = ROOT/'dist/windows/PaperLens'
    # 冻结包必须在源码目录之外加载全部依赖，并确认 UTF-8 模式生效，再生成分发文件。
    with tempfile.TemporaryDirectory(prefix='paperlens-build-check-') as folder:
        data = Path(folder)/'data'
        env = {**os.environ, 'PAPERLENS_DATA_DIR':str(data), 'HF_HOME':str(Path(folder)/'hf'),
               'HF_HUB_OFFLINE':'1', 'TRANSFORMERS_OFFLINE':'1'}
        env.pop('PYTHONUTF8', None)  # 只认冻结程序自身的设置
        subprocess.run([str(app/'PaperLens.exe'), '--self-check'], cwd=folder, env=env, check=True, timeout=600)
        check = json.loads((data/'self_check.json').read_text(encoding='utf-8'))
    print(json.dumps(check, ensure_ascii=False))
    if not check.get('frozen') or check.get('utf8_mode') != 1:
        raise SystemExit('冻结程序自检未通过：需要 frozen=True 且 utf8_mode=1。')
    releases = ROOT/'releases'; releases.mkdir(exist_ok=True)
    name = f'PaperLens-{APP_VERSION}-windows-x64-preview'
    archive = Path(shutil.make_archive(str(releases/name), 'zip', root_dir=app.parent, base_dir=app.name))
    with archive.open('rb') as stream: digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    (releases/(archive.name+'.sha256')).write_text(digest+'  '+archive.name+'\n')
    print(json.dumps({'archive':str(archive), 'bytes':archive.stat().st_size, 'sha256':digest}))


if __name__ == '__main__': main()
