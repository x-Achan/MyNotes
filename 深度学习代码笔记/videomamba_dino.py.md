# 前向传播 forward 函数
-----

## 输入预处理与维度适配

```python
# 保留原始的5D张量，后续输入videomamba中
original_samples = samples  # 保留原始维度
# 处理UAVDT数据集中，固定为5D
if samples.dim() == 5:
    B, C, T, H, W = samples.shape
    samples_flattened = samples.permute(0, 2, 1, 3, 4).flatten(0, 1) # B和T维度合并
# 防御性编程：兼容4D单帧推理
else:
    B, C, H, W = samples.shape
    T = 1
    samples_flattened = samples
# 转化为嵌入张量
samples = nested_tensor_from_tensor_list(samples_flattened)
```

### 嵌入张量
实际数据天然具有不同的尺寸
一批(batch)图片，每张图片分辨率不同，一批文本，长度不同，视频处理中，每个video帧数不同
- 传统方案：填充padding，存储大量零值，浪费内存
- 嵌套张量：实际数据保持原始尺寸，避免信息丢失，适合Transformer等注意力机制模型

在DINO模型中，使用nested_tensor_from_tensor_list，输入张量列表（拥有相同的通道数和维度，可以拥有不同的空间尺寸），返回一个NestedTensor对象（元组），输出包含两个部分：
1. tensors：填充到统一尺寸的实际数据张量
2. mask：标识哪些位置是填充区域的布尔掩码

## Backbone
```python
H, W = samples.tensors.shape[-2:]  # 提取图片的高宽
backbone_features = self.backbone(original_samples) # 输入到videomamba中
```
输入[B,T,C,H,W] ——> 输出[B * T,C,H,W]
videomamba输出的是一个特征字典，而不是单个张量
特征字典包捕获了不同层次的特征

## 特征金字塔与位置编码

```python
last_features = backbone_features[max(backbone_features.keys())]
fpn_features = self.sfp(last_features, img_size=(H, W))
features, poss = self._generate_pos_enc(fpn_features, samples)
```

构建多尺度特征，添加绝对位置信息

max(backbone_features.keys())取出最深层特征，再输入到sfp中进行多尺度特征提取videomamba的特征字典中，虽然包含了不同层的特征，但是每一层的分辨率没有改变过（不同于ResNet的天然金字塔结构），不能直接抽出 VideoMamba 的某几个中间层来代替特征金字塔，SFP是必要的

sfp返回一个张量列表，包含了四个不同尺度（1/8到1/64）的特征图，维度均为[B* T,C，H，W]

generate_pos_enc：接收特征金字塔和原始输入掩码，返回两个结构完全平行的列表
- 输入：
	- fpn_features：包含四个维度的特征
	- samples：嵌套张量，但是保存的原图的像素信息，含有原始mask掩码
- 输出：
	- features：嵌套张量，对四个维度的特征都打上mask
	- poss：包含四个张量，对应四个尺度，每个张量维度都是[B* T,C,H,W],装的是像素级别的GPS坐标，前128维记录该像素在Y轴位置，后128维记录在X轴上的位置


## 输入投影与时间截断

```python
srcs = []   
masks = []  
for l, feat in enumerate(features):
    src, mask = feat.decompose() #解包 NestedTensor
    srcs.append(self.input_proj[l](src)) # 线性投影调整通道数
    masks.append(mask)
    
# 🌟【新增核心逻辑】：截断时间维度，只把融合了时空特征的“中间帧”送入 Transformer🌟
mid_idx = T // 2
for i in range(len(srcs)):
    _, C_src, H_src, W_src = srcs[i].shape
    #将 [B*T, C, H, W] 拆解还原为 [B, T, C, H, W] 并切片取 mid_idx
    srcs[i] = srcs[i].view(B, T, C_src, H_src, W_src)[:, mid_idx]
    masks[i] = masks[i].view(B, T, H_src, W_src)[:, mid_idx]
    poss[i] = poss[i].view(B, T, C_src, H_src, W_src)[:, mid_idx]
```

self.input_proj：做一次1* 1卷积和归一化，让数据更适合 Transformer 去做自注意力计算


## 去噪训练准备

```python
if self.dn_number > 0 or targets is not None:
    input_query_label, input_query_bbox, attn_mask, dn_meta = prepare_for_cdn(...)
else:
    input_query_bbox = input_query_label = attn_mask = dn_meta = None
```

**加速收敛，解决DETR收敛慢的问题**

- prepare_for_cdn：构造Noisy Queries，对真实的Box和Label加上噪声，作为额外的Query输入给Decoder
- attn_mask：确保这些带噪声的 Query 只能看到对应的 GT，不能互相干扰，也不能被普通 Query 看到


## Transformer Decoder

```python
hs, reference, hs_enc, ref_enc, init_box_proposal = self.transformer(
    srcs, masks, input_query_bbox, poss, input_query_label, attn_mask
)
```

**执行核心的注意力机制，从特征图中“查找”目标**
传入中间帧的多尺度特征srcs、masks、poss以及去噪相关的辅助query
输出：
- hs (Hidden States): 解码器每一层输出的隐藏状态。里面包含了模型对目标的最终理解。它的维度通常是 [层数（6层）, Batch, Query总数, 隐藏维度]。  
- reference: 每一层预测时的参考点坐标（Deformable Attention 独有，它指引模型应该去特征图的哪个位置“看”细节）。  
- hs_enc, ref_enc, init_box_proposal: 这是用于 two_stage（两阶段机制）的编码器输出，它能提供更好的初始锚框（这三个参数暂时用不到）

示例数据形状：
```python
reference = [ref0, ref1, ref2, ref3, ref4, ref5, ref6]  # 7个元素
reference[0] 是初始参考点（可学习参数）
reference[1]: 是各层的参考点（来自上一层预测）

self.bbox_embed = [bbox_embed0, bbox_embed1, bbox_embed2, bbox_embed3, bbox_embed4, bbox_embed5]
# 6个边界框预测层（MLP网络）

hs = [hs0, hs1, hs2, hs3, hs4, hs5]  # 6个解码器层的输出特征
```


## 预测头


```python
outputs_coord_list = []  
for dec_lid, (layer_ref_sig, layer_bbox_embed, layer_hs) in enumerate(zip(reference[:-1], self.bbox_embed, hs)):  
    # 1. 预测偏移量  
    layer_delta_unsig = layer_bbox_embed(layer_hs)  
    # 2. 坐标空间反转与相加  
    layer_outputs_unsig = layer_delta_unsig + inverse_sigmoid(layer_ref_sig)  
    # 3. 压回 0~1 范围  
    outputs_coord_list.append(layer_outputs_unsig.sigmoid())   
    
outputs_coord_list = torch.stack(outputs_coord_list)  
```

**Iterative Bounding Box Refinement 迭代边界框精修机制**

DINO 的 Transformer 解码器（Decoder）默认有 **6 层**。这个 for 循环就是在依次遍历这 6 层

- layer_ref_sig：当前层的参考点，形状为[Batch，300，4]，也就是300个候选框的中心点坐标（x,y）和宽高（w,h）,sig表明他们现在是 0-1 之间的合法坐标
- layer_bbox_embed：当前层的边界框预测头MLP，这是一个包含了几个全连接层的神经网络小模块
- layer_hs，当前层的隐藏状态，形状是[Batch，300，256]，也就是 Transformer 刚刚提取出来的那 300 个高级语义特征


1. 输入特征hs，预测偏移量，layer_delta_unsig形状为[Batch，300，4]，unsig代表是与测量是未经约束的（不在0-1内）
```python
layer_delta_unsig = layer_bbox_embed(layer_hs)
```
2. 虚空空间坐标叠加，inverse_sigmoid，反sigmoid，将layer_ref_sig拉长到虚空空间，并且与偏移量相加
```python
layer_outputs_unsig = layer_delta_unsig + inverse_sigmoid(layer_ref_sig)
```

3. 压缩到 0 -1并且存档，每一层算完后，都会把当前的成果存入列表。当循环 6 次结束后，这个列表里就装了 6 份坐标数据，对应着 300 个框在 6 个阶段的演变过程
```python
outputs_coord_list.append(layer_outputs_unsig.sigmoid())
```

4. 和刚才预测框的坐标一样，分类头也是在 6 层 Decoder 中循环进行的，outputs_class的形状是 `[6, Batch, 300, Num_Classes]`。这意味着它保存了6个阶段里，全部 300个预测框的分类得分
```python
outputs_class = torch.stack(
    [layer_cls_embed(layer_hs) for layer_cls_embed, layer_hs in zip(self.class_embed, hs)])
```

## 后处理

1. 使用了去噪训练，需要剥离去噪部分的输出，只保留正常 Query 的结果
```python
if self.dn_number > 0 and dn_meta is not None:
    outputs_class, outputs_coord_list = dn_post_process(outputs_class, outputs_coord_list, dn_meta, ...)
```

2. 组装最终输出，aux_outputs打包了前五层的所有结果，用于损失计算和梯度下降
- 第 6 层（最后一层）是主力，决定了最终输出什么。
- 前 5 层是辅助（Auxiliary），它们的主要作用是在训练时提供强有力的局部梯度，防止梯度消失，极大加速模型收敛
- 所有的 6 层输出全都参与了损失计算和梯度下降
```python
out = {'pred_logits': outputs_class[-1], 'pred_boxes': outputs_coord_list[-1]}
if self.aux_loss:
    out['aux_outputs'] = self._set_aux_loss(outputs_class, outputs_coord_list)
    
return out
```

