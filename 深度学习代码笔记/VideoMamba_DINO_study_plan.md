# VideoMamba-DINO 学习与实验成长计划（从当前项目出发）

> 适用对象：当前能够看懂部分代码、能在他人指导下跑实验，但对 DETR / DINO / Transformer / 视频检测机制还不够扎实的研一学生。  
> 目标：在 16 周内，从“能跑项目”成长到“能解释机制、能做基础消融、能尝试一个小创新”。

---

## 一、总目标

这个阶段不把目标定成“立刻做出一个很强的创新”，而是分成四级：

1. **能跑通**：知道数据如何进模型、loss 在哪里算、评估怎么做。
2. **能解释**：能讲清楚 DETR / DINO 的核心机制，以及当前项目各模块作用。
3. **能改动**：能自己改 1 个模块，跑 1 个消融实验。
4. **能提出小创新**：基于实验现象提出一个合理的小改动，并做验证。

---

## 二、当前项目中的主线（你所有学习都围绕这条线展开）

学习顺序必须围绕当前项目主链路，而不是泛泛学概念：

```text
数据加载 -> backbone(VideoMamba) -> 多层特征聚合 -> SFP多尺度 -> 时序融合
-> Deformable Transformer -> 检测头 -> 匹配器/损失 -> 后处理与评估
```

**对应重点文件**：

- `train.py`
- `datasets/uavdt.py`
- `models/videomamba_dino.py`
- `models/videomamba.py`
- `models/deformable_transformer.py`
- `models/matcher.py`
- `models/criterion.py`
- `models/postprocess.py`
- `tools/evaluate.py`

---

## 三、16 周成长路线图

# 阶段 1：先把项目“跑明白”（第 1-4 周）

### 阶段目标

- 跑通训练 / 验证 / 推理
- 看懂主 forward 的 shape 流
- 搞清楚检测任务最基础概念

### 第 1 周：项目跑通 + 建立整体地图

**学习目标**

- 明白项目目录结构
- 明白训练从哪里开始、在哪里结束
- 知道一个 batch 的数据经过了哪些模块

**必须完成的事**

- 跑通一次最小化训练或测试脚本（哪怕只跑几个 iter）
- 打印并记录：
  - `samples.shape`
  - `targets` 里有哪些字段
  - `outputs['pred_logits'].shape`
  - `outputs['pred_boxes'].shape`
- 自己画一张项目流程图

**本周要看代码**

- `train.py`
- `datasets/uavdt.py`
- `models/videomamba_dino.py`

**本周输出物**

- 一页纸项目总流程图
- 一个“代码入口地图”文档

---

### 第 2 周：PyTorch 与 shape 基础补强

**学习目标**

- 熟悉 `view / reshape / permute / flatten`
- 看懂 `Dataset / DataLoader / collate_fn`
- 看懂 `forward -> loss -> backward -> optimizer.step()`

**必须完成的事**

- 自己写一个最小 toy 网络（两层 MLP 或小 CNN）跑通训练
- 自己写一份“常见 shape 变换笔记”
- 回到项目代码，把 `VideoMambaDINO.forward()` 中每一步输入输出 shape 写出来

**本周要看代码**

- `datasets/uavdt.py`
- `models/videomamba_dino.py`

**本周输出物**

- `shape_笔记.md`
- `forward_注释版.md`

---

### 第 3 周：检测基础补强

**学习目标**

- 弄懂：bbox 格式、IoU / GIoU、mAP、AP50 / AP75
- 弄懂 focal loss 为什么用于分类

**必须完成的事**

- 手推并写清楚：
  - `xyxy` 与 `cxcywh` 的互转
  - IoU / GIoU 的基本含义
- 看项目里的损失实现，并回答：
  - 分类损失是什么
  - 框回归损失是什么
  - 为什么要同时有 L1 和 GIoU

**本周要看代码**

- `util/box_ops.py`
- `models/criterion.py`
- `models/matcher.py`

**本周输出物**

- `检测基础笔记.md`
- `loss_解释.md`

---

### 第 4 周：把数据、forward、loss、eval 串起来

**学习目标**

- 明白训练闭环是怎么完整跑起来的

**必须完成的事**

- 画出一张闭环图：
  - 数据从哪里来
  - 模型输出什么
  - 匹配如何做
  - loss 如何反传
  - 指标如何统计
- 能口头解释一次完整训练过程

**本周要看代码**

- `train.py`
- `models/postprocess.py`
- `tools/evaluate.py`

**本周输出物**

- `训练闭环图.png` 或 `训练闭环.md`

---

# 阶段 2：集中攻克 DETR / Deformable DETR / DINO（第 5-8 周）

### 阶段目标

- 真正理解 query、matching、decoder、deformable attention
- 能把论文原理和当前项目代码对应起来

### 第 5 周：DETR 入门周

**学习目标**

必须搞懂以下 5 个问题：

1. 为什么 DETR 把目标检测看成 set prediction？
2. object query 到底是什么？
3. 为什么需要 Hungarian matching？
4. decoder 每层在做什么？
5. DETR 为什么收敛慢？

**建议学习材料**

- 先看一遍李沐/论文精读类视频，建立直觉
- 再读 DETR 原论文摘要、方法图、损失部分
- 最后对照你项目里的 `matcher.py` 和 `criterion.py`

**本周必须完成的事**

- 画一张“DETR 工作流程图”
- 写一页“我理解的 query 是什么”

**本周输出物**

- `DETR_机制笔记.md`

---

### 第 6 周：Deformable DETR 周

**学习目标**

- 为什么普通 DETR 慢
- 为什么多尺度重要
- 什么是 deformable attention
- 什么是 reference points

**本周必须完成的事**

- 对照项目里的 `models/deformable_transformer.py`
- 写清楚：
  - encoder 输入是什么
  - decoder 输入是什么
  - reference points 在哪产生、怎么更新

**本周输出物**

- `Deformable_DETR_笔记.md`

---

### 第 7 周：DINO 周

**学习目标**

- DINO 相比 DETR / Deformable DETR 多了什么
- 对比去噪训练（DN）在干什么
- two-stage proposals 在干什么
- iterative refinement 为什么有效

**本周必须完成的事**

- 看懂项目中的：
  - `prepare_for_cdn()`
  - `class_embed / bbox_embed`
  - reference 逐层更新逻辑
- 自己总结：为什么 DINO 收敛更快、更稳

**本周输出物**

- `DINO_机制笔记.md`

---

### 第 8 周：项目映射总结周

**学习目标**

把下面这些一一对应起来：

- DETR 原理 -> 当前项目哪里实现
- Deformable DETR 原理 -> 当前项目哪里实现
- DINO 原理 -> 当前项目哪里实现

**本周必须完成的事**

- 写一份 3-5 页总结：
  - 你的项目哪些部分属于 VideoMamba
  - 哪些部分属于 DINO
  - 时序信息是在什么位置进入检测器的

**本周输出物**

- `项目_论文机制对照表.md`

---

# 阶段 3：开始做基础消融实验（第 9-12 周）

### 阶段目标

- 不追求创新，先练会做实验
- 学会记录、比较、解释结果

### 实验规则（整个阶段必须遵守）

1. 一次只改一个变量
2. 每个实验都记配置
3. 每个实验都写结论，不接受“跑完就算了”
4. 结果异常时先排查代码和数据，不急着解释成“新发现”

### 第 9 周：时序帧数实验

**实验主题**

- `num_frames = 4 / 8 / 16`

**观察指标**

- mAP / AP50 / AP75
- 训练速度
- 显存占用
- 是否更稳定

**输出物**

- `exp_01_num_frames.md`

---

### 第 10 周：时序融合实验

**实验主题**

比较：

- `temporal_fusion = mean`
- `temporal_fusion = conv1d`
- `temporal_fusion = recalib`

**你要回答的问题**

- 哪种融合更适合当前数据？
- 如果某种方法涨点，涨在什么场景？
- 如果不涨，是不是因为没有时序对齐？

**输出物**

- `exp_02_temporal_fusion.md`

---

### 第 11 周：多层聚合实验

**实验主题**

比较：

- 只用最后一层特征
- 使用多层特征聚合

**你要回答的问题**

- 小目标是否受益？
- 模型更偏语义还是更偏细节？

**输出物**

- `exp_03_multilayer_aggregation.md`

---

### 第 12 周：输入分辨率 / Query 数实验

**实验主题（二选一或都做）**

- 输入分辨率变化
- `num_queries` 变化

**你要回答的问题**

- 小目标检测对分辨率是否敏感？
- 当前场景是否真的需要 300 个 query？

**输出物**

- `exp_04_resolution_or_queries.md`

---

# 阶段 4：尝试一个小创新（第 13-16 周）

### 阶段目标

- 从“会做实验”进入“会提出可验证的小问题”
- 创新必须小、清楚、可复现

### 可选方向 A：在 backbone 中引入 temporal-first scan

**为什么适合你当前阶段**

- 它更贴近你现在的主线：VideoMamba 时序建模
- 比 query 创新更容易落地
- 它是 backbone 级改动，叙事更清楚

**建议问题**

- 全部层都 temporal-first 是否合适？
- 只在前几层加入 temporal-first 是否更稳？
- spatial-first 与 temporal-first 混合是否更适合交通监控？

---

### 可选方向 B：更稳妥的时序融合增强

**示例**

- center-aware temporal weighting
- level-wise temporal fusion
- motion-aware gate

**优点**

- 改动范围小
- 更容易 debug
- 更容易写清楚为什么有效或无效

---

### 可选方向 C：理解 query 后再做 query 创新

**前提**

只有当你已经真正弄懂 DETR / DINO query 机制，才进入这一步。

**可以考虑的小方向**

- temporal query warm-start
- motion-aware reference refinement
- query consistency regularization

**注意**

- 这类方向论文味更强
- 但也更难 debug
- 不建议作为你的第一个创新尝试

---

## 四、你现在开始就要建立的三个文档

### 1. 研究笔记库

每篇论文统一记录四件事：

- 这篇论文解决什么问题？
- 核心方法是什么？
- 为什么可能有效？
- 和我当前项目有什么关系？

### 2. 实验记录表

每次实验统一记录：

- 日期
- 实验名
- 改动点
- 配置
- 指标结果
- 主观分析
- 下一步动作

### 3. 错误与排查记录

统一记录：

- 报错是什么
- 出现在哪个文件
- 最终怎么解决
- 以后如何避免

---

## 五、每周固定节奏（建议）

### 工作日节奏（每天 2-3 小时即可）

- **40 分钟**：看原理（论文 / 教学视频 / 个人笔记）
- **40 分钟**：看代码（只盯一个模块）
- **40-60 分钟**：跑实验 / 记笔记 / 复盘

### 每周必须完成的三件事

1. 解决一个核心问题
2. 输出一份小文档
3. 跑一次小实验或小验证

### 每周复盘模板

```text
本周我真正搞懂了什么：
本周我还没搞懂什么：
我下周只重点攻克什么：
```

---

## 六、你今天就可以开始执行的任务清单

### 今天的主任务

#### 任务 1：看一遍 DETR 入门材料

目标不是全懂，而是先建立直觉：

- query 是什么
- 匹配是怎么做的
- decoder 在做什么

#### 任务 2：对照当前项目代码定位 DETR 对应部分

今天只看：

- `models/deformable_transformer.py`
- `models/matcher.py`
- `models/criterion.py`

然后回答：

- query 从哪里来？
- reference point 在哪里更新？
- 300 个 query 最后怎么和 GT 对应？

#### 任务 3：写第一份 1 页学习记录

题目可以叫：

`我现在理解的 DETR / DINO 是什么`

只需要写：

- 我已经懂了什么
- 我还不懂什么
- 我下一步准备看什么

---

## 七、未来 4 周的优先级排序

### 最高优先级

1. DETR 基本机制
2. 项目主 forward
3. matcher + criterion
4. eval / postprocess

### 中优先级

1. Deformable attention
2. DINO 的去噪训练
3. 多尺度特征与 reference points

### 暂缓项

1. 大而全的视频检测综述
2. 复杂 query 创新
3. CUDA 底层算子细节
4. 一开始就追求论文级强创新

---

## 八、判断自己有没有进步的标准

到 4 周时，你应该做到：

- 能独立讲清楚当前项目训练闭环
- 能看懂大部分张量 shape
- 知道 DETR / DINO 在当前项目中对应哪些代码

到 8 周时，你应该做到：

- 能独立解释 query、matching、deformable attention、DN
- 能把论文图和代码结构对应起来

到 12 周时，你应该做到：

- 能独立完成 2-4 个消融实验
- 能把结果整理成清楚的对比表

到 16 周时，你应该做到：

- 能提出一个小创新方向
- 能写出简洁的方法描述
- 能设计最基础的验证实验

---

## 九、给自己的提醒

1. **不要因为代码难就怀疑自己不适合做研究。** 研一看不懂复杂项目很正常。  
2. **先做“会解释、会改动、会验证”的人，再做“会创新”的人。**  
3. **你现在最重要的成长，不是学更多名词，而是形成稳定的研究节奏。**  
4. **每周只攻一个核心问题，远比同时学十个概念有效。**

---

## 十、接下来建议的第一步

从今天开始：

- 先看一遍 DETR 入门教学，建立直觉
- 当天就对照项目代码定位对应模块
- 然后写第一份自己的理解笔记

不要等“全懂了”再动手。  
**边学边看代码，边看代码边记笔记，边记笔记边做小实验。**

