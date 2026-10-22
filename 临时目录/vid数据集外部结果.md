
| 排名  | 方法                    | 类型             | Backbone    | public test-dev mAP50-95 / mAP | 全局 mAP50     | 论文另报指标                           | 结果来源          |
| --- | --------------------- | -------------- | ----------- | ------------------------------ | ------------ | -------------------------------- | ------------- |
| 1   | Proposed              | 时序             | ResNet-101  | **0.4426**                     | —            | [APs@0.5](mailto:APs@0.5)=0.2319 | 公开 manuscript |
| 2   | LSTFE                 | 时序             | ResNet-101  | **0.4186**                     | —            | [APs@0.5](mailto:APs@0.5)=0.2179 | 公开 manuscript |
| 3   | TransVOD              | Transformer 时序 | ResNet-101  | **0.3969**                     | —            | [APs@0.5](mailto:APs@0.5)=0.1962 | 公开 manuscript |
| 4   | MEGA                  | 时序记忆           | ResNet-101  | **0.3933**                     | —            | [APs@0.5](mailto:APs@0.5)=0.2056 | 公开 manuscript |
| 5   | SELSA                 | 时序语义聚合         | ResNet-101  | **0.3756**                     | —            | [APs@0.5](mailto:APs@0.5)=0.1953 | 公开 manuscript |
| 6   | FPN                   | 单帧             | ResNet-101  | **0.3712**                     | —            | [APs@0.5](mailto:APs@0.5)=0.1972 | 公开 manuscript |
| 7   | RDN                   | 时序             | ResNet-101  | **0.3703**                     | —            | [APs@0.5](mailto:APs@0.5)=0.1867 | 公开 manuscript |
| 8   | FGFA                  | 光流/特征时序        | ResNet-101  | **0.3526**                     | —            | [APs@0.5](mailto:APs@0.5)=0.1740 | 公开 manuscript |
| 9   | Single Frame Baseline | 单帧             | ResNet-101  | **0.3362**                     | —            | [APs@0.5](mailto:APs@0.5)=0.1790 | 公开 manuscript |
| 10  | DFF                   | 光流时序           | ResNet-101  | **0.3316**                     | —            | [APs@0.5](mailto:APs@0.5)=0.1680 | 公开 manuscript |
| 11  | Faster R-CNN          | 单帧             | ResNet-101  | **0.3180**                     | —            | [APs@0.5](mailto:APs@0.5)=0.1760 | 公开 manuscript |
| 12  | TA-GRU YOLOv7         | 时序，2 帧         | YOLOv7      | **0.2457**                     | **0.4879**   | —                                | 正式论文          |
| 13  | TA-GRU YOLOX          | 时序，2 帧         | YOLOX       | **0.1941**                     | **0.4059**   | —                                | 正式论文          |
| 14  | YOLOv7 baseline       | 单帧             | YOLOv7      | **0.1871**                     | **0.4026**   | —                                | 正式论文          |
| 15  | YOLOX baseline        | 单帧             | YOLOX       | **0.1686**                     | **0.3562**   | —                                | 正式论文          |
| 16  | TA-GRU YOLOv7-tiny    | 时序，2 帧         | YOLOv7-tiny | 约 **0.165***                   | 约 **0.296*** | —                                | 正式论文          |
| 17  | YOLOv7-tiny baseline  | 单帧             | YOLOv7-tiny | 约 **0.103***                   | 约 **0.212*** | —                                | 正式论文          |
| 18  | YOLOv10s baseline     | 单帧             | YOLOv10s    | **0.149**                      | **0.298**    | —                                | 你的实验          |
| 19  | UC-Mamba-ST-Pool2     | 时序             | YOLOv10s    | **0.161**                      | **0.312**    | —                                | 你的实验          |
|     |                       |                |             |                                |              |                                  |               |
