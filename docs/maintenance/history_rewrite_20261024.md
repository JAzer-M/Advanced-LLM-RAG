# 2026-10-24 推送前历史改写

推送到 GitHub 之前，对 `origin/main`（`c2cd612`）之后尚未推送的 6 个提交做了一次改写：

- 作者与提交者统一为 `JAzer-M <d1599356723@163.com>`（其中 5 个原为本机默认身份）
- 从每个提交中移除 `docs/chat_history/`（对话导出只保存在作者本机）

提交内容的其余部分没有变化，但提交号全部改变。归档快照、补丁和验收 JSON 中记录的是改写前的提交号，按原样保留，可用下表对照：

| 改写前 | 改写后 | 提交说明 |
| --- | --- | --- |
| `00d7f6e1231e017bf723a492475b1496a4f2f42d` | `5c73cefb8cd93dd9547b8763805705f8d5b2f81f` | Snapshot Agent/Auto, arXiv evidence and PaperLens web UI before frontend redesign |
| `5a4cd858ecbf288656f3523108f4560a6151607b` | `2dbe1dd7544a01d6ff18e37bd573a5e173a950fd` | Finalize PaperLens redesign and consolidate P4 evidence |
| `86f5c45e8e0b875b07f136c95cc61e3bf3e93d14` | `2dd80cf973bbe61d21aaabf4dea1ec5349fbb382` | Package PaperLens as a macOS preview app and record acceptance |
| `15dfde878c6c473ac1bd5946945d834595f3cc1c` | `436625e6be8bb05d0caff5ee81a049be739c273e` | Include packaging tests in the documented web test command |
| `49be235b64dc4b3f5f2419509e14ff12a2e6e5ac` | `8b7fbf22ec45d5227bd0b3994f6c48f77edc4a81` | Showcase README, MIT license, CI, and stop publishing chat exports |
| `2db05f67eb32ccccf609a24fca52b839eeed17f6` | `c19f9986420821882cc0096c56918f8c629659e2` | Skip the local-KB replay test in clean checkouts; note release prep |

当前文档（PROGRESS、ui_prototype/README、macOS 下载包报告）已改用新提交号。
