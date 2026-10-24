原始 FlashAttention 论文指出，IO 减少涉及的 GPU 内存层级为 GPU 高带宽内存（HBM）与 GPU 片上 SRAM，并通过 tiling 技术减少这两者之间的内存读写/传输[12]。该论文进一步说明，tiling 可避免在（相对较慢的）GPU HBM 上物化大型 N×N 注意力矩阵[14]。

来源：
[12] 2205.14135v2.pdf，p.1；[固定版本PDF](https://arxiv.org/pdf/2205.14135v2)
[14] 2205.14135v2.pdf，p.2；[固定版本PDF](https://arxiv.org/pdf/2205.14135v2)
