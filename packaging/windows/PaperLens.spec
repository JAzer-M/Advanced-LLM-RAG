# Windows x64 构建；只收集运行代码、网页资源和依赖，不读取项目数据或配置。
import re
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, copy_metadata

root = Path(SPECPATH).parents[1]
datas = [(str(root / name), '.') for name in ('main.py', 'agent.py')]
datas += [(str(path), 'src') for path in sorted((root / 'src').glob('*.py'))]
datas += [(str(root / 'webui' / name), 'webui') for name in ('index.html', 'app.js', 'style.css')]
# transformers 根据本地源码构造延迟导入表；SentenceTransformer 也会按模型配置动态导入模块。
for package in ('transformers', 'sentence_transformers'):
    datas += collect_data_files(package, include_py_files=True)
for distribution in ('sentence-transformers', 'faiss-cpu', 'pymupdf', 'rank-bm25'):
    datas += copy_metadata(distribution)
datas += [(str(root / 'build' / 'windows' / 'THIRD_PARTY_NOTICES.txt'), '.')]

a = Analysis(
    [str(root / 'paperlens_app.py')], pathex=[str(root)],
    # 与 macOS 相同：torchvision 的部分本地库由间接加载，通用 hook 不一定收集到。
    binaries=collect_dynamic_libs('torchvision', search_patterns=['*.pyd', '*.dll']), datas=datas,
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
# 项目文件均为 UTF-8；中文 Windows 默认代码页不是 UTF-8，因此冻结程序启用 UTF-8 模式（构建脚本会核对）。
exe = EXE(pyz, a.scripts, [('X utf8', None, 'OPTION')], exclude_binaries=True, name='PaperLens',
          debug=False, strip=False, upx=False, console=False, disable_windowed_traceback=True)
collection = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='PaperLens')
