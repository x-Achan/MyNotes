# Linear
-----
采样偏移预测 ：预测每个 query 在多尺度特征图上的采样偏移
Linear层，本质就是仿射变换 y=Wx+b，将输入特征映射到新空间，在 Deformable Attention 中偏移量预测器，从 query 预测采样位置偏移

Linear 层就负责回答这个问题：
- 输入：当前 query 的语义特征（256维）
- 输出：**16 个建议采样点的偏移坐标**（每个点有 x, y 两个值）

这些偏移是 **可学习的** —— 网络通过训练自动学会 **对不同目标（如车、人）关注不同的局部区域**


```python
self.sampling_offsets = nn.Linear(embed_dim, num_heads*num_levels*num_points*2)
```

