# YOLOv10 Temporal Experiment Log

更新时间：2026-06-10

本文档用于持续记录 YOLOv10 时序检测实验的重要配置、结果和阶段性结论。后续每次出现重要训练结果、代码结构变化或实验决策，都应更新本文档。

## 当前主线结论

当前最值得作为主线的方法是 **DMSA-MQ causal**：

```text
[t-2, t-1, memory, t] -> 检测 t
```

它在保持 online/causal 视频检测设定的同时，超过了普通 DMSA、DMSA-causal 和 dmsa_cg 的 best 指标：

```text
DMSA-MQ causal best:
mAP50     0.344
mAP50-95  0.187
```

这说明 memory queue / state token 方向有效，是目前最有创新解释和继续推进价值的方向。

## 实验结果总表

| 日期         | 实验名                      | 模型配置                               | 时序输入                    | 关键训练配置                                                    | Best epoch | Best mAP50 | Best mAP50-95 | Final mAP50 | Final mAP50-95 | 结论                                                              |
| ---------- | ------------------------ | ---------------------------------- | ----------------------- | --------------------------------------------------------- | ---------: | ---------: | ------------: | ----------: | -------------: | --------------------------------------------------------------- |
| 2026-06-11 | YOLOv10s baseline        | yolov10s                           | single frame            | imgsz=960, batch=24, lr0=0.0003, 12 epochs, seed=0        |          4 |      0.333 |         0.172 |       0.282 |          0.142 | 公平单帧 baseline。DMSA-MQ causal 相对 baseline 明确提升 mAP50 和 mAP50-95。 |
| 2026-06    | Identity sanity          | YOLOv10s temporal identity         | 3 frames, center target | imgsz=960, batch=60, 3 GPUs                               |          - |          - |             - |           - |              - | 验证时序数据管线可跑通，但 identity 实际只走中心帧，显存/速度不能代表真实时序模块。                 |
| 2026-06    | DIS ref-no-grad          | yolov10s-dis                       | [t-1,t,t+1] -> t        | imgsz=960, batch=24, lr0=0.001, 30 epochs                 |          2 |      0.323 |         0.170 |       0.247 |          0.120 | 早期有收益，但后期严重退化。reference no-grad 有效降低显存。                         |
| 2026-06    | DIS freeze11             | yolov10s-dis, freeze backbone part | [t-1,t,t+1] -> t        | imgsz=960, freeze=11, 30 epochs                           |          3 |      0.304 |         0.160 |       0.239 |          0.119 | 冻结 backbone 没有改善峰值，也没解决后期退化。                                    |
| 2026-06    | MTGR full Mamba          | yolov10s-mtgr                      | [t-1,t,t+1] -> t        | imgsz=960, batch=24, lr0=0.0003, 30 epochs                |        4-5 |      0.334 |         0.180 |       0.300 |          0.154 | 比 DIS 稳定且更强，但 full-channel Mamba 慢、显存高，接近 24G。                  |
| 2026-06    | DMSA Lite-Mamba          | yolov10s-dmsa                      | [t-1,t,t+1] -> t        | imgsz=960, batch=24, lr0=0.0003, 30 epochs                |          5 |      0.335 |         0.181 |     约 0.302 |        约 0.159 | 以更低显存/更快速度达到并略超 MTGR，是当前轻量 Mamba 主体。                            |
| 2026-06    | DMSA conservative gate   | yolov10s-dmsa-cg                   | [t-1,t,t+1] -> t        | imgsz=960, batch=24, lr0=0.0003, 15 epochs                |          5 |      0.333 |         0.179 |       0.309 |          0.163 | 更保守 gate/更小 alpha 没有突破，说明退化主因不只是 residual 太强。                   |
| 2026-06-10 | DMSA causal              | yolov10s-dmsa-causal               | [t-2,t-1,t] -> t        | imgsz=960, batch=24, lr0=0.0003, 15 epochs                |          5 |      0.338 |         0.184 |       0.304 |          0.160 | 当前最佳。causal/online 方向成立，但后期仍掉点。                                 |
| 2026-06-10 | DMSA causal low-lr short | yolov10s-dmsa-causal               | [t-2,t-1,t] -> t        | imgsz=960, batch=24, lr0=0.0002, 8 epochs, save_period=1  |          4 |      0.332 |         0.179 |       0.318 |          0.167 | 降低学习率到 0.0002 未超过原始 causal；峰值更晚但更低，不作为主线。                       |
| 2026-06-11 | DMSA-MQ causal           | yolov10s-dmsa-mq-causal            | [t-2,t-1,memory,t] -> t | imgsz=960, batch=24, lr0=0.0003, 12 epochs, save_period=1 |          5 |      0.344 |         0.187 |       0.310 |          0.165 | 当前最佳。Memory token 明确提高 mAP50 和 mAP50-95，值得作为新主线。                |

## 重要代码版本记录

### 已实现能力

| 功能 | 文件 | 说明 |
|---|---|---|
| TemporalYOLODataset | `ultralytics/data/dataset.py` | 支持返回 `[B,T,C,H,W]` clip；当前已支持 `temporal_causal=True`。 |
| temporal dataloader build | `ultralytics/data/build.py` | 当 `temporal_frames > 1` 时启用 TemporalYOLODataset。 |
| CLI 参数 | `ultralytics/cfg/default.yaml`, `ultralytics/cfg/__init__.py` | 已加入 `temporal_frames`, `temporal_stride`, `temporal_causal`。 |
| YOLOv10 temporal forward | `ultralytics/nn/tasks.py` | 支持 temporal clip、reference-frame no-grad、target last/center。 |
| TemporalFeatureFusion | `ultralytics/nn/modules/temporal.py` | 支持 identity, dis, mtgr, dmsa, dmsa_cg；DMSA 支持 `target_index`。 |
| DDP no-grad support | `ultralytics/engine/trainer.py` | reference no-grad 时启用 `find_unused_parameters=True`。 |
| temporal final eval skip | `ultralytics/models/yolov10/train.py` | 避免 AutoBackend final validation 处理 5D clip 报错。 |

### 当前核心 yaml

| 配置文件 | 作用 |
|---|---|
| `ultralytics/cfg/models/v10/yolov10s-dmsa.yaml` | 普通 Lite-Mamba DMSA，中心帧目标。 |
| `ultralytics/cfg/models/v10/yolov10s-dmsa-cg.yaml` | Conservative Gate 版本，峰值低于普通 DMSA。 |
| `ultralytics/cfg/models/v10/yolov10s-dmsa-causal.yaml` | 当前主线，causal `[t-2,t-1,t] -> t`。 |
| `ultralytics/cfg/models/v10/yolov10s-dmsa-mq-causal.yaml` | 待验证的 Memory-Queue DMSA，causal `[t-2,t-1,t] -> t`。 |
| `ultralytics/cfg/models/v10/yolov10s-dmsa-mq-sim-causal.yaml` | 待验证的 Similarity-aware Memory-Queue DMSA，causal `[t-2,t-1,t] -> t`。 |

## 关键发现

1. **identity 只能证明数据管线，不代表真实时序模块显存。**
   identity 模式实际只处理中心帧，所以 batch 可以很大，不能和 DMSA/MTGR/DIS 的显存直接比较。

2. **DMSA-MQ causal 已超过公平 YOLOv10s baseline。**
   YOLOv10s baseline best 为 0.333/0.172，DMSA-MQ causal best 为 0.344/0.187，提升为 +0.011 mAP50 和 +0.015 mAP50-95。

3. **reference-frame no-grad 是必要优化。**
   只对目标帧保留梯度，历史/参考帧 backbone no-grad，可以显著降低显存，为后续更复杂模块留空间。

4. **DIS 不稳定。**
   DIS 早期有收益，但 30 epoch 后明显退化，不适合作为主线。

5. **full-channel MTGR 有效但太重。**
   mAP 达到 0.334/0.180，但训练慢、显存接近 24G，工程风险偏高。

6. **Lite-Mamba DMSA 是更好的主体。**
   DMSA 用降维 Mamba 状态残差，基本达到/超过 MTGR，显存和速度更可控。

7. **过度保守 gate 不解决后期退化。**
   dmsa_cg 的 best 低于 DMSA，说明退化主因不只是 residual 进入检测流过强。

8. **causal sampling 是有效升级。**
   DMSA-causal 达到 0.338/0.184，超过普通 DMSA，同时具备 online 视频检测创新叙事。

9. **Memory Queue / State Token 是当前最有效升级。**
   DMSA-MQ causal 达到 0.344/0.187，超过 DMSA-causal 的 0.338/0.184，说明显式历史状态压缩比继续微调 gate/lr 更有价值。

10. **简单降低学习率没有提升峰值。**
   DMSA-causal 在 `lr0=0.0002, epochs=8` 下 best 为 0.332/0.179，低于 `lr0=0.0003` 的 0.338/0.184。

11. **共同问题：峰值出现在 epoch 3-5，随后下降。**
   后续应优先做训练稳定化，而不是继续堆更复杂模块。

## 推荐下一步实验

### 优先级 1：DMSA-causal 短训练稳定化

目标：在保持当前 causal 结构的基础上，把 best 从：

```text
mAP50     0.338
mAP50-95  0.184
```

推到：

```text
mAP50     >= 0.340
mAP50-95  >= 0.185
```

建议配置：

```text
epochs=8
lr0=0.0002 或 0.00015
save_period=1
imgsz=960
batch=24
temporal_frames=3
temporal_stride=1
temporal_causal=True
```

### 优先级 2：确认 best.pt 单独验证

单独 val 时必须保留：

```text
temporal_frames=3
temporal_stride=1
temporal_causal=True
```

否则验证会变回中心采样，导致模型 target:last 和数据标签错位。

### 优先级 3：online/state cache 推理设计

如果 DMSA-causal 的结果稳定，可继续扩展为：

```text
reference-frame no-grad
+ Lite-Mamba state residual
+ detection-aware gate
+ causal temporal sampling
+ online state sharing
```

这将成为更完整的论文创新闭环。

## 当前主线启动命令

```bash
cd ~/pro26
conda activate videomamba
mkdir -p yolo_outputs/logs

CUDA_VISIBLE_DEVICES=1,2,3 PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128 yolo detect train \
  model=yolov10-temporal/ultralytics/cfg/models/v10/yolov10s-dmsa-causal.yaml \
  data=/home/chenchenyang/pro26/datasets/VisDrone2019-MOT-YOLO/visdrone_mot.yaml \
  pretrained=yolov10-temporal/yolov10s.pt \
  imgsz=960 \
  batch=24 \
  epochs=15 \
  device=0,1,2 \
  temporal_frames=3 \
  temporal_stride=1 \
  temporal_causal=True \
  workers=8 \
  optimizer=SGD \
  lr0=0.0003 \
  seed=0 \
  project=/home/chenchenyang/pro26/yolo_outputs \
  name=visdrone_yolov10s_dmsa_causal_refnograd_3f_960_b24_e15 \
  exist_ok=True \
  plots=True 2>&1 | tee yolo_outputs/logs/visdrone_yolov10s_dmsa_causal_refnograd_3f_960_b24_e15.log
```

## 更新规范

后续每次新增重要实验结果，请至少记录：

```text
实验名
模型 yaml
时序输入方式
训练命令关键参数
best epoch
best mAP50
best mAP50-95
final mAP50
final mAP50-95
是否值得继续
一句话结论
```
