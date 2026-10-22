import os
import json
import torch
from torch.utils.data import Dataset
from PIL import Image
import torchvision.transforms.v2 as T
import torchvision.transforms.v2.functional as F
from pathlib import Path


UAVDT_CATEGORIES = {
    'car': 1,
    'truck': 2,
    'bus': 3,
}

NUM_CLASSES = 3

class UAVDTDetectionDataset(Dataset):
    def __init__(
        self,
        data_root: str,
        ann_dir: str,
        mode: str = "train",
        clip_len: int = 16,
        frame_sample_rate: int = 1,
        img_size: int = 224,
    ):

        self.data_root = Path(data_root)
        self.ann_dir = Path(ann_dir)
        self.mode = mode
        self.clip_len = clip_len
        self.frame_sample_rate = frame_sample_rate
        self.img_size = img_size
        
        # 数据增强变换（训练/验证）
        if mode == "train":
            self.transforms = self._build_train_transforms()
        else:
            self.transforms = self._build_val_transforms()
        
        # 存储所有标注文件路径的列表
        self.samples = self._load_annotation_list()
        
        print(f"Loaded {len(self.samples)} samples for {mode} split")

    def _build_train_transforms(self):
        return T.Compose([
            T.Resize((self.img_size, self.img_size)),
            T.RandomHorizontalFlip(p=0.5), #随机水平翻转
            T.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1), # 颜色抖动
            T.ToImage(),
            T.ToDtype(torch.float32, scale=True),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
    
    def _build_val_transforms(self): # 无随机操作
        return T.Compose([
            T.Resize((self.img_size, self.img_size)),
            T.ToImage(),
            T.ToDtype(torch.float32, scale=True),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
    
    #加载标注文件的路径列表
    def _load_annotation_list(self):

        if not self.ann_dir.exists():
            print(f"Warning: Annotation directory {self.ann_dir} does not exist")
            return []


        ann_files = list(self.ann_dir.glob("*.json")) # glob会返回该目录下所有 .json文件的 Path对象生成器，list将生成器转换为列表
        ann_files.sort()  # 每次glob不保证有序，所以这里进行排序
        
        return ann_files # 返回json文件的路径列表

    '''
        
        - 将标签json文件的内容解析出来，保存到一个字典中（图片数据路径、边界框list、标签list、追踪id、原始图片高和宽）
        - ann_path是一个json的路径
    '''
    def _parse_annotation(self, ann_path: Path) -> dict:
        # 读取json文件，用 json.load()解析为 Python 字典
        with open(ann_path, 'r') as f:
            ann = json.load(f)

        # 提取出图片原始的高度和宽度
        orig_h = ann['size']['height']
        orig_w = ann['size']['width']
        
        boxes = [] # 边界框坐标
        labels = [] # 类别
        track_ids = [] # 跟踪id

        # 遍历标注中的每个物体对象
        for obj in ann.get('objects', []):
            # 获取物体的类别，并转化为小写，跳过未知类别
            class_title = obj.get('classTitle', '').lower()
            if class_title not in UAVDT_CATEGORIES:
                continue
            
            # 获取边界框的两个对角点的两个坐标
            points = obj.get('points', {}).get('exterior', [])
            if len(points) != 2:
                continue  # 如果不是两个点则跳过

            # 取出两个对焦点坐标
            x1, y1 = points[0]
            x2, y2 = points[1]
            
            # 验证必须是有效的边界框
            if x1 >= x2 or y1 >= y2:
                continue

            # 添加有效的边界框，将类别映射为类别id添加到label列表中，边界框和类别一一对应
            boxes.append([x1, y1, x2, y2])
            labels.append(UAVDT_CATEGORIES[class_title])
            
            # 遍历物体的标签，查找 'target id' 标签，获取跟踪ID，默认-1表示无跟踪
            track_id = -1
            for tag in obj.get('tags', []):
                if tag.get('name') == 'target id':
                    track_id = tag.get('value', -1)
                    break
            track_ids.append(track_id)
        
        # 向上两级目录，得到 split目录（如 data/uavdt/train）
        split_dir = ann_path.parent.parent
        # 获取文件名不带扩展名（M0203_img000001）
        ann_filename = ann_path.stem

        # # 去除 .json后缀
        img_name = ann_filename.replace('.json', '')
        
        # 构建图像目录路径
        img_dir = split_dir / 'img'
        # 拼接出候选图像路径
        img_path = img_dir / ann_filename
        

        if not img_path.exists():
            img_name_clean = ann_filename.replace('.jpg', '').replace('.png', '')
            for ext in ['.jpg', '.png', '.bmp']:
                img_path = img_dir / (img_name_clean + ext)
                if img_path.exists():
                    break
        
        return {
            'image_path': str(img_path) if img_path.exists() else None,
            'boxes': boxes,
            'labels': labels,
            'track_ids': track_ids,
            'orig_size': [orig_h, orig_w],
        }


    '''
        1. 加载视频片段，并应用变换
        2. 以 img_path 标准帧为中心，加载相邻帧，clip_len为扩展帧个数
        3. 返回 torch.Tensor [C=3, T=8, H=224, W=224]
    '''
    def _load_and_transform_frames(self, img_path: str) -> torch.Tensor:

        # 图片文件不存在则返回全黑张量
        if img_path is None or not os.path.exists(img_path):
            # Return black frames if image not found
            frames = torch.zeros(3, self.clip_len, self.img_size, self.img_size)
            return frames
        
        try:
            # 尝试用 PIL 打开图片并转换为 RGB
            img = Image.open(img_path).convert('RGB')
        except Exception as e:
            # 出错时打印错误并创建空白 RGB 图片
            print(f"Error loading image {img_path}: {e}")
            img = Image.new('RGB', (self.img_size, self.img_size))
        
        # 获取文件目录名和文件名
        frame_dir = os.path.dirname(img_path)
        frame_name = os.path.basename(img_path)
        
        # 提取帧编号，从 img000001.jpg中提取 000001
        import re
        match = re.search(r'(\d+)', frame_name) #r'(\d+)'匹配连续数字
        if match:
            frame_idx = int(match.group(1)) # 帧编号 1（转为整数）
            prefix = frame_name[:match.start()] # 数字前的部分 img
            ext = frame_name[match.end():] #数字后的部分，文件扩展名 .jpg
        else:
            # 用相同的参考帧复制 clip_len次
            frames = [img] * self.clip_len
            # 立刻返回变换结果
            return self._apply_transforms(frames)
        
        # 图片帧列表，以参考帧为中心，扩展 clip_len个帧
        frames = []
        for i in range(self.clip_len):
            # 以参考帧为中心，对称扩展
            offset = (i - self.clip_len // 2) * self.frame_sample_rate
            idx = frame_idx + offset

            # 防止索引为负或0
            if idx < 1:
                idx = 1

            # 拼接完整路径
            frame_name = f"{prefix}{idx:06d}{ext}"
            frame_path = os.path.join(frame_dir, frame_name)

            # 遇到任何异常，都用参考帧复制
            try:
                if os.path.exists(frame_path):
                    frame = Image.open(frame_path).convert('RGB')
                else:
                    frame = img.copy()  # Use reference frame as fallback
            except:
                frame = img.copy()
            
            frames.append(frame)

        # 调用另一个方法对帧列表进行变换，返回张量
        return self._apply_transforms(frames)

    """
        接收PIL图片帧列表，对帧进行变换
        
        Args:
            frames: 帧列表
        
        Returns:
            Tensor: [C, T, H, W]
    """
    def _apply_transforms(self, frames: list) -> torch.Tensor:

        # 张量列表
        frame_tensors = []
        for frame in frames:
            frame_tensor = F.to_image(frame) # 将 PIL 图片转为 PyTorch 张量
            frame_tensor = F.to_dtype(frame_tensor, dtype=torch.float32, scale=True) # 	转为 float32 并归一化到 [0,1]
            frame_tensors.append(frame_tensor) # 将处理后的张量添加到列表
        
        # 每个元素是 [C, H, W]，在新增的维度 0 上堆叠，结果形状：[T, C, H, W]
        clip = torch.stack(frame_tensors, dim=0)
        
        # 调整所有帧的尺寸
        clip = F.resize(clip, [self.img_size, self.img_size])
        
        # 归一化（标准化）：每通道像素值近似标准正态分布（均值0，方差1）
        mean = [0.485, 0.456, 0.406]
        std = [0.229, 0.224, 0.225]
        for c in range(3):
            clip[:, c, :, :] = (clip[:, c, :, :] - mean[c]) / std[c]
        
        # 转换为 [C, T, H, W]
        clip = clip.permute(1, 0, 2, 3)
        
        return clip
    '''
        - 将边界框归一化到 [0,1] 范围并转换为中心坐标格式
    
    
    '''
    def _normalize_boxes(self, boxes: list, orig_size: list) -> torch.Tensor:
        # 没有边界框，则创建空张量
        if len(boxes) == 0:
            return torch.zeros(0, 4)
        
        orig_h, orig_w = orig_size # 原始图片尺寸
        scale_factor = torch.tensor([orig_w, orig_h, orig_w, orig_h], dtype=torch.float32) # 缩放因子
        
        boxes_tensor = torch.tensor(boxes, dtype=torch.float32)  # 将边界框列表转为张量：[N, 4]，N是边界框数量
        
        # 从角点坐标转换为中心坐标格式 Convert (x1, y1, x2, y2) to (cx, cy, w, h)
        cx = (boxes_tensor[:, 0] + boxes_tensor[:, 2]) / 2
        cy = (boxes_tensor[:, 1] + boxes_tensor[:, 3]) / 2
        w = boxes_tensor[:, 2] - boxes_tensor[:, 0]
        h = boxes_tensor[:, 3] - boxes_tensor[:, 1]

        # 重新堆叠，结果形状：[N, 4]，每行是 [cx, cy, w, h]
        boxes_converted = torch.stack([cx, cy, w, h], dim=1)
        
        # 归一化到 0-1 范围内
        boxes_normalized = boxes_converted / scale_factor
        
        # 裁剪到 [0, 1] 范围内，确保归一化后的坐标不会超出范围
        boxes_normalized = torch.clamp(boxes_normalized, 0.0, 1.0)
        
        return boxes_normalized # 返回归一化后的边界框张量 [N, 4]
    
    def __len__(self) -> int:
        # samples 存储所有标注文件路径的列表，返回样本数量
        return len(self.samples)


    '''
        - 实现索引访问 dataset[i]
        - 接收索引index，返回（frames，targets）元组
    '''
    def __getitem__(self, index: int) -> tuple:

        # 1. 根据索引获取标注文本 .json 路径
        ann_path = self.samples[index]
        # 2. 解析json文件，返回字典，包括：image_path, boxes, labels, track_ids, orig_size
        ann = self._parse_annotation(ann_path)
        
        # 3. 根据对应的图片路径，加载和变换帧，返回[C, T, H, W]
        frames = self._load_and_transform_frames(ann['image_path'])
        
        # 4. 归一化边界框，归一化后的 (cx, cy, w, h)格式张量，形状 [N, 4]
        boxes = self._normalize_boxes(ann['boxes'], ann['orig_size'])

        # 5. 将类别标签转化为一维张量
        labels = torch.tensor(ann['labels'], dtype=torch.int64) if len(ann['labels']) > 0 else torch.zeros(0, dtype=torch.int64)

        # 6. 同样逻辑处理跟踪id，一位张量
        track_ids = torch.tensor(ann['track_ids'], dtype=torch.int64) if len(ann['track_ids']) > 0 else torch.zeros(0, dtype=torch.int64)
        
        # 索引作为图片id
        image_id = index
        
        targets = {
            'boxes': boxes, # [N, 4] ，N代表一张图中有 N 个目标
            'labels': labels, # [N]
            'image_id': image_id, # int 值
            'orig_size': torch.tensor(ann['orig_size'], dtype=torch.int64), # [2]，原始尺寸 [H, W]
            'track_ids': track_ids, # [N]
        }

        # 给定一个索引，返回单个样本的堆叠帧张量，和对应的标签信息，返回元组：(frames, targets)
        return frames, targets


class UAVDTDetectionDatasetMultiClip(UAVDTDetectionDataset):
    """
    Extended UAVDT dataset that creates multi-frame clips for tracking.
    
    Instead of single frames, this creates clips of `clip_len` consecutive frames,
    with annotations from the last frame as the target.
    """
    
    def __init__(
        self,
        data_root: str,
        ann_dir: str,
        mode: str = "train",
        clip_len: int = 16,
        frame_sample_rate: int = 1,
        img_size: int = 224,
    ):
        super().__init__(data_root, ann_dir, mode, clip_len, frame_sample_rate, img_size)
    
    def _load_annotation_list(self):
        """Load annotations and group them by sequence for multi-clip creation."""
        # Use the same single-frame approach for now
        # Multi-clip can be added later for tracking
        return super()._load_annotation_list()
