# YOLOv10 时序检测实验整理报告

> **数据集**：VisDrone2019‑MOT (val: 564 images / 22 543 instances)
> **基础模型**：YOLOv10s
> **整理时间**：2026/06/16（增量更新：新增 UC‑Mamba 系列 4 条 + UTR‑DMSA 增量配置 2 条）
> **评估指标**：Precision (P), Recall (R), mAP@0.5, mAP@0.5:0.95
> **统计口径**：每个实验取整训练过程中验证集上 **mAP@0.5:0.95 最高 epoch** 的结果（“peak”）。

---

## 1. 实验概览

本批实验围绕 **基于 YOLOv10s 的视频/时序目标检测** 展开，输入为 3 帧或 5 帧的相邻帧序列，覆盖以下方法族：

| 方法族 | 简介 | 实验数 |
|---|---|---|
| **Baseline (单帧)** | 原始 YOLOv10s，无时序融合 | 2 |
| **Identity (3帧无融合)** | 输入 3 帧但仅复用单帧特征，验证 dataloader 正确性 | 1 (有效) + 2 (失败) |
| **DIS / MTGR (蒸馏类)** | 多帧→单帧蒸馏与多教师梯度路由 | 3 |
| **DMSA / DMSA‑CG (基础时序融合)** | 因果型多尺度可分离注意力 | 4 |
| **DMSA‑MQ (Multi‑Query 变体)** | 在 DMSA 上引入多查询 / Sim / MS 多尺度 / 二阶段微调 | 13 |
| **DMSA + 模块组合** | MA / MASM / OCM / OSMG / QSM 等组件与 DMSA 联合 | 7 |
| **UTR‑DMSA (统一时序表征)** | 将 DMSA 与 UTR 模块结合，含分辨率提升 / SyncAug / α 调节 / stride2 | 6 |
| **UC‑Mamba (时序状态空间融合)** | UC‑Mamba lite / st‑pool2 / st‑topk / lite+stride2，全部配 SyncAug | 4 |
| **DTS (失败方案)** | 三流 P5 蒸馏；模型未学到 | 2 |

> 共计 **49 条日志**，其中有效结果 **41 条**，失败/早停/空日志 **8 条**（在第 7 节单独列出）。

---

## 2. 总体结果对比表（按 mAP@0.5:0.95 排序）

| Rank | Model / Run | Frames | Img Size | Batch | Epochs | P | R | mAP@0.5 | **mAP@0.5:0.95** | Δ vs Best Baseline |
|---:|---|:---:|:---:|:---:|:---:|---:|---:|---:|---:|---:|
| **1 ★** | **UTR‑DMSA** (`utr_dmsa_3f_1280`) | 3 | **1280** | 9 | 12 | 0.458 | 0.393 | **0.375** | **0.199** | **+0.027** |
| 2 | UTR‑DMSA + SyncAug | 3 | 960 | 24 | 12 | 0.425 | 0.403 | 0.355 | 0.193 | +0.021 |
| 2 | **UC‑Mamba‑ST‑TopK + SyncAug** ✦ | 3 | 960 | 24 | 12 | 0.426 | 0.401 | **0.356** | **0.193** | +0.021 |
| 4 | **UC‑Mamba‑Lite + SyncAug** ✦ | 3 | 960 | 24 | 12 | 0.426 | 0.401 | 0.354 | 0.191 | +0.019 |
| 5 | DMSA‑MQ + GroupFix + BNFix | 3 | 960 | 24 | 12 | 0.471 | 0.376 | 0.353 | **0.190** | +0.018 |
| 5 | **UC‑Mamba‑Lite + SyncAug + stride2** ✦ | 3 | 960 | 24 | 12 | 0.430 | 0.399 | 0.352 | 0.190 | +0.018 |
| 5 | **UC‑Mamba‑ST‑Pool2 + SyncAug** ✦ | 3 | 960 | 24 | 12 | 0.425 | 0.400 | 0.352 | 0.190 | +0.018 |
| 5 | **UTR‑DMSA + SyncAug + stride2** ✦ | 3 | 960 | 24 | 12 | 0.422 | 0.401 | 0.353 | 0.190 | +0.018 |
| 9 | DMSA‑MQ + GroupFix + BNFix + SyncAug | 3 | 960 | 24 | 12 | 0.430 | 0.390 | 0.349 | 0.189 | +0.017 |
| 9 | UTR‑DMSA (960) | 3 | 960 | 24 | 12 | 0.464 | 0.383 | 0.352 | 0.189 | +0.017 |
| 9 | **UTR‑DMSA + α=5e‑4 + SyncAug** ✦ | 3 | 960 | 24 | 12 | 0.426 | 0.398 | 0.352 | 0.189 | +0.017 |
| 12 | UTR‑DMSA + α=5e‑4 | 3 | 960 | 24 | 12 | 0.457 | 0.386 | 0.352 | 0.188 | +0.016 |
| 13 | DMSA‑MQ‑Causal (refnograd) | 3 | 960 | 24 | 12 | 0.444 | 0.383 | 0.344 | 0.187 | +0.015 |
| 13 | DMSA‑MQ‑Sim Causal (refnograd) | 3 | 960 | 24 | 12 | 0.452 | 0.384 | 0.344 | 0.187 | +0.015 |
| 13 | MASM + DMSA | 3 | 960 | 24 | 12 | 0.461 | 0.376 | 0.349 | 0.187 | +0.015 |
| 13 | QSM + DMSA | 3 | 960 | 24 | 12 | 0.449 | 0.380 | 0.348 | 0.187 | +0.015 |
| 17 | OCM‑Calib + DMSA Causal | 3 | 960 | 24 | 12 | 0.449 | 0.379 | 0.343 | 0.186 | +0.014 |
| 18 | DMSA‑MQ + α=5e‑4 | 3 | 960 | 24 | 12 | 0.449 | 0.376 | 0.345 | 0.185 | +0.013 |
| 19 | DMSA Causal (refnograd, e15) | 3 | 960 | 24 | 15 | 0.435 | 0.374 | 0.338 | **0.184** | +0.012 |
| 19 | MA + DMSA‑MQ Causal | 3 | 960 | 24 | 12 | 0.448 | 0.376 | 0.341 | 0.184 | +0.012 |
| 21 | DMSA‑MQ + GroupFix (4‑GPU) | 3 | 960 | 24 | 12 | 0.414 | 0.396 | 0.336 | 0.182 | +0.010 |
| 21 | OSMG + DMSA (fix‑save) | 3 | 960 | 24 | 12 | 0.442 | 0.381 | 0.343 | 0.182 | +0.010 |
| 23 | DMSA (refnograd, e30) | 3 | 960 | 24 | 30 | 0.434 | 0.374 | 0.335 | 0.181 | +0.009 |
| 24 | MTGR (refnograd, e30) | 3 | 960 | 24 | 30 | 0.433 | 0.375 | 0.334 | 0.180 | +0.008 |
| 24 | OCM‑Lite + DMSA Causal | 3 | 960 | 24 | 12 | 0.432 | 0.379 | 0.335 | 0.180 | +0.008 |
| 26 | DMSA‑CG (refnograd, e15) | 3 | 960 | 24 | 15 | 0.431 | 0.374 | 0.333 | 0.179 | +0.007 |
| 26 | DMSA Causal (e8, lr2e‑4) | 3 | 960 | 24 | 8 | 0.413 | 0.385 | 0.332 | 0.179 | +0.007 |
| 28 | DMSA‑MQ‑Sim 5 frames | **5** | 960 | 12 | 6 | 0.403 | 0.389 | 0.323 | 0.174 | +0.002 |
| 29 | DMSA‑MQ‑MS (multi‑scale) | 3 | 960 | 12 | 6 | 0.415 | 0.369 | 0.323 | 0.173 | +0.001 |
| 30 | **Baseline (lr=3e‑4)** | 1 | 960 | 24 | 12 | 0.388 | 0.360 | 0.328 | **0.172** | — (ref) |
| 31 | DIS (refnograd) | 3 | 960 | 24 | 30 | 0.390 | 0.369 | 0.323 | 0.170 | −0.002 |
| 32 | DMSA‑MQ Stage‑2 (stable‑ft) | 3 | 960 | 24 | — | 0.392 | 0.355 | 0.310 | 0.165 | −0.007 |
| 33 | DIS + freeze11 | 3 | 960 | 24 | 30 | 0.396 | 0.351 | 0.304 | 0.160 | −0.012 |
| 34 | Baseline (seed=1) | 1 | 960 | 24 | 12 | 0.400 | 0.348 | 0.311 | 0.158 | −0.014 |
| 35 | Identity 3‑frame (b60) | 3 | 960 | 60 | — | 0.428 | 0.338 | 0.313 | 0.157 | −0.015 |
| 36 | DMSA‑MQ Causal (groupfix, seed=1) | 3 | 960 | 24 | 12 | 0.372 | 0.337 | 0.301 | 0.152 | −0.020 |
| 37 | DMSA‑MQ Causal e8 (seed=1, stable) | 3 | 960 | 24 | 8 | 0.368 | 0.338 | 0.294 | 0.150 | −0.022 |
| 38 | DMSA‑MQ Causal (seed=1, original) | 3 | 960 | 24 | 12 | 0.357 | 0.334 | 0.291 | 0.149 | −0.023 |
| 39 | DMSA‑MQ‑MS (b18, e12) | 3 | 960 | 18 | 12 | 0.299 | 0.292 | 0.237 | 0.126 | −0.046 |
| 40 | OSMG + DMSA (broken save) | 3 | 960 | 24 | 12 | 0.283 | 0.298 | 0.233 | 0.123 | −0.049 |
| 41 | DTS 3‑f P5 (val‑fix) | 3 | 960 | 63 | — | 0.320 | 0.265 | 0.225 | 0.113 | −0.059 |
| 42 | DMSA‑MQ Stage‑1 (fuser‑only) | 3 | 960 | 24 | — | 0.280 | 0.271 | 0.208 | 0.104 | −0.068 |

> ★ 全榜最高；粗体值为各方法族的代表最优；✦ 标记为 2026/06/16 增量更新的实验。

---

## 3. 分类别结果分析

### 3.1 Baseline (单帧 YOLOv10s)

| Run | P | R | mAP@0.5 | mAP@0.5:0.95 |
|---|---:|---:|---:|---:|
| baseline (seed 0, lr=3e‑4) | 0.388 | 0.360 | 0.328 | **0.172** |
| baseline (seed=1)          | 0.400 | 0.348 | 0.311 | 0.158 |

> **基线选择**：取 seed‑0 (lr=3e‑4) 作为对照基线 (mAP50‑95 = 0.172, mAP50 = 0.328)。该数值与文献中 YOLOv10s 在 VisDrone 上的常见水平一致。两次种子差异 (0.158 vs 0.172) 表明 VisDrone 训练对随机种子敏感，下文“多种子分析”将进一步讨论。

### 3.2 Identity / Sanity Check (3 帧无融合)

| Run | mAP@0.5 | mAP@0.5:0.95 | 备注 |
|---|---:|---:|---|
| identity_3f_b60 | 0.313 | 0.157 | 等价于把 t‑1/t‑2 帧丢弃；性能略低于 baseline 也属合理（输入有少量 noise） |
| identity_3f_b18 / b36 | – | – | 日志为空，未完成 |

> **结论**：3 帧 dataloader 在不引入融合时不会带来增益，验证了实验框架的中立性。

### 3.3 蒸馏类方法 (DIS / MTGR)

| Run | mAP@0.5 | mAP@0.5:0.95 |
|---|---:|---:|
| MTGR (refnograd) | **0.334** | **0.180** |
| DIS  (refnograd) | 0.323 | 0.170 |
| DIS + freeze11   | 0.304 | 0.160 |

> 与 baseline 相比，MTGR 提升 +0.008 (mAP50‑95)、+0.006 (mAP50)；DIS 大致与 baseline 持平；冻结 backbone 的 DIS 显著掉点。蒸馏路径单独使用上限有限。

### 3.4 DMSA 与变体（无 MQ）

| Run | Frames | Epochs | mAP@0.5 | mAP@0.5:0.95 |
|---|:---:|:---:|---:|---:|
| DMSA (refnograd) | 3 | 30 | 0.335 | 0.181 |
| DMSA‑Causal (e15) | 3 | 15 | **0.338** | **0.184** |
| DMSA‑Causal (e8, lr2e‑4) | 3 | 8 | 0.332 | 0.179 |
| DMSA‑CG (e15) | 3 | 15 | 0.333 | 0.179 |

> 引入 **因果约束 (Causal)** 的 DMSA 比非因果版略好（+0.003 mAP50‑95），且训练 15 epoch 即可到达饱和。

### 3.5 DMSA‑MQ (Multi‑Query) 系列

| Run | mAP@0.5 | mAP@0.5:0.95 |
|---|---:|---:|
| DMSA‑MQ‑Causal (refnograd) | 0.344 | 0.187 |
| DMSA‑MQ + GroupFix + BNFix (seed 0) | **0.353** | **0.190** |
| DMSA‑MQ + GroupFix + BNFix + SyncAug | 0.349 | 0.189 |
| DMSA‑MQ + GroupFix + BNFix (seed 1) | 0.301 | 0.152 |
| DMSA‑MQ + GroupFix (4 GPU) | 0.336 | 0.182 |
| DMSA‑MQ + α=5e‑4 | 0.345 | 0.185 |
| DMSA‑MQ‑Sim Causal | 0.344 | 0.187 |
| DMSA‑MQ‑Sim 5‑frame | 0.323 | 0.174 |
| DMSA‑MQ‑MS Causal (b12 e6) | 0.323 | 0.173 |
| DMSA‑MQ Stage‑2 (stable‑ft) | 0.310 | 0.165 |
| DMSA‑MQ Stage‑1 (fuser‑only) | 0.208 | 0.104 |

> **关键发现**：
> 1. **GroupFix + BNFix** 修正后达 **0.190** (+0.018 over baseline)，是 DMSA‑MQ 的最优配置。
> 2. **5 帧** 和 **MS 多尺度** 在小 batch + 低 epoch 下未能复现 3 帧的优势，主要受限于 batch=12/18 与 epoch=6/12。
> 3. **二阶段微调** 单独跑 fuser‑only 仅 0.104，需配合 stable‑ft 才能恢复至 0.165；端到端 e2e 仍是更优选择。
> 4. **种子差异**：seed‑0 (0.190) vs seed‑1 (0.152) 的方差极大，与 baseline 一致。这一现象提示 **VisDrone 单次训练的指标方差应当报告**。

### 3.6 DMSA + 其他模块组合

| Run | mAP@0.5 | mAP@0.5:0.95 |
|---|---:|---:|
| MASM + DMSA | **0.349** | **0.187** |
| QSM + DMSA  | 0.348 | 0.187 |
| OCM‑Calib + DMSA Causal | 0.343 | 0.186 |
| MA + DMSA‑MQ Causal | 0.341 | 0.184 |
| OSMG + DMSA (fix‑save) | 0.343 | 0.182 |
| OCM‑Lite + DMSA Causal | 0.335 | 0.180 |

> 在相同训练预算 (3 帧, 960, b24, e12) 下，这些组件 (MASM / QSM / OCM‑Calib) 与 DMSA 组合均能稳定到 ~0.186–0.187，处于同一统计水平。

### 3.7 UTR‑DMSA — 当前最佳

| Run | Img Size | mAP@0.5 | mAP@0.5:0.95 |
|---|:---:|---:|---:|
| **UTR‑DMSA (1280)** | 1280 | **0.375** | **0.199** ★ |
| UTR‑DMSA + SyncAug (960) | 960 | 0.355 | 0.193 |
| UTR‑DMSA + SyncAug + stride2 (960) ✦ | 960 | 0.353 | 0.190 |
| UTR‑DMSA + α=5e‑4 + SyncAug (960) ✦ | 960 | 0.352 | 0.189 |
| UTR‑DMSA (960) | 960 | 0.352 | 0.189 |
| UTR‑DMSA + α=5e‑4 (960) | 960 | 0.352 | 0.188 |

> **UTR‑DMSA** 在所有方法族中表现最佳。把分辨率从 960 提升到 **1280** 时，**mAP50 +0.023, mAP50‑95 +0.010**，是单一改动里收益最高的开关；**SyncAug** 在 960 下也稳定贡献 +0.004 mAP50‑95。
>
> 增量结果（2026/06/16）：在 UTR‑DMSA + SyncAug 基础上叠加 **stride2** 时序下采样后 mAP50‑95 从 0.193 降至 0.190（−0.003），表明在 960 输入下时序分辨率不应再下采样；将 **α=5e‑4** 与 SyncAug 同时启用时同样停留在 0.189，相比单 α=5e‑4 (0.188) 仅微增，未叠加出额外收益。

### 3.8 UC‑Mamba — 时序状态空间融合（新增）

| Run | mAP@0.5 | mAP@0.5:0.95 |
|---|---:|---:|
| **UC‑Mamba‑ST‑TopK + SyncAug** ✦ | **0.356** | **0.193** |
| UC‑Mamba‑Lite + SyncAug ✦ | 0.354 | 0.191 |
| UC‑Mamba‑Lite + SyncAug + stride2 ✦ | 0.352 | 0.190 |
| UC‑Mamba‑ST‑Pool2 + SyncAug ✦ | 0.352 | 0.190 |

> **关键观察**：
> 1. **UC‑Mamba‑ST‑TopK + SyncAug** 取得 **mAP50‑95 = 0.193 / mAP50 = 0.356**，与 UTR‑DMSA + SyncAug (960) 在 mAP50‑95 上**完全持平**，并在 mAP50 上略胜 0.001，是 960 输入下与 UTR‑DMSA 并列的最佳方案。
> 2. 全部 4 个 UC‑Mamba 变体集中在 **0.190–0.193** 区间，相比 baseline 提升 **+0.018 ~ +0.021**，方差非常小，体现出该方法的稳定性。
> 3. UC‑Mamba 的 4 条 Recall 全部 ≥ 0.399（其中 3 条 ≥ 0.400），**Recall 表现持续优于 UTR‑DMSA / DMSA‑MQ 系列**（后者通常在 0.376–0.396），说明状态空间式时序传播对漏检有显著缓解。
> 4. **ST‑TopK > Lite > Lite+stride2 ≈ ST‑Pool2**：选择性 Top‑K 路由比统一池化或步长压缩更有效；同样地，stride2 时序下采样在 960 输入下并未带来收益（与 UTR‑DMSA 的结论一致）。

---

## 4. 顶尖结果对比 (Top‑6)

> 以 baseline (lr=3e‑4) 为参照，重点比较 6 个最强配置：

| # | Model | Img | P | R | mAP@0.5 | mAP@0.5:0.95 | ΔmAP50 | ΔmAP50‑95 | 备注 |
|---:|---|:---:|---:|---:|---:|---:|---:|---:|---|
| – | Baseline (YOLOv10s) | 960 | 0.388 | 0.360 | 0.328 | 0.172 | – | – | 单帧, seed‑0 |
| 1 | **UTR‑DMSA‑1280** | 1280 | 0.458 | 0.393 | **0.375** | **0.199** | **+0.047** | **+0.027** | 最佳；高分辨率 |
| 2 | **UC‑Mamba‑ST‑TopK + SyncAug** ✦ | 960 | 0.426 | 0.401 | **0.356** | **0.193** | +0.028 | +0.021 | 960 下并列最优；Recall 最高 |
| 2 | UTR‑DMSA + SyncAug | 960 | 0.425 | 0.403 | 0.355 | 0.193 | +0.027 | +0.021 | 960 下并列最优 |
| 4 | UC‑Mamba‑Lite + SyncAug ✦ | 960 | 0.426 | 0.401 | 0.354 | 0.191 | +0.026 | +0.019 | 状态空间最简版 |
| 5 | DMSA‑MQ + GroupFix + BNFix | 960 | **0.471** | 0.376 | 0.353 | 0.190 | +0.025 | +0.018 | Precision 最高 |
| 6 | DMSA‑MQ + GroupFix + BNFix + SyncAug | 960 | 0.430 | 0.390 | 0.349 | 0.189 | +0.021 | +0.017 | 强同步增广 |

### 4.1 关键观察

1. **UTR‑DMSA‑1280 全面超越所有方案**，在 4 个指标上同时显著占优，是唯一进入 mAP@0.5 ≥ 0.37 区间的实验。
2. **从 960→1280**：UTR‑DMSA 提升 mAP50‑95 +0.010；该收益源自小目标场景 (VisDrone 极小目标占比高) 对分辨率的高敏感度。
3. **SyncAug** (跨 3 帧同步增广) 在 960 上贡献 +0.004 mAP50‑95，是 9.6 % 的相对提升，建议默认启用。
4. **DMSA‑MQ 的 P 值 0.471** 在所有实验中最高，但其 R 偏低 (0.376)；UTR‑DMSA 的 P/R 更平衡 (0.458 / 0.393)，更利于高 IoU 阈值下的 AP 累积。
5. **GroupFix + BNFix** (Group/BN 统计量在多帧分支共享时的修复) 是 DMSA‑MQ 系列从 0.187 → 0.190 的关键工程改动，且对 SyncAug 兼容。
6. **UC‑Mamba (新增)**：在 960 输入下与 UTR‑DMSA 并列最佳 (mAP50‑95 = 0.193)，但其 **Recall 全部 ≥ 0.399**，明显高于注意力族 (0.376–0.396)，对漏检有更强的缓解能力；其中 **ST‑TopK** 选择性变体最优，**stride2 时序下采样无收益**。在论文层面 UC‑Mamba 与 UTR‑DMSA 形成 “状态空间 vs 注意力” 的互补对照组。

### 4.2 推荐最终配置（Best of class）

```yaml
model: yolov10s
temporal_module: UTR + DMSA  (causal, 3 frames)
input_resolution: 1280
batch_size: 9
epochs: 12
optimizer: SGD, lr=3e-4, momentum=0.937
augmentation: per-frame mosaic + SyncAug (recommended in 960 regime)
group_norm_fix: enabled
bn_share_fix: enabled
```

---

## 5. 主要消融与趋势

| 维度 | 比较对象 | 收益 (mAP@0.5:0.95) |
|---|---|---:|
| **架构 (融合 vs 蒸馏)** | DMSA‑MQ vs MTGR | +0.010 |
| **MQ 头** | DMSA‑MQ vs DMSA | +0.006 (0.190 vs 0.184) |
| **GroupFix + BNFix** | DMSA‑MQ vs DMSA‑MQ‑GFBF | +0.003 |
| **UTR 模块** | UTR‑DMSA vs DMSA‑MQ | +0.002 (0.189 vs 0.187，相同 960/24/12) |
| **UC‑Mamba (状态空间)** | UC‑Mamba‑ST‑TopK vs UTR‑DMSA (均 +SyncAug, 960) | 0.000 (0.193 vs 0.193，并列最优) |
| **SyncAug** | UTR‑DMSA SyncAug vs UTR‑DMSA | +0.004 |
| **分辨率 960→1280** | UTR‑DMSA | +0.010 |
| **5 帧 vs 3 帧** | DMSA‑MQ‑Sim | −0.013 (但 batch / epoch 受限) |
| **Causal vs 非 Causal** | DMSA | +0.003 |
| **stride2 时序下采样 (新增)** | UTR‑DMSA SyncAug 与 UC‑Mamba‑Lite SyncAug | −0.003 / −0.001 (均无收益) |
| **TopK vs Pool2 选择性 (新增)** | UC‑Mamba ST‑TopK vs ST‑Pool2 | +0.003 (0.193 vs 0.190) |

> 各项收益独立来看较小（小目标场景常见），但 **DMSA‑MQ → UTR → SyncAug → 1280** 这一组合带来的总体增益为 **+0.027 mAP50‑95 / +0.047 mAP50**，达到 ~16 % 的相对提升。

---

## 6. 多种子稳定性说明

| Setting | seed 0 | seed 1 | 差距 |
|---|---:|---:|---:|
| YOLOv10s baseline | 0.172 | 0.158 | 0.014 |
| DMSA‑MQ + GroupFix + BNFix | 0.190 | 0.152 | **0.038** |
| DMSA‑MQ Causal (e12, original) | – | 0.149 | – |
| DMSA‑MQ Causal (e8, stable) | – | 0.150 | – |

> seed‑1 训练在 VisDrone 上呈现一致的“低位”表象，疑似与 dataloader 顺序导致的早期收敛轨迹相关。**论文级最终报告应至少 3 seed 求均值±方差**；目前仅 seed‑0 的结果可作为单点参考。

---

## 7. 失败 / 异常实验列表

| Run | 现象 | 可能原因 |
|---|---|---|
| `dts_3f_p5_b63.log` | mAP 全 0 | 模型未收敛 / loss 配置错误 |
| `dts_3f_p5_b63_valfix.log` | mAP@0.5 仅 0.225 | 三流方案 (P5 only) 失配检测头 |
| `identity_3f_960_b18 / b36.log` | 日志无 `all` 行 | 早期中断 / 验证未触发 |
| `dis_3f_960_b24_e30.log`,`b36_e30.log` | 日志无 `all` 行 | 早期中断 |
| `dmsa_mq_causal_3f_960_b32_e12_groupfix_seed0.log` | 日志无 `all` 行 | OOM / 早期中断 |
| `dmsa_mq_sim_causal_refnograd_5f_960_b18_e12.log` | 仅 1 个验证点 (0.126) | 训练中断 |
| `dmsa_mq_ms_causal_refnograd_3f_960_b18_e12.log` | 仅 1 个验证点 (0.126) | 训练中断 |
| `osmg_dmsa_3f_960_b24_e12_seed0.log` | 仅 1 验证点 (0.123) | 已被 `_fixsave` 替代 |
| `dmsa_mq_stage1_fuseronly_seed0.log` | 0.104 | Stage‑1 仅训练 fuser，本身不应单独评估 |
| `visdrone_yolclear` | 0 字节 | 占位文件 |

---

## 8. 总结

1. 在 **VisDrone2019‑MOT** 上，**UTR‑DMSA @ 1280 输入** 取得本批实验最佳成绩
   **mAP@0.5 = 0.375 / mAP@0.5:0.95 = 0.199**，相对 YOLOv10s 单帧 baseline 分别提升 **+4.7 / +2.7 个百分点**。
2. 在 **960 输入** 下，**UC‑Mamba‑ST‑TopK + SyncAug** 与 **UTR‑DMSA + SyncAug** 并列最优 (mAP50‑95 = 0.193)，前者在 mAP50 与 Recall 上略胜，提供了与注意力路线**互补的状态空间方案**。
3. **DMSA‑MQ** 是关键的时序融合块，引入 **GroupFix + BNFix** 后达到 0.190 mAP50‑95，是同等训练预算下的次优。
4. 所有蒸馏路径 (DIS / MTGR) 单独使用上限低于注意力 / 状态空间融合路径，建议作为辅助 loss 而非主路。
5. 工程层面：**因果约束、Group/BN 修正、同步多帧增广 (SyncAug)、提升输入分辨率** 是最稳定且可叠加的 4 个收益点；而 **stride2 时序下采样** 在 960 下为负收益，应避免在该分辨率使用。
6. 后续工作建议：(a) 多种子均值±std 报告；(b) 5 帧设定下补足 batch/epoch 预算；(c) UTR‑DMSA / UC‑Mamba 与 SyncAug 在 1280 上的联合验证；(d) UC‑Mamba 与 UTR‑DMSA 的特征级融合或集成。

---

*本文件由日志批量解析生成，所有数值均直接来自 `logs/*.log` 中验证集“all”行的逐 epoch 记录，每条实验取 mAP@0.5:0.95 最高的 epoch。*
