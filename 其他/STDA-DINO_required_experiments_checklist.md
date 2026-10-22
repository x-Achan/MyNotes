# STDA-DINO 投稿前需要补充的实验与确认清单

这份清单用于把当前 STDA-DINO 第一版论文从“可写成投稿初稿”推进到“更接近可直接投稿”。优先级按审稿风险排序。

---

## 0. 当前论文主线建议

**建议论文名称：** STDA-DINO  
**建议核心贡献：** Small-object-aware Temporal Deformable Alignment for VideoMamba-DINO  
**暂不建议主打：** Query Temporal Mamba / STDA-QM  
**原因：** 当前最优结果来自 `V3 + Plan C`，best mAP = 0.7069；QTM-v1 best mAP = 0.6878，未超过主方法。

论文主张应控制为：

> 在 VideoMamba-DINO 框架下，显式的小目标感知可变形时序对齐能够稳定提升交通监控视频中心帧检测性能。

不要写成：

> 本方法全面超过 YOLOv10 或所有现有检测器。

---

## 1. P0 必须补充：DenseEval 主结果

### 问题

当前主消融结果里 `V3 + Plan C` 的 best mAP = 0.7069，但需要确认它对应的是哪一种评估滑窗设置。你补充的信息里说明：

- VideoMamba-DINO 的 “full” 和 “split60” 使用同一个 60/20/20 序列级划分；
- 差异在于评估滑窗步长：full 使用 `sliding_step=16`，split60 使用 `sliding_step=5`；
- YOLOv10-S 使用的是从同一序列划分导出的帧数据，val/test 为 step=5。

### 必补内容

在 `sliding_step=5` / DenseEval 设置下重新评估：

| Method | Checkpoint | sliding_step | mAP50-95 | mAP50 | mAP75 | AP_S | AP_M | AP_L |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| VideoMamba-DINO none | best | 5 | TODO | TODO | TODO | TODO | TODO | TODO |
| STDA-DINO V3 + Plan C | best | 5 | TODO | TODO | TODO | TODO | TODO | TODO |

### 论文用途

这张表用于和 YOLOv10-S 做更公平对比。没有这组结果时，论文中不能强行把 `0.7069` 与 YOLOv10-S 的 `0.6381` 直接对比，因为评估密度可能不同。

---

## 2. P0 强烈建议：DINO-R50 或 RT-DETR baseline

### 问题

目前没有单独训练纯 DINO 或 RT-DETR baseline。由于 STDA-DINO 使用 DINO 检测头，审稿人可能会问：

> 提升到底来自时序对齐，还是来自 DINO 检测头本身？

### 最低补充方案

优先跑一个：

| Baseline | 推荐程度 | 原因 |
|---|---:|---|
| DINO-R50 4-scale | 最高 | 与你的检测头最一致，最公平 |
| RT-DETR-R50 | 高 | 强 DETR-like 工程基线，速度有说服力 |
| Deformable DETR-R50 | 中 | 经典 DETR-like baseline，但性能可能偏弱 |

### 建议表格

| Method | Backbone | Temporal Input | Detector Head | mAP50-95 | mAP50 | mAP75 | Params | FPS |
|---|---|---|---|---:|---:|---:|---:|---:|
| DINO-R50 | ResNet-50 | single frame | DINO | TODO | TODO | TODO | TODO | TODO |
| RT-DETR-R50 | ResNet-50 | single frame | RT-DETR | TODO | TODO | TODO | TODO | TODO |
| VideoMamba-DINO none | VideoMamba-Tiny | 8-frame clip | DINO | TODO | TODO | TODO | TODO | TODO |
| STDA-DINO | VideoMamba-Tiny | 8-frame clip | DINO + STDA | TODO | TODO | TODO | TODO | TODO |

### 如果时间不够

至少跑 DINO-R50。RT-DETR 可以作为可选补充。

---

## 3. P0 必须补充：效率指标

### 需要报告

| 指标 | STDA-DINO 当前状态 | 需要补充 |
|---|---|---|
| Params | 约 33.5M | 精确值 |
| FLOPs | 未提供 | 需要用固定输入 544×960、T=8 统计 |
| FPS / latency | 未提供 | 单卡 A30 上推理速度 |
| Memory | 未提供 | 可选，最好有 |

### 建议写法

至少给出：

```text
All speed measurements are conducted on a single NVIDIA A30 GPU with batch size 1.
```

建议表格：

| Method | Input | T | Params | FLOPs | FPS | mAP50-95 |
|---|---:|---:|---:|---:|---:|---:|
| YOLOv10-S | 960 | 1 | TODO | TODO | TODO | 0.6381 |
| STDA-DINO | 544×960 | 8 | TODO | TODO | TODO | TODO |

### 注意

STDA-DINO 很可能比 YOLOv10 慢，所以论文表述要强调：

> 本文关注视频时序建模和对齐机制，不以实时单帧检测器替代为主要目标。

---

## 4. P1 建议补充：V3 参数消融

当前 V1/V2/V3 是组合消融，可以证明总体设计演进，但还不能充分说明每个设计点的必要性。建议至少补 2-3 个最关键消融。

### 4.1 temporal radius

| Setting | Temporal Coverage | mAP50-95 | mAP50 | Notes |
|---|---|---:|---:|---|
| radius = 2 | 5 frames | TODO | TODO | V2 相关设置 |
| radius = 3 | 7 frames | TODO | TODO | 当前 V3 |
| radius = 4 | 8/9 frames | TODO | TODO | 如果 T=8，需要说明边界裁剪 |

### 4.2 gate bias

| Setting | Initial Gate | mAP50-95 | Notes |
|---|---|---:|---|
| bias = -1.0 | more open | TODO | 可能引入噪声 |
| bias = -2.0 | conservative | TODO | 当前 V3 |
| bias = -3.0 | more closed | TODO | 可能抑制时序信息 |

### 4.3 reliability branch

| Setting | mAP50-95 | Notes |
|---|---:|---|
| w/o reliability | TODO | 证明可靠性加权是否有效 |
| w/ reliability | TODO | 当前 V3 |

### 4.4 level-aware sampling

| Setting | High-res points/offset | Low-res points/offset | mAP50-95 |
|---|---|---|---:|
| uniform | 4 / 4.0 | 4 / 4.0 | TODO |
| level-aware | 4 / 2.0 | 3 / 3.0 | TODO |

### 最小可接受版本

如果时间紧，至少补：

1. `radius=2 vs radius=3`
2. `gate bias=-1 vs -2`
3. `w/o reliability vs w/ reliability`

---

## 5. P1 建议补充：Plan C 训练策略拆分

当前 Plan C 同时改变了：

- fpn_lr_multiplier: 1.0 → 0.1
- weight_decay: 0.001 → 0.005
- drop_path: 0.2 → 0.3
- lr_drop_epochs: [10,14] → [4,8]

审稿人可能会认为这是调参得到的结果。建议补一个训练策略拆分表。

| Setting | fpn_lr | wd | drop_path | lr_drop | mAP50-95 |
|---|---:|---:|---:|---|---:|
| Default | 1.0 | 0.001 | 0.2 | [10,14] | 0.7017 |
| Default + low fpn_lr | 0.1 | 0.001 | 0.2 | [10,14] | TODO |
| + stronger wd | 0.1 | 0.005 | 0.2 | [10,14] | TODO |
| + stronger drop_path | 0.1 | 0.005 | 0.3 | [10,14] | TODO |
| Plan C | 0.1 | 0.005 | 0.3 | [4,8] | 0.7069 |

如果只能补一个，优先补：

> Default vs only fpn_lr=0.1 vs Plan C

---

## 6. P1 建议补充：定性可视化

至少准备 4 张图，每张图包含：

- Center frame image
- VideoMamba-DINO none results
- STDA-DINO results
- Ground truth

建议场景：

| 场景 | 目的 |
|---|---|
| 远距离小车辆 | 展示小目标召回提升 |
| 运动模糊车辆 | 展示时序上下文补偿 |
| 部分遮挡 | 展示邻帧证据帮助检测 |
| 密集车流 | 展示可靠性加权减少错检 |

论文中的表达可以是：

> STDA-DINO recovers several missed small vehicles under blur and partial occlusion, while the no-fusion baseline tends to miss low-resolution targets.

---

## 7. P2 可选：VisDrone 长训练或重新定位

当前 VisDrone-MOT 结果较低：

| Method | mAP50-95 | mAP50 |
|---|---:|---:|
| STDA-DINO V3 base | 0.0959 | 0.1998 |
| STDA-DINO V3 large | 0.1096 | 0.2273 |
| YOLOv10-S | 0.1402 | 0.2740 |

### 建议

如果没有时间继续训练，不要把 VisDrone 作为主结果。可以作为 limitation 或 exploratory study。

如果要补，建议：

- 输入固定为 768×1280；
- queries = 900；
- 训练至少 36 epochs；
- 对比 YOLOv10-S 960；
- 重点观察 AP_small。

---

## 8. P2 可选：QTM 后续实验

当前 QTM-v1 不建议写成核心贡献。

### 可以尝试的方向

| 方向 | 说明 |
|---|---|
| QTM-v2 proposal-level context | 不用全局池化，改为 proposal/query 局部上下文 |
| Mamba vs GRU/Transformer | 证明 Mamba 不是随意替换 |
| gate bias 调参 | -2 可能过保守或不适合 query-level |
| 只作用于 high-confidence proposals | 减少噪声 query 注入 |

### 论文处理建议

当前第一版论文中只在 limitation/future work 提到 QTM，不放主贡献。

---

## 9. 投稿前最小完成包

如果时间有限，完成下面 5 项即可投稿更稳：

1. **DenseEval：STDA-DINO V3 + Plan C, sliding_step=5**
2. **DenseEval：VideoMamba-DINO none, sliding_step=5**
3. **DINO-R50 baseline 或 RT-DETR-R50 baseline，至少一个**
4. **Params + FPS，至少不要缺效率指标**
5. **3-4 张 qualitative detection figures**

---

## 10. 最终论文表格建议

### Table 1: Main controlled ablation

none / motion_guided / V1 / V2 / V3 / V3 + Plan C

### Table 2: Comparison with practical detectors

YOLOv10-S / DINO-R50 / RT-DETR-R50 / VideoMamba-DINO none / STDA-DINO

### Table 3: STDA design ablation

radius / gate bias / reliability / level-aware sampling

### Table 4: Efficiency comparison

Params / FLOPs / FPS / mAP

### Figure 1: Overall architecture

VideoMamba → Aggregator → SFP → STDA → DINO

### Figure 2: STDA module

center frame reference → offset prediction → grid sampling → reliability attention → residual gate

### Figure 3: Qualitative comparison

none vs STDA-DINO on small/blurred/occluded objects

---

## 11. 可以直接放进论文的说明句

### 关于 YOLOv10

> YOLOv10-S is reported as a strong practical image detector under the same sequence-level split. However, our main objective is not to replace highly optimized real-time single-frame detectors, but to investigate whether explicit temporal deformable alignment improves a VideoMamba-DINO video detection framework.

### 关于 DenseEval

> For fair comparison with frame-based detectors, we additionally evaluate the video model under the same dense frame sampling protocol used by the exported YOLO-format validation/test sets.

### 关于 QTM

> Although query-level temporal modeling is conceptually complementary to feature-level alignment, our current QTM prototype does not improve over STDA-DINO. We therefore leave proposal-level query temporal modeling as future work.

---

## 12. 当前不建议写的说法

不要写：

- “Our method achieves state-of-the-art performance on UA-DETRAC.”
- “Our method outperforms YOLOv10.”
- “Query Mamba is the key reason for performance improvement.”
- “The method generalizes well to VisDrone.”

可以写：

- “STDA consistently improves the VideoMamba-DINO baseline under controlled ablation.”
- “The results validate the effectiveness of explicit feature-level temporal alignment.”
- “YOLOv10-S is included as a strong practical detector reference.”
- “Cross-dataset generalization remains an open direction.”
