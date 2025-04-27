# YOLOv5 🚀 by Ultralytics, GPL-3.0 license
"""
Auto-batch utils
"""

from copy import deepcopy

import numpy as np
import torch
from torch.cuda import amp

from utils.general import LOGGER, colorstr
from utils.torch_utils import profile


def check_train_batch_size(model, imgsz=640):
    # Check YOLOv5 training batch size
    with amp.autocast():
        return autobatch(deepcopy(model).train(), imgsz)  # compute optimal batch size


def autobatch(model, imgsz=640, fraction=0.9, batch_size=16):
    # Automatically estimate best batch size to use `fraction` of available CUDA memory
    # Usage:
    #     import torch
    #     from utils.autobatch import autobatch
    #     model = torch.hub.load('ultralytics/yolov5', 'yolov5s', autoshape=False)
    #     print(autobatch(model))

    prefix = colorstr('AutoBatch: ')
    LOGGER.info(f'{prefix}Computing optimal batch size for --imgsz {imgsz}')
    """
    # 方案1：转换为列表后取第一个（不推荐，因为会创建完整列表）
    device = list(model.parameters())[0].device
    
    # 方案2：使用模型的device属性（不是所有模型都有这个属性）
    device = model.device  # 可能会报错
    
    # 方案3：使用next（推荐，当前使用的方案）
    device = next(model.parameters()).device
    """
    device = next(model.parameters()).device  # get model device
    if device.type == 'cpu':
        LOGGER.info(f'{prefix}CUDA not detected, using default CPU batch-size {batch_size}')
        return batch_size

    d = str(device).upper()  # 'CUDA:0'
    properties = torch.cuda.get_device_properties(device)  # device properties
    t = properties.total_memory / 1024 ** 3  # (GiB)
    r = torch.cuda.memory_reserved(device) / 1024 ** 3  # (GiB)
    a = torch.cuda.memory_allocated(device) / 1024 ** 3  # (GiB)
    f = t - (r + a)  # free inside reserved
    LOGGER.info(f'{prefix}{d} ({properties.name}) {t:.2f}G total, {r:.2f}G reserved, {a:.2f}G allocated, {f:.2f}G free')
    # 通过不同bs拟合一条bs-占显存曲线，从而估算占显存0.9(fraction)时候bs设置为多少
    batch_sizes = [1, 2, 4, 8, 16]
    try:
        img = [torch.zeros(b, 3, imgsz, imgsz) for b in batch_sizes]
        y = profile(img, model, n=3, device=device)     # (shape, time, memory)
    except Exception as e:
        LOGGER.warning(f'{prefix}{e}')

    y = [x[2] for x in y if x]  # memory [2]
    batch_sizes = batch_sizes[:len(y)]
    p = np.polyfit(batch_sizes, y, deg=1)  # first degree polynomial fit
    b = int((f * fraction - p[1]) / p[0])  # y intercept (optimal batch size)
    LOGGER.info(f'{prefix}Using batch-size {b} for {d} {t * fraction:.2f}G/{t:.2f}G ({fraction * 100:.0f}%)')
    return b
