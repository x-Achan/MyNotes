# UC-Mamba-ST-Pool2 整体架构报告

> 生成日期：2026-06-17  
> 对应配置：`yolov10-temporal/ultralytics/cfg/models/v10/yolov10s-uc-mamba-st-pool2-causal.yaml`  
> 关键实现：`yolov10-temporal/ultralytics/nn/modules/temporal.py`、`yolov10-temporal/ultralytics/nn/tasks.py`  
> 任务场景：YOLOv10s 短视频/多帧目标检测，使用 3 帧因果时序融合，输出当前帧/最后一帧检测结果。

---

## 1. 一句话概括

**UC-Mamba-ST-Pool2** 是在 YOLOv10s 检测框架中插入的一个轻量时序状态空间融合模块：它以 3 帧短 clip 为输入，先让当前帧和参考帧共享 YOLOv10 backbone 提取特征，然后只在高层语义特征层 `layer 10 / PSA / P5` 处进行时空融合；融合时先将低维特征做 `2×2` 平均池化降采样，再把“时间 × 空间” token 串接成序列送入 Mamba/GRU 建模，最后通过不确定性门控和运动残差把时序增量注入当前帧特征，供 YOLOv10 neck/head 完成检测。

---

## 2. 配置层面的整体框架

### 2.1 temporal 配置

配置文件中核心时序开关如下：

```yaml
temporal:
  frames: 3
  mode: uc_mamba_st_pool2
  target: last
  reference_grad: False
  fuse_layers: [10]
  replace_layers: [10]
```

含义如下：

| 字段 | 含义 |
|---|---|
| `frames: 3` | 输入为 3 帧短序列。 |
| `mode: uc_mamba_st_pool2` | 使用 UC-Mamba 的 ST-Pool2 分支。 |
| `target: last` | 目标帧为最后一帧，即因果检测：只利用历史帧辅助当前帧。 |
| `reference_grad: False` | 参考帧分支不反传梯度，并冻结其 BN running stats 更新，降低训练开销和统计污染。 |
| `fuse_layers: [10]` | 在模型第 10 层做时序融合。 |
| `replace_layers: [10]` | 融合后的特征替换第 10 层输出，继续进入后续检测头。 |

### 2.2 YOLOv10s 主干与融合位置

该配置保持 YOLOv10s 的标准 backbone + FPN/PAN head 结构，时序模块只插入在 backbone 末端的高层语义层：

```text
输入 3 帧 clip
  │
  ├─ 历史参考帧: t-2, t-1  ── YOLOv10 backbone, no_grad, BN stats frozen
  │
  └─ 当前目标帧: t        ── YOLOv10 backbone, normal grad
                                  │
                                  ▼
Layer 10: PSA / P5 高层语义特征
                                  │
                                  ▼
UC-Mamba-ST-Pool2 temporal fusion
                                  │
                                  ▼
替换 layer 10 输出
                                  │
                                  ▼
YOLOv10 neck/head: Upsample + Concat + C2f/C2fCIB
                                  │
                                  ▼
v10Detect 多尺度检测输出
```

从 YAML 结构看，`layer 10` 是 backbone 末端 `PSA` 层，位于 `SPPF` 之后；它的输出随后被 head 上采样，并与中层特征 `layer 6`、`layer 4` 做多尺度融合。因此，UC-Mamba-ST-Pool2 虽然只直接作用于 P5/32 高层特征，但它会通过后续 FPN/PAN 路径向 P4/P3 检测分支传播时序语义。

---

## 3. 推理/训练时的数据流

### 3.1 输入形态

模型支持两类 temporal 输入：

```text
[B, T, C, H, W]
```

或把 3 帧拼在通道维的：

```text
[B, T*C, H, W]
```

当 `T=3` 时，`target: last` 使目标帧索引为 `2`，即：

```text
frame 0 = t-2, 历史参考帧
frame 1 = t-1, 历史参考帧
frame 2 = t,   当前检测帧 / target frame
```

### 3.2 Reference-guided 前向机制

由于 `reference_grad: False`，实际前向不是简单地把 `B*T` 帧全部同等送入网络，而是采用 **reference-guided** 机制：

1. 当前帧 `t` 正常前向，参与梯度更新。
2. 历史参考帧 `t-2, t-1` 在 `torch.no_grad()` 下前向。
3. 参考帧通过 backbone 时临时冻结 BatchNorm running statistics，避免参考帧扰动 BN 统计。
4. 到达 `fuse_layers=[10]` 后，将当前帧特征和参考帧特征重新拼成 `[B*T, C, H, W]`，送入 `TemporalFeatureFusion`。
5. 融合输出替换当前帧的第 10 层特征；替换后参考帧分支停止继续计算，只保留当前帧进入后续 head。

这种设计的优点是：**参考帧只服务于时序融合，不完整参与检测头计算**，因此比全 3 帧完整反传更省显存、更稳定。

---

## 4. UC-Mamba-ST-Pool2 模块内部结构

### 4.1 模块入口

`TemporalFeatureFusion` 接收第 10 层特征，先恢复为 clip 形式：

```text
输入:  x = [B*T, C, H, W]
恢复: clip = [B, T, C, H, W]
取目标帧: center = clip[:, target_index]
```

对于本配置：

```text
T = 3
center = clip[:, 2]  # 最后一帧 / 当前帧
```

### 4.2 通道压缩：降低 Mamba 建模成本

模块不会直接在原始通道 `C` 上做 Mamba，而是先用 `1×1 Conv` 将通道压缩到状态通道：

```text
state_channels = max(16, int(C × 0.25))
low = Conv1×1(center/ref features): C → state_channels
low_clip = [B, T, state_channels, H, W]
```

作用：

- 降低 Mamba/GRU 的 token 维度；
- 保留高层语义的主要状态信息；
- 让时序模块更轻量，适合插在 YOLOv10s 中。

### 4.3 ST-Pool2：空间池化后做时空序列建模

ST-Pool2 的核心在 `_uc_st_pool2_delta()`：

```text
low_clip: [B, T, Cs, H, W]
  │
  ├─ AvgPool2d(kernel=2, stride=2, ceil_mode=True)
  │     ↓
  │   pooled: [B, T, Cs, Hp, Wp]
  │
  ├─ 不确定性调制历史帧
  │
  ├─ flatten 为时空 token 序列
  │     pooled.permute(...).reshape(B, T×Hp×Wp, Cs)
  │
  ├─ LayerNorm
  │
  ├─ Mamba(d_model=Cs, d_state=16, d_conv=3, expand=2)
  │   若 `mamba_ssm` 不可用，则 fallback 到双向 GRU + Linear projection
  │
  ├─ 取目标帧 token slice
  │     state_tokens = seq[:, center×Hp×Wp : (center+1)×Hp×Wp]
  │
  ├─ reshape 回特征图: [B, Cs, Hp, Wp]
  │
  ├─ 1×1 Conv expand: Cs → C
  │
  ├─ Bilinear interpolate: [Hp, Wp] → [H, W]
  │
  └─ temporal_delta = state - center
```

其中 `Pool2` 的意义是：在送入 Mamba 前把空间分辨率约降为一半，使序列长度从 `T×H×W` 降为约 `T×H/2×W/2`，显著降低状态空间建模开销。

如果输入图像为 `960×960`，第 10 层约为 `30×30` 的 P5 特征，则：

```text
未池化序列长度 ≈ 3 × 30 × 30 = 2700 tokens
Pool2 后长度 ≈ 3 × 15 × 15 = 675 tokens
```

这就是 ST-Pool2 的主要工程动机：**保留时空全局建模，但用池化控制 token 数量**。

---

## 5. 不确定性感知机制

UC-Mamba 中的 `UC` 可以理解为 uncertainty-conditioned / uncertainty-calibrated 的时序注入策略。该模块包含两级不确定性：

### 5.1 前置不确定性：调制历史帧输入

前置不确定性图来自低维特征：

```text
current_low = 当前帧低维特征
prev_low    = 前一帧低维特征
prev2_low   = 前两帧低维特征

low_disagreement = |current_low - prev_low|
low_motion       = mean(|current_low - prev_low|, |prev_low - prev2_low|)

pre_uncertainty = sigmoid(Conv([current_low, low_disagreement, low_motion]))
```

然后对历史帧做增益调制：

```text
history_gain = 1 + tanh(uc_gamma) × pre_uncertainty
```

注意：`uc_gamma` 初始化为 `0`，因此训练初期：

```text
tanh(uc_gamma) = 0
history_gain = 1
```

也就是说，模块初始时不会强行放大历史帧，而是在训练中逐步学习“哪些不确定区域更需要历史信息”。

### 5.2 后置不确定性：调制残差注入强度

Mamba/GRU 得到时序状态后，会计算：

```text
temporal_delta = state - center
```

再根据当前帧、时序差异和运动强度生成后置不确定性：

```text
motion_lite = 0.5 × (mean(|center-prev|) + mean(|prev-prev2|))
post_uncertainty = sigmoid(Conv([center, |temporal_delta|, motion_lite]))
```

最终输出不是直接替换当前特征，而是保守残差注入：

```text
residual = Conv([temporal_delta, motion_lite])
output = center + alpha × (0.75 + 0.5 × post_uncertainty) × residual
```

其中：

- `alpha` 默认初始化为 `1e-3`；
- `uc_residual` 最后一层以很小方差初始化；
- 整个模块训练初期接近 identity mapping。

这种设计能避免时序融合在早期破坏单帧检测能力，适合从已有 YOLOv10s 权重继续训练。

---

## 6. 与 UC-Mamba-Lite / ST-TopK 的区别

| 变体 | 核心思路 | 优点 | 代价/风险 |
|---|---|---|---|
| UC-Mamba-Lite | 不做 Pool2/TopK，按每个空间位置沿时间建模或常规低维序列建模 | 结构简单，稳定 | 对空间-时间联合交互较弱 |
| **UC-Mamba-ST-Pool2** | 先 `2×2` 平均池化，再把 `T×Hp×Wp` 作为完整时空序列送入 Mamba | 全局时空建模，token 数比全分辨率低 | 池化可能削弱极小目标局部细节 |
| UC-Mamba-ST-TopK | 根据前置不确定性选 Top-K 空间位置，只对高不确定区域做时空建模 | 更聚焦疑难区域，实验最优 | Top-K 路由更复杂，对 K 值敏感 |

实验摘要中 ST-Pool2 的结果为 `mAP50=0.352 / mAP50-95=0.190`，与 Lite+stride2 接近，略低于 ST-TopK；说明统一池化虽然降低成本，但对 VisDrone 这类小目标场景可能会损失部分空间细节。

> 注意：自 DMSA-MQ + GroupFix + BNFix 之后，后续 UC-Mamba / UTR-DMSA / SyncAug 等实验默认已经处在 GFBF 基线之上。因此解读 ST-Pool2 的收益时，不应把 GFBF 的额外收益重复计入 UC-Mamba-ST-Pool2。

---

## 7. 论文/汇报表述建议

可以将 UC-Mamba-ST-Pool2 描述为：

> 为了在 YOLOv10s 中高效利用短时历史帧，我们在 backbone 顶层语义特征处引入 UC-Mamba-ST-Pool2。该模块首先将 3 帧 P5 特征压缩到低维状态空间，并通过 2×2 平均池化降低空间 token 数；随后把时间和空间维度展平成统一序列，使用 Mamba 状态空间模型进行长程时空依赖传播。为避免历史帧噪声破坏当前帧检测，我们设计了前置不确定性调制和后置不确定性残差注入，使模型仅在运动差异或预测不确定区域自适应增强历史信息。最终，融合后的当前帧 P5 特征替换原 YOLOv10s 第 10 层输出，并通过检测头的多尺度路径传递到最终预测。

---

## 8. 方法图生成提示词

下面提示词适合用于 GPT-4o / Claude Artifacts / draw.io AI / Mermaid 生成器 / PPT 图形助手。建议生成 **横向流程图**，用于论文方法总览或组会报告。

### 8.1 中文提示词：整体方法图

```text
请根据以下代码框架生成一张论文风格的深度学习方法总览图，横向布局，简洁、清晰、适合目标检测论文。

方法名称：UC-Mamba-ST-Pool2 for YOLOv10 Temporal Object Detection。

图中从左到右展示：
1. 输入为 3 帧短视频 clip：[I_{t-2}, I_{t-1}, I_t]，其中 I_t 是当前检测帧，target=last，因果时序设置。
2. 三帧进入共享的 YOLOv10s Backbone。历史参考帧 I_{t-2}, I_{t-1} 标注为 no_grad / BN frozen；当前帧 I_t 标注为 gradient path。
3. Backbone 层级依次简化为 Conv/C2f/SCDown/C2fCIB/SPPF/PSA。突出显示 layer 10 = PSA / P5 feature。
4. 在 layer 10 处把 3 帧 P5 特征送入 UC-Mamba-ST-Pool2 Temporal Fusion 模块。
5. UC-Mamba-ST-Pool2 输出 fused P5 feature，并替换原 layer 10 当前帧特征。
6. 融合特征进入 YOLOv10 neck/head：Upsample、Concat with layer6 P4、Concat with layer4 P3、C2f/C2fCIB。
7. 最后进入 v10Detect，输出当前帧 I_t 的多尺度检测结果 boxes/classes。

视觉要求：
- 使用蓝色表示 YOLOv10 backbone/head，橙色表示 UC-Mamba-ST-Pool2，灰色虚线表示历史参考帧 no_grad 分支，绿色实线表示当前帧梯度分支。
- 在 UC-Mamba-ST-Pool2 模块旁标注关键词：3-frame causal fusion, P5/32, ST sequence modeling, uncertainty-conditioned residual injection。
- 图中不要放太多公式，只保留关键张量形状：[B,3,C,H,W]、[B,3,C5,H/32,W/32]、[B,C5,H/32,W/32]。
- 输出为矢量图风格，白色背景，适合放入论文或答辩 PPT。
```

### 8.2 English prompt: overall method figure

```text
Create a clean paper-style architecture diagram for “UC-Mamba-ST-Pool2 for YOLOv10 Temporal Object Detection”. Use a left-to-right layout.

Show a 3-frame causal input clip [I_{t-2}, I_{t-1}, I_t], where I_t is the target frame. The three frames are processed by a shared YOLOv10s backbone. Mark the two historical reference frames as “no_grad + BN frozen” with gray dashed paths, and mark the current frame as the gradient path with a green solid path.

Simplify the backbone as Conv / C2f / SCDown / C2fCIB / SPPF / PSA, and highlight layer 10, i.e., the PSA P5 feature. At layer 10, merge the three P5 features and feed them into an orange module named “UC-Mamba-ST-Pool2 Temporal Fusion”. The fusion module outputs a fused current-frame P5 feature, which replaces the original layer-10 feature.

Then show the YOLOv10 neck/head: upsample, concatenate with P4 from layer 6, concatenate with P3 from layer 4, C2f/C2fCIB refinement, and v10Detect. The final output is current-frame detection boxes and classes.

Use blue for the YOLOv10 backbone/head, orange for UC-Mamba-ST-Pool2, gray dashed lines for reference-frame no-gradient branches, and green solid lines for the current-frame branch. Add small tensor shape labels: [B,3,C,H,W], [B,3,C5,H/32,W/32], and [B,C5,H/32,W/32]. Keep the figure minimal, vector-graphic style, white background, suitable for a research paper or presentation slide.
```

---

## 9. UC-Mamba-ST-Pool2 模块框架图提示词

这一张图建议作为 **模块细节图**，重点画 temporal fusion 内部。

### 9.1 中文提示词：模块内部框架图

```text
请生成一张 UC-Mamba-ST-Pool2 模块内部结构图，论文风格，横向或上下结合布局，突出“低维压缩 → Pool2 时空序列建模 → 不确定性残差注入”的流程。

输入：来自 YOLOv10 layer 10 的三帧 P5 特征 F_{t-2}, F_{t-1}, F_t，形状为 [B,3,C,H,W]，目标是输出融合后的当前帧特征 F'_t，形状 [B,C,H,W]。

模块步骤：
1. Clip reshape：把 [B*T,C,H,W] 恢复为 [B,T,C,H,W]，取当前帧 center=F_t。
2. Channel reduction：使用 1×1 Conv 将通道 C 压缩到 Cs=max(16,0.25C)，得到 low_clip [B,T,Cs,H,W]。
3. Pre-uncertainty branch：
   - 计算 |F_t^low - F_{t-1}^low| 和轻量 motion map；
   - 经过小型 Conv-BN-SiLU-Conv + sigmoid 得到 pre uncertainty map；
   - 用 1 + tanh(gamma) * uncertainty 调制历史帧，当前帧不调制。
4. ST-Pool2 branch：
   - 对 low_clip 做 AvgPool2d(kernel=2,stride=2)，得到 [B,T,Cs,H/2,W/2]；
   - flatten 为时空序列 [B,T×H/2×W/2,Cs]；
   - LayerNorm；
   - Mamba SSM，如果不可用则 BiGRU fallback；
   - 取当前帧 token slice，reshape 回 [B,Cs,H/2,W/2]；
   - 1×1 Conv expand 到 C 通道，并双线性上采样回 [H,W]；
   - 得到 temporal_delta = state - center。
5. Post-uncertainty residual injection：
   - 根据 center、|temporal_delta|、motion_lite 生成 post uncertainty map；
   - residual = Conv([temporal_delta, motion_lite])；
   - 输出 F'_t = F_t + alpha * (0.75 + 0.5 * post_uncertainty) * residual。

视觉要求：
- 主路径用橙色，Mamba/SSM 模块用紫色，不确定性分支用红色或黄色，残差连接用绿色。
- 标注关键设计：Pool2 reduces token length, spatio-temporal sequence, uncertainty-conditioned history modulation, conservative residual injection, alpha initialized to 1e-3, gamma initialized to 0。
- 图中显示关键公式，但保持简洁。
- 白色背景，模块边框清晰，适合论文方法图。
```

### 9.2 English prompt: UC-Mamba-ST-Pool2 module figure

```text
Draw a detailed module diagram for “UC-Mamba-ST-Pool2 Temporal Fusion”. Use a clean research-paper style.

Input: three P5 features from YOLOv10 layer 10, F_{t-2}, F_{t-1}, F_t, with shape [B,3,C,H,W]. The output is a fused current-frame feature F'_t with shape [B,C,H,W].

Show the following pipeline:
1. Reshape [B*T,C,H,W] into [B,T,C,H,W], and select the current target feature center = F_t.
2. Channel reduction: a 1×1 convolution maps C to Cs=max(16,0.25C), producing low_clip [B,T,Cs,H,W].
3. Pre-uncertainty branch: compute low-level disagreement |F_t^low - F_{t-1}^low| and a lightweight motion map, feed [current_low, disagreement, motion] into Conv-BN-SiLU-Conv + sigmoid to obtain a pre-uncertainty map. Use 1 + tanh(gamma) * uncertainty to modulate historical frames only.
4. ST-Pool2 branch: apply AvgPool2d with kernel=2 and stride=2, flatten the pooled clip into a spatio-temporal token sequence [B,T×H/2×W/2,Cs], apply LayerNorm, then Mamba SSM (or BiGRU fallback). Extract the target-frame token slice, reshape it to [B,Cs,H/2,W/2], expand channels back to C with 1×1 convolution, and bilinearly upsample to [H,W]. Compute temporal_delta = state - center.
5. Post-uncertainty residual injection: compute post uncertainty from [center, |temporal_delta|, motion_lite], compute residual = Conv([temporal_delta, motion_lite]), and output F'_t = F_t + alpha * (0.75 + 0.5 * post_uncertainty) * residual.

Use orange for the main temporal fusion path, purple for Mamba/SSM, yellow/red for uncertainty branches, and green for the residual connection. Add concise annotations: “Pool2 reduces token length”, “spatio-temporal sequence modeling”, “uncertainty-conditioned history modulation”, “conservative residual injection”, “alpha initialized to 1e-3”, and “gamma initialized to 0”. White background, vector style, suitable for a paper figure.
```

---

## 10. 可直接放入报告的 Mermaid 草图

### 10.1 总体架构 Mermaid

```mermaid
flowchart LR
    A[3-frame causal clip<br/>I_{t-2}, I_{t-1}, I_t] --> B1[Reference frames<br/>no_grad + BN frozen]
    A --> B2[Target frame I_t<br/>gradient path]

    B1 -.-> C[Shared YOLOv10s Backbone]
    B2 --> C

    C --> D[Layer 10: PSA / P5 feature]
    D --> E[UC-Mamba-ST-Pool2<br/>Temporal Fusion]
    E --> F[Fused P5 replaces layer 10]
    F --> G[YOLOv10 Neck / PAN-FPN<br/>Upsample + Concat P4/P3 + C2f]
    G --> H[v10Detect]
    H --> I[Current-frame detections]
```

### 10.2 模块内部 Mermaid

```mermaid
flowchart TB
    A[Input P5 clip<br/>[B,T,C,H,W]] --> B[1x1 Conv Reduce<br/>C -> Cs]
    B --> C[low_clip<br/>[B,T,Cs,H,W]]

    C --> U1[Pre-uncertainty<br/>current, disagreement, motion]
    U1 --> U2[History modulation<br/>1 + tanh(gamma) * uncertainty]

    U2 --> P[AvgPool2d k=2,s=2<br/>[B,T,Cs,H/2,W/2]]
    P --> S[Flatten ST tokens<br/>[B,T*H/2*W/2,Cs]]
    S --> N[LayerNorm]
    N --> M[Mamba SSM<br/>or BiGRU fallback]
    M --> R[Target-frame token slice]
    R --> E[Reshape + 1x1 Expand + Upsample]
    E --> D[temporal_delta = state - center]

    D --> U3[Post-uncertainty<br/>center, |delta|, motion_lite]
    D --> Res[Residual Conv]
    U3 --> O[Conservative residual injection]
    Res --> O
    O --> Y[Fused current feature<br/>F'_t]
```
