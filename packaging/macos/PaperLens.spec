# Apple Silicon 构建；只收集运行代码、网页资源和依赖，不读取项目数据或配置。
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, copy_metadata

root = Path(SPECPATH).parents[1]
import re
version = re.search(r"APP_VERSION = '([^']+)'", (root/'src/runtime_paths.py').read_text(encoding='utf-8')).group(1)
datas = [(str(root / name), '.') for name in ('main.py', 'agent.py')]
datas += [(str(path), 'src') for path in sorted((root / 'src').glob('*.py'))]
datas += [(str(root / 'webui' / name), 'webui') for name in ('index.html', 'app.js', 'style.css')]
# transformers 根据本地源码构造延迟导入表；SentenceTransformer 也会按模型配置动态导入模块。
for package in ('transformers', 'sentence_transformers'):
    datas += collect_data_files(package, include_py_files=True)
for distribution in ('sentence-transformers', 'faiss-cpu', 'pymupdf', 'rank-bm25'):
    datas += copy_metadata(distribution)
datas += [(str(root / 'build' / 'macos' / 'THIRD_PARTY_NOTICES.txt'), '.')]

a = Analysis(
    [str(root / 'paperlens_app.py')], pathex=[str(root)],
    # torchvision 0.29 改为 *_stable.so，现有通用 hook 未收集这些间接加载的库。
    binaries=collect_dynamic_libs('torchvision', search_patterns=['*.so', '*.dylib']), datas=datas,
    hiddenimports=[
        'transformers.models.bert.modeling_bert',
        'transformers.models.bert.tokenization_bert',
        'transformers.models.xlm_roberta.modeling_xlm_roberta',
        'transformers.models.xlm_roberta.tokenization_xlm_roberta',
        'sentence_transformers.sentence_transformer.modules.pooling',
        'sentence_transformers.base.modules.transformer',
        'sentence_transformers.base.modules.normalize',
    ],
    hookspath=[], runtime_hooks=[], excludes=['tkinter', 'IPython', 'matplotlib'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='PaperLens',
          debug=False, strip=False, upx=False, console=False,
          target_arch='arm64', codesign_identity=None, entitlements_file=None)
collection = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='PaperLens')
app = BUNDLE(collection, name='PaperLens.app', bundle_identifier='org.paperlens.desktop',
             info_plist={'CFBundleShortVersionString':version, 'CFBundleVersion':'1',
                         'LSUIElement':True, 'NSHighResolutionCapable':True,
                         'LSMinimumSystemVersion':'14.0'})
