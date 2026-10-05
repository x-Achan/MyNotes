# STDA-DINO: Small-Object-Aware Temporal Deformable Alignment for Video Object Detection in Traffic Surveillance

**Authors:** [Author 1], [Author 2], [Author 3]  
**Affiliations:** [Affiliation 1], [Affiliation 2]  
**Corresponding Author:** [Name, Email]  
**Submission Type:** Generic English Conference Paper Draft  
**Version:** v1.0

---

## Abstract

Traffic surveillance video object detection remains challenging because targets are frequently small, partially occluded, blurred by motion, and captured under large scale variations. Although strong image detectors can achieve high accuracy on individual frames, they usually ignore the temporal redundancy and complementary evidence available in neighboring frames. A direct temporal fusion strategy, however, may introduce misaligned features because moving vehicles do not occupy the same spatial locations across frames, and this issue is particularly harmful for small objects whose discriminative regions cover only a few pixels. In this paper, we propose **STDA-DINO**, a video object detection framework that integrates a VideoMamba backbone with a DINO-style deformable transformer detector and a **Small-object-aware Temporal Deformable Alignment** module. The proposed STDA module enhances center-frame features by learning local deformable sampling offsets from neighboring frames, estimating reliability-aware temporal aggregation weights, and injecting the aligned temporal context through a conservative residual gate. To better handle scale-dependent alignment errors, STDA adopts a level-aware design: high-resolution feature levels use smaller offsets and denser sampling for small objects, while low-resolution levels use a larger offset range for medium and large moving objects. Experiments on a sequence-level split of UA-DETRAC show that STDA-DINO improves the VideoMamba-DINO baseline from 0.6651 to 0.7069 mAP, with 0.8401 mAP50 and 0.7989 mAP75. Ablation studies further show that reliable temporal alignment and conservative gated injection are crucial for stable video detection. The current draft also reports YOLOv10-S as a strong practical detector reference and identifies the remaining baseline and dense-evaluation experiments required before final submission.

**Keywords:** Video object detection, traffic surveillance, temporal feature fusion, deformable alignment, small object detection, VideoMamba, DINO.

---

## 1. Introduction

Video object detection is a fundamental task for intelligent transportation systems, traffic monitoring, and surveillance analytics. Unlike still-image object detection, traffic videos provide temporally adjacent frames that contain repeated observations of the same objects. These repeated observations can compensate for transient degradation in individual frames, such as motion blur, partial occlusion, low resolution, defocus, and illumination variation. In principle, exploiting temporal information should improve detection robustness, especially for small vehicles and distant traffic participants that are difficult to localize from a single frame.

However, temporal fusion in traffic videos is non-trivial. A straightforward aggregation of neighboring frame features may introduce noise rather than useful context, because vehicles move across frames and their spatial locations are not naturally aligned. This misalignment becomes more harmful for small objects: even a minor offset can cause the sampled feature to fall on background regions or adjacent vehicles. Therefore, an effective video detection model should not only use neighboring frames, but also align them in a scale-aware and reliability-aware manner.

Recent object detectors based on Transformer architectures, such as DETR variants and DINO, have simplified detection pipelines and achieved strong accuracy through object queries, denoising training, mixed query selection, and iterative box refinement. Meanwhile, state space models such as Mamba and VideoMamba have shown promise for efficient long-range sequence modeling in vision and video understanding. These developments motivate us to investigate whether a VideoMamba-based video backbone can be combined with a DINO-style detection head for center-frame traffic video detection. More importantly, we study whether an explicit feature-level temporal alignment module can further improve the baseline beyond the implicit temporal representation learned by the backbone.

In this work, we propose **STDA-DINO**, a video object detection framework centered on **Small-object-aware Temporal Deformable Alignment**. Given an input video clip, a VideoMamba-Tiny backbone extracts multi-layer spatiotemporal token representations. A multi-layer feature aggregator and a simple feature pyramid produce multi-scale feature maps. Instead of directly forwarding only the center-frame features to the detector, we introduce STDA after the feature pyramid and before the DINO deformable transformer encoder. STDA takes multi-frame features at each pyramid level, aligns neighboring frames to the center frame by learned deformable sampling, weights sampled features using reliability-aware temporal attention, and injects the temporal context through a conservative residual gate.

The design of STDA is motivated by a series of controlled experiments. A basic deformable temporal alignment module already improves the VideoMamba-DINO baseline, showing that explicit neighboring-frame alignment is beneficial. A subsequent small-object-aware version introduces local temporal windows, level-aware sampling, frame reliability, and motion-prior gating, but it underperforms due to excessive suppression of temporal signals. The final version keeps level-aware sampling and reliability weighting, removes the overly restrictive motion-prior gate, expands the temporal window, and applies a unified conservative gate initialization. This design achieves the best result in our current experiments.

Our contributions are summarized as follows:

1. We build a VideoMamba-DINO video detection framework for center-frame traffic surveillance detection, combining a VideoMamba backbone, multi-layer feature aggregation, a simple feature pyramid, and a DINO deformable transformer detector.
2. We propose a small-object-aware temporal deformable alignment module that performs learnable spatial alignment over neighboring frame features before DINO encoding.
3. We introduce a level-aware temporal sampling strategy and reliability-aware aggregation to reduce misalignment noise, especially for small objects in high-resolution feature levels.
4. We empirically analyze the evolution from generic temporal alignment to small-object-aware alignment and show that conservative gated temporal injection is important for stable training.
5. On UA-DETRAC, our current best model improves the VideoMamba-DINO baseline from 0.6651 to 0.7069 mAP, demonstrating the effectiveness of explicit temporal alignment under the same architecture.

The goal of this paper is not to claim that STDA-DINO universally outperforms highly optimized single-frame detectors such as YOLOv10. Instead, the central question is whether explicit temporal deformable alignment improves a VideoMamba-DINO video detection framework. Accordingly, our main analysis focuses on controlled comparisons within the same architecture, while strong image detectors are reported as practical references.

---

## 2. Related Work

### 2.1 Image Object Detection

Image object detection has progressed from convolutional detectors to query-based Transformer detectors. YOLO-family detectors are widely used due to their high inference speed and strong engineering performance. YOLOv10 further explores real-time end-to-end detection with an NMS-free design, making it a strong practical baseline for traffic object detection.

DETR reformulates object detection as a set prediction problem and removes many hand-designed components. Deformable DETR improves convergence and efficiency by attending to sparse spatial sampling points. DINO further strengthens DETR-like detection with improved denoising anchor boxes, mixed query selection, and iterative box refinement, achieving strong performance in end-to-end object detection. Since our detector head follows the DINO-style deformable transformer design, DINO and RT-DETR are natural comparison candidates for future controlled baselines.

### 2.2 Video Object Detection

Video object detection aims to improve per-frame detection by exploiting temporal information from adjacent or long-range frames. FGFA performs flow-guided feature aggregation along motion paths to improve degraded frame features. SELSA aggregates sequence-level semantic information to build more discriminative video features. MEGA introduces memory-enhanced global-local aggregation to combine local temporal evidence and global semantic memory. TransVOD explores end-to-end video object detection with spatial-temporal Transformers and object-query-based temporal modeling.

These methods demonstrate that temporal context is beneficial for video detection. However, many classical video detection methods are developed and evaluated mainly on ImageNet VID. In contrast, this paper focuses on traffic surveillance videos, where small vehicle detection and fixed-camera temporal alignment are central challenges. Our method differs from optical-flow-based aggregation by directly learning deformable temporal sampling offsets from feature differences, avoiding reliance on an external flow estimator.

### 2.3 Temporal Alignment and Deformable Aggregation

Temporal feature aggregation often requires spatial alignment. Without alignment, features from neighboring frames may correspond to background or different objects. Flow-based methods estimate explicit motion, while deformable attention and deformable convolution learn sparse sampling positions implicitly. Our STDA module follows the latter direction by predicting offsets and attention weights with respect to the center-frame feature. Compared with generic deformable fusion, STDA introduces a scale-aware design: high-resolution feature levels use smaller offsets to protect small objects, while low-resolution levels allow larger search ranges for larger objects and stronger motion.

### 2.4 State Space Models for Video Understanding

Mamba introduces selective state spaces for efficient sequence modeling with linear complexity. VideoMamba extends state space modeling to video understanding and provides an efficient backbone for spatiotemporal representation learning. In this work, we use VideoMamba-Tiny as the backbone to extract temporally informed token representations from an input clip. Nevertheless, our experiments show that implicit temporal modeling in the backbone is not sufficient: explicit feature-level temporal alignment still brings a clear improvement over the no-fusion baseline.

---

## 3. Method

### 3.1 Problem Formulation

Given a video clip

\[
X \in \mathbb{R}^{B \times C \times T \times H \times W},
\]

where \(B\) is the batch size, \(C\) is the number of image channels, \(T\) is the number of frames, and \(H, W\) are spatial dimensions, the goal is to detect objects in the center frame. In our current implementation, \(T=8\), and the model predicts class logits and bounding boxes for the center frame:

\[
\hat{Y}_{c}=\{(\hat{p}_i, \hat{b}_i)\}_{i=1}^{N_q},
\]

where \(N_q=300\) denotes the number of object queries, \(\hat{p}_i\) is the predicted class distribution, and \(\hat{b}_i\) is the predicted bounding box.

### 3.2 Overall Architecture

The overall architecture of STDA-DINO consists of five parts:

1. **VideoMamba backbone.** The input clip is processed by a VideoMamba-Tiny backbone with 24 bidirectional Mamba layers and embedding dimension 192. Hidden states from multiple layers are extracted for multi-level representation.
2. **Multi-layer feature aggregation.** Selected hidden states are normalized, linearly projected, and combined by learnable softmax weights.
3. **Simple feature pyramid.** The aggregated token map is converted into four spatial feature levels with strides approximately corresponding to 1/8, 1/16, 1/32, and 1/64 of the input resolution.
4. **Small-object-aware temporal deformable alignment.** For each feature level, multi-frame features are aligned and fused into an enhanced center-frame feature map.
5. **DINO deformable transformer detector.** The enhanced multi-scale center-frame features are passed to the DINO-style deformable transformer encoder and decoder to produce final detections.

The current model has approximately 33.5M parameters, including about 22M parameters in the VideoMamba-Tiny backbone, 8M in the DINO transformer and heads, 2M in the feature pyramid and projection layers, and 1.5M in the temporal fusion modules. Exact parameter count and FLOPs should be filled after running the final profiling script.

### 3.3 VideoMamba-DINO Baseline

The no-fusion baseline processes all frames using the VideoMamba backbone but uses only the center-frame feature map for detection after feature aggregation and pyramid construction. This baseline allows us to isolate the contribution of explicit feature-level temporal fusion. Since the backbone itself receives the full video clip, the baseline already contains implicit temporal modeling. Therefore, any improvement from STDA indicates the added value of explicit temporal alignment beyond backbone-level sequence processing.

Formally, the baseline can be written as:

\[
F_c^{l}=\mathrm{SFP}^{l}(\mathrm{Agg}(\mathrm{VideoMamba}(X)))_c,
\]

where \(F_c^{l}\) denotes the center-frame feature at pyramid level \(l\). The detector then predicts:

\[
\hat{Y}_c = \mathrm{DINO}(\{F_c^{l}\}_{l=1}^{L}).
\]

### 3.4 Small-Object-Aware Temporal Deformable Alignment

For each pyramid level \(l\), the temporal feature tensor is represented as:

\[
F^{l} = \{F^{l}_t\}_{t=1}^{T}, \quad F^{l}_t \in \mathbb{R}^{B \times C \times H_l \times W_l}.
\]

Let \(c\) be the center-frame index. STDA aims to align neighboring frame features \(F^{l}_t\) to \(F^{l}_c\) and aggregate useful temporal context.

For each temporal neighbor \(t\), we build an alignment input by concatenating the center feature and the feature difference:

\[
A^{l}_t = \mathrm{Concat}(F^{l}_c, F^{l}_t - F^{l}_c).
\]

The difference term provides a local cue about appearance and motion discrepancy. A lightweight convolutional prediction network estimates sampling offsets and attention logits:

\[
(\Delta P^{l}_{t,k}, a^{l}_{t,k}) = \phi_l(A^{l}_t), \quad k=1,\dots,K_l,
\]

where \(K_l\) is the number of sampling points at level \(l\). The raw offsets are constrained with a hyperbolic tangent and a level-specific maximum offset:

\[
\Delta P^{l}_{t,k}=\mathrm{tanh}(\Delta \tilde{P}^{l}_{t,k}) \cdot r_l.
\]

Here, \(r_l\) is the maximum offset range. This constraint prevents early training from producing excessively large offsets, which is important for small-object stability.

Given a regular grid coordinate \(p"), the sampled feature is:

\[
\tilde{F}^{l}_{t,k}(p)=\mathrm{Bilinear}(F^{l}_t, p + \Delta P^{l}_{t,k}(p)).
\]

The temporal context is obtained by a softmax-weighted aggregation over temporal neighbors and sampling points:

\[
C^{l}(p)=\sum_{t \in \mathcal{T}_c}\sum_{k=1}^{K_l}\alpha^{l}_{t,k}(p)\tilde{F}^{l}_{t,k}(p),
\]

where \(\mathcal{T}_c\) is the selected local temporal window around the center frame.

### 3.5 Level-Aware Sampling for Small Objects

A single offset range is suboptimal for all pyramid levels. High-resolution feature maps are crucial for small objects, but they are also more sensitive to offset errors. Therefore, STDA uses a level-aware sampling strategy:

- high-resolution levels use \(K_l=4\) sampling points and a smaller maximum offset \(r_l=2.0\);
- low-resolution levels use \(K_l=3\) sampling points and a larger maximum offset \(r_l=3.0\).

This design keeps high-resolution temporal sampling local and precise, reducing the risk that small-object features are replaced by background. At lower resolutions, a larger offset range is allowed because each feature cell covers a larger image region and larger motion can be tolerated.

### 3.6 Reliability-Aware Temporal Aggregation

Neighboring frames may be unreliable due to occlusion, blur, or severe displacement. To reduce harmful temporal signals, STDA includes a reliability branch that predicts reliability logits and adds them to temporal attention logits before softmax normalization:

\[
\alpha^{l}_{t,k}(p)=\mathrm{Softmax}_{t,k}(a^{l}_{t,k}(p)+r^{l}_{t,k}(p)).
\]

The reliability term encourages the model to down-weight uncertain or misaligned samples. This mechanism is particularly useful in fixed-camera traffic surveillance scenes, where temporary occlusion by other vehicles is common.

### 3.7 Conservative Residual Gating

After obtaining temporal context \(C^{l}\), directly replacing the center-frame feature can destabilize training. We therefore use residual gated injection:

\[
G^{l}=\sigma(\psi_l(\mathrm{Concat}(F^{l}_c, C^{l}))),
\]

\[
\hat{F}^{l}_c=\mathrm{Norm}(F^{l}_c + G^{l}\odot C^{l}).
\]

The gate bias is initialized to \(-2.0\), making the initial gate value small. This conservative initialization allows the model to begin training close to the center-frame baseline and gradually learn to incorporate reliable temporal context. Our experiments show that this design is more stable than an overly open gate or a double-suppression design that combines reliability weighting with an additional motion-prior gate.

### 3.8 Design Evolution: V1, V2, and V3

We evaluate three main versions of temporal deformable alignment.

**V1** uses all frames, a uniform number of sampling points across all feature levels, a maximum offset of 4.0, and a simple residual gate. It improves the no-fusion baseline, showing that deformable temporal alignment is effective.

**V2** introduces small-object-aware ideas: a local temporal window, level-aware offset ranges, a reliability branch, and motion-prior gating. However, it performs worse than V1. We attribute this to two issues: the temporal window is too narrow, and the combination of reliability weighting and motion-prior gating excessively suppresses useful temporal signals.

**V3**, the final version used in STDA-DINO, keeps the useful components of V2 while removing the excessive suppression. It uses a temporal radius of 3, which covers up to 7 frames around the center frame, retains level-aware sampling and reliability aggregation, removes the motion-prior gate, uses 3 sampling points on low-resolution levels, and applies a unified gate bias of \(-2.0\).

---

## 4. Experiments

### 4.1 Dataset

#### UA-DETRAC

UA-DETRAC is a traffic surveillance benchmark containing 100 challenging real-world video sequences. In this work, we use a sequence-level 60/20/20 split. Specifically, 60 sequences are used for training, 20 for validation, and 20 for testing. The split is generated with a balanced strategy using `seed=42`, considering frame counts, box counts, and category statistics from XML annotations. Entire video sequences are assigned to one split, and frames from the same sequence are not shared across training, validation, and test sets.

UA-DETRAC contains four vehicle categories in our setting: **car**, **van**, **bus**, and **others**. The class distribution is highly imbalanced, with cars occupying the majority of annotations.

The YOLO-format split used for YOLOv10 is exported from the same sequence-level split. The training set contains 87,242 images and 750,827 boxes with frame step 1; the validation set contains 5,270 images and 50,147 boxes with frame step 5; the test set contains 5,184 images and 41,803 boxes with frame step 5. For VideoMamba-DINO, current experiments include a sparse sliding-window evaluation setting and a denser evaluation setting. Final submission should report the same dense evaluation setting when comparing with YOLO-style frame detectors.

#### VisDrone-MOT

We also report preliminary results on VisDrone-MOT, which contains ten categories: pedestrian, people, bicycle, car, van, truck, tricycle, awning-tricycle, bus, and motor. The current VisDrone experiments are exploratory and are not used as the main claim of this draft, because the model has not yet been fully tuned for dense small-object scenes.

### 4.2 Implementation Details

Unless otherwise stated, all VideoMamba-DINO experiments are conducted on 4 NVIDIA A30 GPUs with 24 GB memory each. The backbone is initialized from a Kinetics-400 pretrained VideoMamba-Tiny checkpoint. The DINO transformer and prediction heads are initialized from a COCO 4-scale DINO checkpoint, while the feature pyramid, feature aggregation layers, input projection, and STDA modules are randomly initialized.

The input resolution on UA-DETRAC is 544 × 960, and the clip length is \(T=8\). The DINO detector uses 300 object queries. We train with AdamW, a base learning rate of \(2\times10^{-4}\), MultiStepLR scheduling, gradient clipping with maximum norm 0.1, mixed precision training, and gradient accumulation. The loss consists of focal classification loss, L1 box loss, GIoU loss, denoising loss, and auxiliary decoder losses.

For the original strategy, the backbone learning rate multiplier is 0.1, and the FPN/temporal fusion/head modules use the base learning rate. For the final Plan C strategy, the FPN and temporal fusion learning rate multiplier is reduced to 0.1, weight decay is increased to 0.005, drop path is increased to 0.3, and learning-rate drops are moved earlier. This strategy is designed to stabilize newly initialized temporal fusion modules.

**To be filled before final submission:** exact PyTorch version, CUDA runtime version, total batch size per GPU, number of epochs used for the final dense evaluation, exact parameter count, FLOPs, and FPS.

### 4.3 Main Ablation Results on UA-DETRAC

Table 1 shows the main controlled comparison within the VideoMamba-DINO framework. The no-fusion baseline reaches 0.6651 mAP. Motion-guided temporal fusion improves the baseline to 0.6808 mAP, indicating that temporal context is useful, but its lack of spatial alignment limits effectiveness. V1 deformable alignment reaches 0.6971 mAP, confirming the benefit of learnable temporal alignment. V2 decreases to 0.6914 mAP, suggesting that simply adding more small-object-aware components is not sufficient if the temporal signal becomes over-suppressed. The final V3 design reaches 0.7017 mAP under the default strategy. With Plan C training stabilization, STDA-DINO achieves the best current result of 0.7069 mAP, 0.8401 mAP50, and 0.7989 mAP75.

**Table 1. Main ablation results on UA-DETRAC.**

| Method | Temporal Module | Training | mAP | mAP50 | mAP75 | AP_S | AP_M | AP_L |
|---|---|---|---:|---:|---:|---:|---:|---:|
| VideoMamba-DINO | None | Default | 0.6651 | 0.8277 | 0.7613 | 0.2860 | 0.6584 | 0.7099 |
| VideoMamba-DINO | Motion-guided | Default, 36ep | 0.6808 | 0.8190 | 0.7767 | - | - | - |
| VideoMamba-DINO | Deformable Align V1 | Default | 0.6971 | 0.7988 | 0.7734 | 0.2595 | 0.6730 | 0.7168 |
| VideoMamba-DINO | Small-object-aware V2 | Default | 0.6914 | 0.8267 | - | - | - | 0.7552 |
| VideoMamba-DINO | Small-object-aware V3 | Default | 0.7017 | 0.8297 | 0.7870 | 0.2841 | 0.6593 | 0.7637 |
| **STDA-DINO** | **V3** | **Plan C** | **0.7069** | **0.8401** | **0.7989** | **0.2813** | **0.6541** | **0.7642** |

These results support two observations. First, explicit temporal alignment improves the baseline even though VideoMamba already processes the full clip. Second, the best temporal module is not the most complex one; rather, performance depends on balancing temporal coverage, alignment flexibility, reliability suppression, and residual injection strength.

### 4.4 Analysis of V1, V2, and V3

Table 2 summarizes the structural differences between V1, V2, and V3.

**Table 2. Design comparison of temporal alignment variants.**

| Design | V1 | V2 | V3 |
|---|---|---|---|
| Temporal coverage | all 8 frames | center ± 2 | center ± 3 |
| High-res sampling points | 4 | 4 | 4 |
| Low-res sampling points | 4 | 2 | 3 |
| High-res max offset | 4.0 | 2.0 | 2.0 |
| Low-res max offset | 4.0 | 3.0 | 3.0 |
| Reliability branch | No | Yes | Yes |
| Motion-prior gate | No | Yes | No |
| Gate input | center, context | center, context, motion | center, context |
| Gate bias | -2.0 | mixed | -2.0 |
| Best mAP | 0.6971 | 0.6914 | 0.7017 |

V1 validates the effectiveness of deformable temporal alignment. V2 introduces more prior constraints, but the result indicates that reliability weighting and motion-prior gating together may suppress useful temporal context too strongly. V3 recovers temporal coverage, removes the motion-prior gate, and uses a conservative but simple residual gate. This version achieves the best default-strategy mAP among temporal fusion variants.

### 4.5 Training Stabilization

The original strategy shows an early-peak pattern and relatively large oscillations. For example, V3 reaches 0.7017 mAP at epoch 6 but fluctuates afterward. The final Plan C strategy reduces the learning rate of FPN and temporal fusion modules, strengthens regularization, and applies earlier learning-rate decay. As shown in Table 3, this strategy improves V3 from 0.7017 to 0.7069 mAP and reduces the oscillation magnitude from approximately 0.05 to approximately 0.015.

**Table 3. Effect of training stabilization.**

| Method | Training Strategy | Best mAP | mAP50 | mAP75 | Oscillation |
|---|---|---:|---:|---:|---:|
| V3 | Default | 0.7017 | 0.8297 | 0.7870 | ~0.05 |
| V3 | Plan C | **0.7069** | **0.8401** | **0.7989** | **~0.015** |
| V3 | Plan C + EMA | 0.6952 | 0.8288 | 0.7884 | ~0.007 |

Although EMA smooths the training curve, EMA with decay 0.999 under the current short training schedule underperforms Plan C. We hypothesize that the decay is too slow to track the rapidly improving non-EMA model when learning-rate drops occur early. Therefore, EMA is not used in the current best model.

### 4.6 Comparison with Strong Practical Detectors

Table 4 reports the currently available YOLOv10-S result on the same UA-DETRAC sequence split. The YOLOv10-S baseline is trained for 100 epochs with image size 960 and obtains 0.6381 mAP50-95 and 0.8083 mAP50 on the exported split60 frame dataset. This result is a strong practical reference. However, the current STDA-DINO result and YOLOv10-S result should be interpreted carefully until the final dense evaluation setting is fully matched.

**Table 4. Practical detector reference. Final dense-evaluation numbers should be filled before submission.**

| Method | Input | Temporal Input | mAP50-95 | mAP50 | Precision | Recall | Notes |
|---|---:|---:|---:|---:|---:|---:|---|
| YOLOv10-S | 960 | single frame | 0.6381 | 0.8083 | 0.8753 | 0.7371 | same sequence split, exported frame dataset |
| STDA-DINO | 544×960 | 8-frame clip | **[DenseEval TODO]** | **[DenseEval TODO]** | - | - | final dense evaluation required |
| STDA-DINO | 544×960 | 8-frame clip | 0.7069 | 0.8401 | - | - | current main ablation setting |

We include YOLOv10-S to avoid restricting the paper to internal ablations. Nevertheless, the primary claim of this work remains architectural: explicit temporal deformable alignment improves VideoMamba-DINO under controlled settings. Before final submission, at least one DINO-R50 or RT-DETR baseline should be trained on the same split to provide a more architecture-aligned comparison.

### 4.7 Split60 and VisDrone Exploratory Results

Table 5 reports additional results. On UA-DETRAC split60 evaluation, V3 improves mAP50 and mAP75 compared with the no-fusion version, but the difference in mAP is small. On VisDrone-MOT, the current results are low due to dense small objects, more categories, and insufficient tuning. These results are currently treated as exploratory rather than central claims.

**Table 5. Additional exploratory results.**

| Dataset | Method | Input | Queries | Best mAP | mAP50 | mAP75 |
|---|---|---:|---:|---:|---:|---:|
| UA-DETRAC split60 | None | 544×960 | 300 | 0.5820 | 0.7705 | 0.6828 |
| UA-DETRAC split60 | V3 | 544×960 | 300 | 0.5899 | 0.8010 | 0.6929 |
| VisDrone-MOT | V3 | 640×960 | 300 | 0.0959 | 0.1998 | - |
| VisDrone-MOT | V3-large | 768×1280 | 900 | 0.1096 | 0.2273 | 0.0916 |
| VisDrone-MOT | YOLOv10-S | 960 | - | 0.1402 | 0.2740 | - |

### 4.8 Discussion

The current experiments suggest that temporal alignment is effective but sensitive. V1 improves the baseline substantially, but V2 demonstrates that adding priors can hurt when they suppress temporal evidence too strongly. V3 performs best because it balances alignment flexibility and conservative injection. Plan C further stabilizes learning by reducing the learning rate of newly initialized temporal modules.

Small-object performance remains an open issue. In early Plan C epochs, AP_S is high, but it decreases in later epochs, suggesting that strong regularization may suppress fine-grained small-object features. Future work should investigate more balanced regularization, adaptive high-resolution feature learning, and parameter-level ablations.

Query Temporal Mamba is also not used as a main contribution in this draft. Although it is conceptually complementary to feature-level temporal alignment, the current QTM-v1 result does not exceed V3 + Plan C. It should therefore remain an exploratory module until further tuning improves performance.

---

## 5. Limitations

This draft has several limitations that should be addressed before final submission. First, the current best STDA-DINO number should be re-evaluated under the same dense frame sampling protocol used by the YOLOv10 frame dataset. Second, a pure DINO or RT-DETR baseline should be trained on the same split to show that the improvements are not merely due to the DINO detection head. Third, exact FLOPs, parameter count, and inference speed are not yet reported. Fourth, VisDrone-MOT results are not strong enough to support cross-dataset generalization claims. Finally, although V1/V2/V3 provide useful combined ablations, more fine-grained sensitivity analysis on temporal radius, sampling points, max offset, reliability branch, and gate bias would make the design justification stronger.

---

## 6. Conclusion

We present STDA-DINO, a VideoMamba-DINO framework with small-object-aware temporal deformable alignment for traffic surveillance video object detection. The proposed STDA module aligns neighboring frame features to the center frame through learned deformable sampling, reliability-aware aggregation, level-aware sampling, and conservative residual gating. Controlled experiments on UA-DETRAC show that explicit temporal alignment improves the VideoMamba-DINO baseline from 0.6651 to 0.7069 mAP. The results indicate that even when a video backbone already processes multiple frames, explicit feature-level temporal alignment remains beneficial for center-frame detection. The current version provides a solid foundation for a submission-oriented paper, while final dense evaluation, architecture-aligned baselines, and efficiency profiling should be completed before submission.

---

## References

[1] H. Zhang, F. Li, S. Liu, L. Zhang, H. Su, J. Zhu, L. M. Ni, and H.-Y. Shum. **DINO: DETR with Improved DeNoising Anchor Boxes for End-to-End Object Detection.** ICLR, 2023.

[2] X. Zhu, W. Su, L. Lu, B. Li, X. Wang, and J. Dai. **Deformable DETR: Deformable Transformers for End-to-End Object Detection.** ICLR, 2021.

[3] Y. Zhao, W. Lv, S. Xu, J. Wei, G. Wang, Q. Dang, Y. Liu, and J. Chen. **DETRs Beat YOLOs on Real-time Object Detection.** CVPR, 2024.

[4] A. Wang et al. **YOLOv10: Real-Time End-to-End Object Detection.** arXiv:2405.14458, 2024.

[5] K. Li, X. Li, Y. Wang, Y. He, Y. Wang, L. Wang, and Y. Qiao. **VideoMamba: State Space Model for Efficient Video Understanding.** ECCV, 2024.

[6] A. Gu and T. Dao. **Mamba: Linear-Time Sequence Modeling with Selective State Spaces.** arXiv:2312.00752, 2023.

[7] X. Zhu, Y. Wang, J. Dai, L. Yuan, and Y. Wei. **Flow-Guided Feature Aggregation for Video Object Detection.** ICCV, 2017.

[8] H. Wu, Y. Chen, N. Wang, and Z. Zhang. **Sequence Level Semantics Aggregation for Video Object Detection.** ICCV, 2019.

[9] Y. Chen, Y. Cao, H. Hu, and L. Wang. **Memory Enhanced Global-Local Aggregation for Video Object Detection.** CVPR, 2020.

[10] Q. Zhou, X. Li, L. He, Y. Yang, G. Cheng, Y. Tong, L. Ma, and D. Tao. **TransVOD: End-to-End Video Object Detection with Spatial-Temporal Transformers.** IEEE TPAMI / arXiv version, 2022.

[11] L. Wen, D. Du, Z. Cai, Z. Lei, M.-C. Chang, H. Qi, J. Lim, M.-H. Yang, and S. Lyu. **UA-DETRAC: A New Benchmark and Protocol for Multi-Object Detection and Tracking.** CVIU, 2020.

---

## Appendix A. Submission Placeholders

- **Author information:** [To be filled]
- **Affiliations:** [To be filled]
- **Funding:** [To be filled]
- **Code availability:** [To be filled]
- **Data split file / sequence list:** [To be attached]
- **Final dense evaluation:** [To be filled]
- **DINO/RT-DETR baseline:** [To be filled]
- **FLOPs / FPS / exact params:** [To be filled]
- **Qualitative figures:** [To be added]
