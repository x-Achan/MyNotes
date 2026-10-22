# YOLOv10-Temporal 项目深度体检与方法梳理报告

> 生成时间：2026-06-13  
> 适用：用于学习项目内部所有时序方法的设计动机、实现细节与对比关系，并作为后续汇报的方法/流程图蓝本。  
> 阅读顺序建议：1 → 2 → 3 → 4 → 5。

---

## 0. 一句话总览

本项目把"VideoMamba-DINO 作为完整视频检测器"的失败路线（`temporal_yolo_research_plan.md`）换成了
"**强单帧检测器 YOLOv10-S + 可插拔时序特征聚合模块**"，并按
`identity → concat → motion → dis → mtgr → dmsa → dmsa_cg → dmsa_causal → dmsa_mq → dmsa_mq_sim → dmsa_mq_ms → ocm_dmsa(_calib) → ma_dmsa_mq`
的顺序逐步迭代。所有变体共用同一份骨架（YOLOv10-S backbone + neck + v10Detect head + `TemporalYOLODataset` clip dataloader），唯一差别是
`ultralytics/nn/modules/temporal.py::TemporalFeatureFusion` 中的 `mode` 分支，以及 yaml 中的
`temporal.fuse_layers / replace_layers / target / reference_grad` 配置。**当前最佳是 DMSA-MQ causal 3f**
（seed=0 best `mAP50=0.344, mAP50-95=0.187`，比单帧 baseline `0.333/0.172` 高 +0.011/+0.015），
但 seed=1 复现只有 `0.291/0.149`，**稳定性是主要风险**。

---

## 1. 项目架构总览（必看）

### 1.1 主要文件分工

| 模块 | 路径 | 职责 |
|---|---|---|
| 时序数据集 | `ultralytics/data/dataset.py::TemporalYOLODataset` | 把单帧样本扩展成 `[B,T,C,H,W]` clip；按 sequence 分组、按 stride 取相邻帧；支持 `temporal_causal=True` 仅取过去帧 |
| dataloader 装配 | `ultralytics/data/build.py` | `temporal_frames>1` 时切换到 `TemporalYOLODataset`，并强制 `augment=False` 保证多帧同步 |
| CLI 参数 | `ultralytics/cfg/default.yaml` + `ultralytics/cfg/__init__.py` | 暴露 `temporal_frames / temporal_stride / temporal_causal` |
| 模型 forward | `ultralytics/nn/tasks.py::YOLOv10DetectionModel` | 解析 yaml 中的 `temporal:` 字段；支持两种 forward：(a) 全帧带梯度，(b) 中心帧带梯度 / 参考帧 no-grad |
| 时序融合模块 | `ultralytics/nn/modules/temporal.py::TemporalFeatureFusion` | 12 种 mode 全部在这一个类中实现 |
| 训练器 hack | `ultralytics/models/yolov10/train.py` | 时序训练时关闭 W&B、跳过 AutoBackend final 验证（5D 张量不兼容） |
| 训练器 DDP | `ultralytics/engine/trainer.py` | reference no-grad 时启用 `find_unused_parameters=True` |

### 1.2 端到端 pipeline（高层）

```
                          ┌─────────────────────────────────────────────┐
                          │  TemporalYOLODataset (clip 采样)             │
                          │  groups by (parent, sequence prefix)         │
                          │  causal=True → offsets [-T+1 .. 0]           │
                          │  causal=False→ offsets [-T/2 .. T/2]         │
                          │  output: img: [T,C,H,W], label = 中心/最后帧 │
                          └────────────────┬────────────────────────────┘
                                           │
                                  collate → [B,T,C,H,W]
                                           │
                                           ▼
              ┌───────────────────────────────────────────────────────┐
              │ YOLOv10DetectionModel._predict_once                   │
              │  if reference_grad=False:                              │
              │     center stream (with grad)                          │
              │     ref stream    (no_grad, 共享 backbone 权重)         │
              │     至 fuse_layers 处合并 → TemporalFeatureFusion       │
              │     replace_layers 处替换主流 → 后续只跑 center stream  │
              │  else:                                                  │
              │     全部 [B*T,C,H,W] 一起跑，fuse 处把 BT 重 view 成 BT │
              └────────────────────────┬───────────────────────────────┘
                                       │
                                       ▼
                       Backbone (Conv/C2f/SCDown/SPPF/PSA)
                                       │
                                fuse@layer 6 (P4) ──┐ 可选（仅 ms 版本）
                                       │            │
                                fuse@layer 10 (P5) ─┤ 主插入点（所有 dmsa* 都在这）
                                       │            │
                                       ▼            │
                       Neck (FPN+PAN, 引用 layer 6 ◄┘
                                       │  layer 10 的特征做 Concat)
                                       ▼
                       v10Detect head (one-to-one + one-to-many)
                                       ▼
                                 Detections_t
```

关键点：
- **fuse_layers**：在哪几层做时序融合（按 layer index）。
- **replace_layers**：fusion 输出是否真正替换主流。如果只在 `fuse_layers` 列出但不在 `replace_layers`，那么 fused feature 仅被写入 `y[i]` 给 head 的 `Concat` 用（即多尺度记忆），主流仍是单帧特征。
- **target**：`last` 表示中心帧索引 = T-1（causal/online 设定），`center` 表示索引 = T//2（offline 中心采样）。
- **reference_grad=False**：参考帧 backbone 走 `torch.no_grad()`，显存大幅下降；副作用是参考帧仍会触发 BN running stats 更新（潜在隐患，体检章节会提）。

### 1.3 yaml 中 `temporal:` 字段速查

| 字段 | 作用 | 取值范围 |
|---|---|---|
| `frames` | clip 帧数 T，必须为奇数且 ≥3 | 3 / 5 |
| `mode` | 对应 `TemporalFeatureFusion` 的分支 | identity/concat/motion/tmfa/dts/dis/mtgr/dmsa/dmsa_cg/dmsa_mq/dmsa_mq_sim/ocm_dmsa/ocm_dmsa_calib/ma_dmsa_mq |
| `target` | 预测哪一帧 | center（默认）/ last / causal |
| `reference_grad` | 是否给参考帧也算梯度 | True / False |
| `fuse_layers` | 在哪些层插入时序融合 | 例：`[10]`，`[6,10]`，`[4,6,10]` |
| `replace_layers` | 哪些 fuse 层会替换主流 | 通常只 `[10]` |

---

## 2. 12 种时序融合方法的详尽对比与代码体检

> 全部位于 `ultralytics/nn/modules/temporal.py`，按 mode 分支列出。  
> 表头里"$F_t$"表示当前帧（target）特征，"$F_{t-1}, F_{t-2}, F_{t+1}$"等表示邻居帧特征。

### 2.1 逐方法精解

#### (1) `identity` — 数据管线 sanity check
```
output = clip[:, center]
```
- **目的**：只走中心帧、不做任何时序融合，验证 dataloader / forward 是否正确。
- **代码位置**：`temporal.py:246-247`。
- **注意陷阱**：identity 模式下 forward 实际只跑中心帧（`tasks.py:710-712`），参考帧从不进入 backbone，**所以它的显存不能代表真实时序模型的显存**（实验日志关键发现 1 已记录此事）。

#### (2) `concat` — 最朴素 baseline（论文 Version 1）
```
output = Conv1×1( Concat(F_{t-1}, F_t, F_{t+1}) )   # channel: C*T → C
```
- **目的**：证明"多帧输入"本身的基础贡献，避免后续工作被人怀疑"只是看了几帧"。
- **代码位置**：`temporal.py:248-249`。

#### (3) `motion` — 运动差分 baseline（论文 Version 2）
```
output = Conv1×1( Concat(F_t,  F_t - F_{t-1},  F_{t+1} - F_t) )
```
- **目的**：显式把"两个时刻间的运动"作为通道送进 conv，比 concat 更对运动敏感。
- **代码位置**：`temporal.py:250-254`。

#### (4) `tmfa` — Pure Temporal Mamba（论文 Version 3 的最纯版本）
```
seq[B*H*W, T, C]    ← 把每个空间位置展开成时序序列
seq = LayerNorm(seq)
seq = Mamba(seq)    （若 mamba_ssm 不可用则退化为 BiGRU）
output = seq[:, center].view(B,C,H,W)
```
- **目的**：对每个像素位置做一次时间方向的 SSM 扫描，输出中心帧位置的 SSM 隐状态。
- **代码位置**：`temporal.py:127-137, 322-333`。
- **关键差异**：tmfa 是"全通道 Mamba"，没有降维，显存大；DMSA 把它压到 25% 通道再扫描。

#### (5) `dis` — Detection-Informed Selector（早期残差版）
```
motion  = motion_proj([|F_t-F_{t-1}|, |F_{t+1}-F_t|])
weights = softmax(selector([F_{t-1}, F_t, F_{t+1}, motion]))   # 3 个权重
selected = w0·F_{t-1} + w1·F_t + w2·F_{t+1}
quality = sigmoid(quality_conv(F_t))
gate    = sigmoid(gate_conv([F_t, selected, motion])) · quality
output  = F_t + gate · residual([selected - F_t, motion])
```
- **目的**：用 softmax 选择器从三帧加权挑出"最值得信任"的特征，再以残差形式加回当前帧。
- **特点**：不含 Mamba，**显式的多帧选择 + 检测感知 gate + 残差加法**。初始化把 `selector` 的中间通道偏置 +2，等价于初始全选当前帧 → 训练初期接近恒等。
- **代码位置**：`temporal.py:45-60, 165-171, 255-269`。
- **实验结论**：早期 epoch 有收益（best 0.323/0.170 @ epoch 2），但 30 epoch 后掉到 0.247/0.120，**严重退化**。已废弃。

#### (6) `mtgr` — Mamba Temporal Gated Residual（full-channel Mamba）
```
state = Mamba(seq[B*H*W, T, C])[:, center]            # 全通道 Mamba
motion = motion_proj([|F_t-F_{t-1}|, |F_{t+1}-F_t|])
delta  = state - F_t
quality = sigmoid(quality_conv(F_t))
gate    = sigmoid(gate_conv([F_t, delta, motion])) · quality
output  = F_t + α · gate · residual([delta, motion])    # α 初值 1e-3
```
- **目的**：在 dis 基础上把"selected"换成"Mamba 时序状态的 delta"，并引入可学小残差权重 α。
- **代码位置**：`temporal.py:138-154, 173-176, 339-349`。
- **实验结论**：best 0.334/0.180，**比 DIS 稳定且更强**，但 full-channel Mamba 显存接近 24G，工程负担大。

#### (7) `dmsa` — Detection-aware Multi-Scale Aggregation **（Lite-Mamba 主体）**
```
low      = reduce(F)            # 1×1 conv: C → state_C ≈ C/4
seq      = LayerNorm(low.view(B*H*W, T, state_C))
seq      = Mamba(seq)           # 低维 Mamba
state    = expand(seq[:, center].view(B,state_C,H,W))   # 1×1 conv: state_C → C
delta    = state - F_t
motion   = motion_proj(...)     # 同 mtgr
quality  = sigmoid(quality_conv(F_t))
gate     = sigmoid(gate_conv([F_t, delta, motion])) · quality
output   = F_t + α · gate · residual([delta, motion])
```
- **目的**：**核心创新**——把 mtgr 的全通道 Mamba 换成"低维状态 Mamba"，显存/速度大幅下降，仍能接近 mtgr 的精度。
- **代码位置**：`temporal.py:61-125, 178-193, 270-320`。
- **实验结论**：best 0.335/0.181，与 mtgr 持平，显存/速度更可控 → **此后所有 DMSA-* 系列的基础**。

#### (8) `dmsa_cg` — Conservative Gate（消融）
- 在 dmsa 基础上把 `gate_scale=0.5`，并把 gate 的 conv 初始化为 `weight=0, bias=-2`（sigmoid≈0.12），让训练初始几乎不走 residual。
- **目的**：测试"是不是 residual 太强导致后期退化"。
- **实验结论**：best 0.333/0.179，**没有突破 dmsa**，证明退化主因不是 residual 太强。

#### (9) `dmsa_causal` — 把 dmsa 改成 online 设定（**重要里程碑**）
- yaml 改两处：`frames: 3 + target: last`（再配合 CLI `temporal_causal=True`）。
- 输入由 `[t-1, t, t+1]` 变成 `[t-2, t-1, t]`，预测 t。
- 代码层面 `dmsa` 分支会自动走 `if center == frames-1` 的运动差分（用 `[F_t-F_{t-1}, F_{t-1}-F_{t-2}]`）。
- **实验结论**：best 0.338/0.184，**超过 offline dmsa**，且具备"online 视频检测"叙事 → 成为后续主线设定。

#### (10) `dmsa_mq` — DMSA + **Memory Queue / State Token**（**当前最佳**）
关键代码（`temporal.py:282-296`）：
```
history = seq[:, :center]                                # [t-2, t-1] 的低维特征
memory_logits = self.memory_logits[:H]                   # 可学 K 维标量
memory_weights = softmax(memory_logits)                  # 时间维加权
memory = (history * memory_weights).sum(t-axis)           # 1 个 memory token
memory = memory + memory_refine(memory)                   # 残差精修，初始零
seq = cat([history, memory, current], dim=t-axis)        # [t-2, t-1, mem, t]
state = Mamba(seq)[:, last]                              # 取最后位置作为 state
```
- **目的**：在 causal 短序列中显式注入一个"压缩历史"token，让 Mamba 在 t 之前看到一个被加权过的记忆位置。这是项目宣称的"State Token / Memory Queue"创新点，对应 TV3S-style temporal state sharing 思想。
- **`memory_refine` 末层零初始化** → 初始时 `memory = weighted_avg(history)`，随训练学出非零修正。
- **实验结论**：best **0.344/0.187 (seed=0)** —— 全项目最佳。但 seed=1 复现仅 0.291/0.149（见 §3 体检）。

#### (11) `dmsa_mq_sim` — 给 memory queue 加相似度检索（消融）
```
similarity   = cos_sim(history, current_query)          # 每个历史帧与当前帧的相似度
memory_logits = memory_logits + memory_sim_scale · similarity
memory_weights = softmax(memory_logits)
```
- **目的**：让"哪些历史更值得记"由当前帧本身决定，类似 attention retrieval。
- **实验结论**：3f best 0.344/0.187，**与 dmsa_mq 持平**；5f 反而掉到 0.323/0.174 → 5 帧没有收益。

#### (12) `dmsa_mq_ms` — 多尺度 memory queue（消融）
- yaml `fuse_layers: [6, 10]`，即同时在 P4 和 P5 上挂 `dmsa_mq` 模块。
- P4 的 fused 不替换主流，但通过 `Concat [-1, 6]` 进入 head。
- **实验结论**：best 0.323/0.172（batch=12, 6 epoch），**没有超过 P5-only 的 0.344/0.187**。多尺度 dense memory 引入太多背景噪声。

#### (13) `ocm_dmsa` (Lite) — Object-Centric Multiplicative Gate（消融）
```
object_gate = sigmoid(object_gate_conv([F_t, |delta|, motion]))   # bias 初值 = -1
gate = gate · object_gate                                          # 硬乘法
```
- **目的**：让时序残差只作用在"目标可能存在"的位置，类似 hard mask。
- **实验结论**：best 0.335/0.180，**比 dmsa_mq 弱**。日志结论：硬 gate 把有用 residual 也压住了。

#### (14) `ocm_dmsa_calib` — Object-Centric Calibration（消融）
```
object_gate = sigmoid(object_gate_conv([F_t, |delta|, motion]))   # bias 初值 = 0 → ~0.5
gate = gate · (1 + β · (object_gate - 0.5))                         # β 初值 0.1
```
- **目的**：把 object gate 改成温和的乘性校准，初始等价于 dmsa_mq。
- **实验结论**：best 0.343/0.186 → **几乎等于 dmsa_mq**，验证"object gate 不是当前瓶颈"。

#### (15) `ma_dmsa_mq` — Motion-Aligned DMSA-MQ（消融）
```
pair = cat([F_low_neighbor, F_low_current, |F_low_current - F_low_neighbor|])
offset = tanh(align_offset_conv(pair)) · 2.0          # offset_max = 2 像素
F_low_neighbor_warped = grid_sample(F_low_neighbor, base_grid + offset)   # 在低维空间 warp
```
- **目的**：在低维 memory 进入 Mamba 之前先做学习式的"特征对齐"，缓解快速运动导致的跨帧错位。
- **offset 头零初始化** → 初始等价于 dmsa_mq。
- **实验结论**：best 0.341/0.184，**没超过 dmsa_mq 的 0.344/0.187**。低维 alignment 信号不足。

> `dts` 模式存在但当前没有 yaml 在用（`yolov10s-dts.yaml` 列出来了但 log 里不在主线对比中）。它和 mtgr 的差别是用 `objectness` 替代 `quality_conv(F_t)`，输入是 `[F_t, motion]`。可视为 DTS 计划文档（`DTS_YOLOv10_implementation_plan.md`）的早期实现。

### 2.2 一张总表（按时间/创新度排序）

| # | 模式 | 输入 | 是否 Mamba | 关键创新 | best AP50 | best AP50-95 | 状态 |
|---|---|---|---|---|---|---|---|
| 0 | YOLOv10s 单帧 | 1f | – | – | 0.333 | 0.172 | baseline |
| 1 | identity | 3f→1f | 否 | sanity | – | – | 测管线 |
| 2 | concat | 3f | 否 | 多帧 1×1 conv | 未独立测 | – | baseline |
| 3 | motion | 3f | 否 | 显式差分 | 未独立测 | – | baseline |
| 4 | tmfa | 3f | 全通道 | 像素级时序扫描 | 未独立测 | – | 显存重 |
| 5 | dis | 3f | 否 | softmax selector + gate residual | 0.323 | 0.170 | 后期退化、废弃 |
| 6 | mtgr | 3f | 全通道 + α | full-Mamba TGR | 0.334 | 0.180 | 重，已被 dmsa 取代 |
| 7 | **dmsa** | 3f | **低维** + α | Lite-Mamba 残差 | 0.335 | 0.181 | DMSA 主体 |
| 8 | dmsa_cg | 3f | 低维 + α | 保守 gate (gate_scale=0.5) | 0.333 | 0.179 | 消融失败 |
| 9 | **dmsa_causal** | 3f causal | 低维 + α | online 设定 | 0.338 | 0.184 | 升级里程碑 |
| 10 | **dmsa_mq** | 3f causal | 低维 + memory token | **state token / memory queue** | **0.344** | **0.187** | **当前最佳** |
| 11 | dmsa_mq_sim | 3f causal | + cosine retrieval | 相似度检索 | 0.344 | 0.187 | 与 mq 持平 |
| 12 | dmsa_mq_sim 5f | 5f causal | 同上 | 长历史 | 0.323 | 0.174 | 5 帧反而掉 |
| 13 | dmsa_mq_ms | 3f causal | P4+P5 | 多尺度 dense memory | 0.323 | 0.172 | 多尺度噪声 |
| 14 | ocm_dmsa (Lite) | 3f causal | + 硬 object gate | 目标中心 hard mask | 0.335 | 0.180 | 抑制太强 |
| 15 | ocm_dmsa_calib | 3f causal | + 温和 object 校准 | residual 校准 | 0.343 | 0.186 | 与 mq 持平 |
| 16 | ma_dmsa_mq | 3f causal | + 低维 grid_sample warp | learn-to-align memory | 0.341 | 0.184 | 信号不足 |

### 2.3 各方法的"关系树"（创新演进图）

```
单帧 YOLOv10-S baseline
        │
        ▼
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│  identity (sanity)  │    │  concat (Version 1) │    │  motion (Version 2) │
└─────────┬───────────┘    └────────┬────────────┘    └────────┬────────────┘
          │                          │                          │
          ▼                          ▼                          ▼
                  tmfa  ─────►  pure full-channel Mamba (Version 3)
                                          │
                  dis   ─────►  selector + residual  ──── 后期退化，废弃
                                          │
                  mtgr  ─────►  full Mamba + α·gate·residual (DTS 雏形)
                                          │ 降维替换 Mamba
                                          ▼
                                     【dmsa】 Lite-Mamba 主体  ← Pareto 起点
                                          │
                  ┌────────────────┬──────┴──────────┬────────────────┐
                  ▼                ▼                 ▼                ▼
             dmsa_cg         dmsa_causal         dmsa_mq          ma_dmsa_mq
         (保守 gate)         (online 设定)   (memory queue) ★    (motion align)
                                  │                 │                 │
                                  └─→ 配合 ──────►───┴────────────────┘
                                                    │
                                          ┌─────────┴───────────┐
                                          ▼                     ▼
                                     dmsa_mq_sim           dmsa_mq_ms
                                  (相似度检索)            (P4+P5 多尺度)
                                          │
                              ┌───────────┴───────────┐
                              ▼                       ▼
                    ocm_dmsa (硬 object gate)    ocm_dmsa_calib (温和校准)
```

---

## 3. 代码体检报告（创新点是否真正实现 + 隐患）

### 3.1 ✅ 已真正实现且与论文计划一致的项

| 计划/创新点 | 实现位置 | 体检结论 |
|---|---|---|
| 多帧 dataloader | `dataset.py:228-292` | ✅ 序列分组、stride、causal 三个开关都到位；中心帧 label 沿用单帧 label |
| Reference no-grad（参考帧 backbone 不算梯度） | `tasks.py:744-792` | ✅ 已实现，DDP 配套 `find_unused_parameters=True`（`trainer.py`） |
| Lite-Mamba（DMSA 降维 → Mamba → 升维） | `temporal.py:71,94,100` | ✅ `state_channels = max(16, C//4)`；GRU 兜底 |
| Memory Queue / State Token | `temporal.py:282-296` | ✅ history+memory+current 三段拼接，refine 零初始化 |
| Similarity Memory Retrieval | `temporal.py:288-290` | ✅ cos-sim + 可学温度 |
| Causal/Online 设定 | yaml `target: last` + dataset `temporal_causal=True` | ✅ offsets `[-T+1..0]`；运动差分自动切换为 `[F_t-F_{t-1}, F_{t-1}-F_{t-2}]` |
| α 残差 + gate（防初始化破坏） | `temporal.py:124, 178-193` | ✅ α 初值 1e-3；residual 末层 1e-3 init；gate bias 控制初始活跃度 |
| Object-centric gate（OCM 系列） | `temporal.py:114-123, 313-318` | ✅ Lite 版 hard 乘法 + Calib 版温和校准两版 |
| 学习式 motion align（MA-DMSA） | `temporal.py:73-81, 209-242` | ✅ 低维 grid_sample warp，offset 头零初始化 |
| 多尺度插入 | yaml `fuse_layers: [6,10]` | ✅ 已实现（P4 fused → save → head Concat） |

### 3.2 ⚠️ 偏离计划 / 没真正实现 / 实现脆弱的项

| 问题 | 位置 | 体检结论 |
|---|---|---|
| **训练增强被强制关闭** | `build.py:93` `augment=mode=='train' and temporal_frames==1` | 时序训练时所有 train-time augmentation（mosaic/mixup/affine/hsv 等）都被关掉，泛化降低；这是导致"epoch 3-5 早峰、之后下降"的高度嫌疑因子之一 |
| **Reference no-grad 仍触发 BN running stats 更新** | 走 `m(ref_in)` 的 `with torch.no_grad():` 块（`tasks.py:768-769`） | `no_grad` 不阻止 BN running stats 更新；参考帧每步会"二次更新"BN 统计，可能让 BN 漂移、训练不稳。建议把 backbone BN 切到 eval 模式或用 `frozen_bn` |
| **Seed 复现失败** | 实验 `dmsa_mq seed=1` best 仅 0.291/0.149（`TEMPORAL_EXPERIMENT_LOG.md:217-243`） | 同一配方在 seed=1 下显著掉点 → 当前 +0.011/+0.015 收益**不可靠**。论文要求至少 2-3 seed 平均 |
| **冻结 backbone 的两阶段训练计划没有执行** | 计划文档明确建议 5-10 epoch frozen → 解冻 fine-tune | 实际所有实验都是直接 full fine-tune `lr0=0.0003`；"DIS freeze11" 是 freeze=11 而不是分阶段 |
| **同一类输入下方法对比不公平** | dmsa.yaml 默认 `target: center`（offline），causal 版换成 `target: last` | 比较 0.335 vs 0.338 时分别在 offline / online 设定下，不是严格 same-base；应在同一帧设定下比较 |
| **数据增强里 Mosaic 等会破坏多帧一致性** | 所以 `augment=False` | 但代价是关掉所有增强而不是只关 Mosaic/MixUp。可以通过自定义 transform 只保留同步增强（resize/flip/jitter）来恢复一部分 |
| **multi-scale 的 P3 没插入** | yaml `fuse_layers` 最深只到 [6, 10]，没有触达 layer 4 (P3) | 论文计划里 small object 收益主要靠 P3，但目前所有 dmsa 主线都是 P5（甚至 P4+P5），未验证 P3 的贡献 |
| **5f 显存崩溃只在日志里口头提及** | `dmsa_mq_sim 5f` batch=18 反向崩溃 | 没看到 grad-checkpoint / mixed-precision 的解决路径 |
| **`dts` 分支挂着但没参与对比** | `temporal.py:155-163` + `yolov10s-dts.yaml` | 早期 DTS 实现保留但未参加论文表，应明确清理或补实验 |
| **AutoBackend final validation 被绕过** | `models/yolov10/train.py:21-26` | 出于 5D 张量不兼容；意味着上报的 best mAP 来自训练中验证而非"最终独立 val"；汇报时需说明 |

### 3.3 🔬 推荐立刻补的两个最小验证

1. **Seed 鲁棒性**：在 seed=0/1/2 下重跑 dmsa_mq baseline，平均后再宣称"+0.011/+0.015"。若标准差 ≥ 0.005，应换稳定化策略（EMA/distillation/multi-seed）。
2. **BN 行为**：把 `_predict_once_temporal_reference_guided` 中参考帧分支临时切到 `m.eval()` 模式，看 best 是否上移。若上移则确认 BN running stats 是退化主因。

---

## 4. 可直接放进汇报的流程架构图

> 下面 4 张 ASCII 图建议直接转成 mermaid / draw.io 出图。

### 4.1 图 A：单帧 baseline vs 时序总览

```
 [单帧 YOLOv10-S baseline]                  [本项目 时序变体]
 ─────────────────────────                  ──────────────────────────────────
  Image_t                                    [Image_{t-2}, Image_{t-1}, Image_t]
    │                                          │ (TemporalYOLODataset, causal)
    ▼                                          ▼
  Backbone                                   Shared Backbone (ref no-grad)
    │                                          │
    ▼                                          ▼  在 layer 10 (P5) 处
  Neck (PAN/FPN)                             ┌──── TemporalFeatureFusion ────┐
    │                                          │     (mode = dmsa_mq …)       │
    ▼                                          └────────────┬─────────────────┘
  v10Detect                                                 ▼
    │                                                  Fused F_t^P5
    ▼                                                       │
  Detections_t                                            Neck
                                                            │
                                                            ▼
                                                        v10Detect
                                                            │
                                                            ▼
                                                       Detections_t
```

### 4.2 图 B：DMSA-MQ causal 模块内部（论文主图）

```
                        clip[B,T,C,H,W]          T=3, target=last
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
              F_{t-2}       F_{t-1}        F_t  ←— current (with grad)
                │             │             │
   reduce 1×1 (C → C/4)  ────┴──┬──────────┘
                                ▼
                          [B,T,C/4,H,W] low-dim clip
                                │
                       LayerNorm + view → seq[B*HW, T, C/4]
                                │
                history = seq[:, :T-1]
                current = seq[:, T-1:T]
                                │
              ┌──── memory_logits (T-1 个可学标量) ─────┐
              │                                         │
              ▼                                         ▼
     (可选) + memory_sim_scale·cos(hist, curr)   (dmsa_mq_sim 才有)
              │                                         │
              ▼                                         │
        softmax → memory_weights ─────────────►  Σ_t (history · w_t)
                                                        │
                                            memory_refine (零初始化)
                                                        │
                                                        ▼
                                                 1 个 memory token
                                                        │
        seq' = concat([history, memory, current])  ►   shape [B*HW, T+1, C/4]
                                │
                              Mamba (state_channels)
                                │
                         state = seq'[:, last]  → view(B,C/4,H,W)
                                │
                         expand 1×1 (C/4 → C)
                                │
                              state_t (即 \tilde{F}_t 的 SSM 估计)
                                │
              ┌─────────────────┴─────────────────┐
              ▼                                   ▼
       motion = motion_proj(|F_t-F_{t-1}|, |F_{t-1}-F_{t-2}|)
       delta  = state_t - F_t
              │
              ▼
       quality = sigmoid(quality(F_t))
       gate    = sigmoid(gate([F_t, delta, motion])) · quality · gate_scale
              │
              ▼
       residual = residual_block([delta, motion])
              │
              ▼
       Output = F_t  +  α · gate · residual           # α 初值 1e-3
                       └─── 残差贡献小 ↔ 训练初期接近恒等
```

### 4.3 图 C：四类时序融合 mode 的对比一图

```
 ┌────────────────┐    ┌────────────────┐    ┌────────────────┐    ┌──────────────────────┐
 │   concat       │    │    motion       │    │  tmfa / mtgr   │    │  dmsa* (Lite-Mamba)   │
 │ Concat 三帧     │    │ Concat 当前 +    │    │ 全通道 Mamba    │    │ reduce → 低维 Mamba   │
 │ 1×1 Conv       │    │ 当前-prev,        │    │ + α·gate·       │    │ → expand →            │
 │                │    │ next-当前         │    │ residual        │    │ α·gate·residual       │
 │ 不带 Mamba      │    │ 不带 Mamba        │    │ 显存重           │    │ 含 memory token (mq) │
 └────────────────┘    └────────────────┘    └────────────────┘    └──────────────────────┘
       baseline           baseline                  Version 3                 主线
```

### 4.4 图 D：Reference no-grad 双流前向

```
              clip [B, T, C, H, W]    target = last (T-1)
                       │
        ┌──────────────┴───────────────┐
        ▼                              ▼
   center_x = clip[:, T-1]       ref_x = clip[:, [0..T-2]] reshape(B*(T-1),C,H,W)
   (with grad)                    (with no_grad)
        │                              │
        ▼                              ▼
    layer 0 (Conv) ──共享权重──► layer 0 (Conv)
        │                              │
        ▼                              ▼
    layer 1 (Conv) ──共享权重──► layer 1 (Conv)
        │                              │           （直至 fuse_layers 之前都两路并行）
        ▼                              ▼
    ...                              ...
        │                              │
        ▼                              ▼
    layer 10 (PSA)                layer 10 (PSA)
        │                              │
        └──────────► merge_clip ◄──────┘
                       │
                  TemporalFeatureFusion( fused_clip [B*T,C,H,W] )
                       │
                ┌──────┴──────┐
                ▼             ▼
       (replace_layers 命中:      (replace_layers 未命中:
        center_x = fused           只把 fused 写入 y[i] 给 head Concat 用)
        refs_active = False)
                       │
                       ▼
              Neck + v10Detect → Loss (只对 center 帧反传)
```

---

## 5. 给汇报和后续学习的建议清单

### 5.1 汇报时可以这样讲

1. **故事线**：从单帧 YOLOv10-S baseline 出发，按 concat / motion / dis / mtgr / dmsa / dmsa_causal / dmsa_mq 七步演进，每一步都解决前一步的具体痛点（多帧 → 显式运动 → 检测感知 gate → 全通道 Mamba → 降维 Mamba → online → memory token），最后形成 DMSA-MQ causal 这一闭环。
2. **三个核心创新**对应 DTS 计划文档：
   - **Detection-aware Temporal State Sharing**：α·gate·residual，把时序贡献限定在"检测有把握的位置"。
   - **Motion-guided Selective State Update**：用 `|F_t - F_{t-1}|, |F_{t-1} - F_{t-2}|` 作 motion proxy 喂 gate。
   - **Memory Queue / State Token**：在 Mamba 序列里塞一个对 history 加权得到的"压缩历史 token"。
3. **公平对比要点**：所有变体共享同一份 backbone+neck+head+dataset，只换 fusion 模块；固定 imgsz=960、batch=24、lr0=0.0003、12 epoch。
4. **当前结论 + 风险要诚实地讲**：
   - "在 seed=0 下 DMSA-MQ causal 比单帧 baseline 提升 +0.011 mAP50 / +0.015 mAP50-95"。
   - "在 seed=1 下复现失败，需要稳定化策略（EMA / distillation / multi-seed average）"。
   - "5 帧 / P4+P5 dense memory / 硬 object gate / 学习式 motion align 四个方向已确认无收益，需要换思路"。

### 5.2 后续要学习的代码点（按优先级）

| 优先级 | 学什么 | 入口 |
|---|---|---|
| P0 | TemporalFeatureFusion 全部 mode forward 的张量形状 | `temporal.py:244-355` |
| P0 | reference-guided forward 的双流合并 | `tasks.py:744-792` |
| P0 | Mamba 块本身的 d_state / d_conv / expand 含义 | mamba_ssm 官方文档 |
| P1 | TemporalYOLODataset 的 sequence 分组规则 | `dataset.py:240-260` |
| P1 | yaml 中 `fuse_layers` 是怎么从 layer index 映射到 channel | `tasks.py:669-691` |
| P2 | DDP unused_parameters 的逻辑 | `trainer.py` |
| P2 | 为什么 final AutoBackend val 会失败 | `models/yolov10/train.py:21-26` |

### 5.3 推荐的下一步实验方向（基于体检的硬建议）

1. **稳定性优先**：dmsa_mq seed=0/1/2 三次平均，并在 baseline seed=1 上确认是否同样掉点（隔离训练敏感 vs 时序模块敏感）。
2. **修复 BN**：把 ref 分支 backbone 切到 eval 或加 `frozen_bn`，看 epoch 5 之后退化是否缓解。
3. **恢复部分增强**：手写一个仅含 resize / hflip / hsv 的同步多帧增强，覆盖 `augment=False` 的硬开关。
4. **P3 插入**：在 `fuse_layers: [4, 10]`（P3+P5）做对比，验证 small object 收益（VisDrone 主要痛点）。
5. **Distillation**：以 dmsa baseline 为 teacher 对 dmsa_mq 做 feature distillation，缓解 memory queue 后期波动。

---

## 6. 文件清单（本次梳理覆盖到的）

```
yolov10-temporal/
├── temporal_yolo_research_plan.md            ← 顶层路线（baseline + 5 阶段实验）
├── DTS_YOLOv10_implementation_plan.md        ← DTS 创新设计（detection-aware gate / state sharing）
├── TEMPORAL_EXPERIMENT_LOG.md                ← 实验日志（按时间记录）
├── PROJECT_AUDIT_AND_METHOD_GUIDE.md         ← 本文（体检 + 方法梳理）
├── ultralytics/
│   ├── nn/
│   │   ├── modules/temporal.py               ← 12 种 mode 全部在此
│   │   └── tasks.py (YOLOv10DetectionModel)  ← reference-guided 双流 forward
│   ├── data/
│   │   ├── dataset.py (TemporalYOLODataset)  ← clip 采样 / sequence 分组
│   │   └── build.py                          ← temporal_frames>1 时切换 dataset
│   ├── models/yolov10/train.py               ← 训练器 hack（W&B / final val skip）
│   ├── engine/trainer.py                     ← DDP find_unused_parameters
│   └── cfg/
│       ├── default.yaml                      ← CLI 暴露 temporal_frames/stride/causal
│       └── models/v10/
│           ├── yolov10s.yaml                 ← 单帧 baseline
│           ├── yolov10s-temporal-identity.yaml      [identity]
│           ├── yolov10s-temporal-concat.yaml        [concat]
│           ├── yolov10s-temporal-motion.yaml        [motion]
│           ├── yolov10s-tmfa.yaml                   [tmfa]
│           ├── yolov10s-dis.yaml                    [dis]
│           ├── yolov10s-dts.yaml                    [dts] (闲置)
│           ├── yolov10s-mtgr.yaml                   [mtgr]
│           ├── yolov10s-dmsa.yaml                   [dmsa] offline
│           ├── yolov10s-dmsa-cg.yaml                [dmsa_cg]
│           ├── yolov10s-dmsa-causal.yaml            [dmsa] causal ← 主线一
│           ├── yolov10s-dmsa-mq-causal.yaml         [dmsa_mq] ★ 当前最佳
│           ├── yolov10s-dmsa-mq-sim-causal.yaml     [dmsa_mq_sim]
│           ├── yolov10s-dmsa-mq-sim-causal-5f.yaml  [dmsa_mq_sim 5f]
│           ├── yolov10s-dmsa-mq-ms-causal.yaml      [dmsa_mq P4+P5]
│           ├── yolov10s-ocm-dmsa-lite-causal.yaml   [ocm_dmsa hard mask]
│           ├── yolov10s-ocm-dmsa-calib-causal.yaml  [ocm_dmsa_calib]
│           └── yolov10s-ma-dmsa-mq-causal.yaml      [ma_dmsa_mq]
```

---

> **最后一句**：本项目的代码层面创新（reference no-grad / Lite-Mamba / memory queue / object gate / motion align）**全部已真正实现且与计划文档一致**；当前真正的瓶颈不在"模块本身"，而在**训练稳定性**（seed 敏感、BN running stats、增强被全关、early peak then drop）。汇报时把这点诚实写出来，反而更有学术可信度。
