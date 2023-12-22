# security_status_detection

## 1本项目完成的具体工作内容如下

### 1.1算法实现

![img](https://github.com/wztsir/security_status_detection/blob/main/img/clip_image002.png?raw=true)

l 结构设计： 在业界模型比较的基础上，选择了以工业界广泛应用的轻量级YOLO系列模型为设计和优化基础，以在满足工业应用速度需求的同时提高模型预测精度。

l 数据集增强与标签分配： 收集了包含10,000多张图像的数据集，并完成了1,000张图像的自主标注工作，以确保数据集的质量和多样性。

l 训练策略： 采用了辅助训练头与重参数化的策略，以提升模型对困难样本的召回率和增强模型的表征能力，以更好地满足实际应用中的需求。

### 1.2平台搭建

前端使用三件套技术，后端使用flask框架

l 安全装备检测系统： 设计了一个用户友好的平台，用户可选择上传视频、RTSP链接或图片，并获取相应的检测结果，以确保工地安全装备的合规性。

l 火灾烟雾检测系统： 用户可选择相应的图片目录，平台将对所有图片进行检测并显示检测结果，旨在帮助用户及时发现火灾和烟雾情况，从而采取有效措施确保工地安全。

 

## 2本项目成果创新

1.本项目以工业界中应用广泛的YOLO系列的轻量化模型为基础进行设计优化，预测精度高，泛化能力强。

采用MPConv模块通过两个分支分别用卷积以及池化操作进行下采样，有效缩减特征图的尺寸从而减少运算量和参数量，防止过拟合、提高泛化能力。

采用Mosaic、模糊、色域变换等多种数据增强的方式扩充训练数据，提升模型在复杂的工业环境中检测能力的鲁棒性。

现有模型难以检测识别数据集中未曾出现过的场景，泛化性不足。

2.采用ELAN模块，使得模型学习到更加丰富的表达，提高网络提取特征能力的同时，也保证了学习的效率。

​    采用重参数化的思想，在训练阶段将卷积层分解为可线性叠加的多个卷积层从而增强模型的表达能力，在推理阶段将参数合并，不增加推理延时。

​    采用辅助训练头的思想，在训练过程中利用辅助训练头提升主干网络召回目标的能力，提升模型对困难样本的召回率。

  解决检测对象多样、类内差异大、无法模拟现实中复杂的检测场景的问题。

3.采用SPPCSPC模块通过池化的方式获取不同感受野的特征，增大感受野，使得模型适应不同的分辨率图像。通过四条分支学习四种尺度的特征，提升模型同时区分大目标及小目标的能力。

​    采用辅助训练头策略，辅助头通常使用更小的感受野和更高的分辨率，以更好地适应目标的尺寸和形状变化。

  现有模型对于小目标的检测准确度低。

4.采用近邻位置分配策略以及simOTA结合的思想，为每个真实值动态分配正样本，使模型能够动态高效地利用标注信息学习。

​    采用TensorRT推理部署框架进行加速，进一步提升模型推理速度。

 

## 3本项目成果展示

### 3.1数据集构造（收集10,000多张，标注1000多张）

![img](https://github.com/wztsir/security_status_detection/blob/main/img/clip_image004.jpg?raw=true)

![img](https://github.com/wztsir/security_status_detection/blob/main/img/clip_image006.jpg?raw=true)



### 3.2平台展示

![img](https://github.com/wztsir/security_status_detection/blob/main/img/clip_image008.jpg?raw=true)

 

​																							图1 平台开始界面

![img](https://github.com/wztsir/security_status_detection/blob/main/img/clip_image010.jpg?raw=true)

​																					图2 安全装备检测系统界面

![img](https://github.com/wztsir/security_status_detection/blob/main/img/clip_image012.jpg?raw=true)

​																	图3 安全装备检测系统-视频/rtsp检测界面

![img](https://github.com/wztsir/security_status_detection/blob/main/img/clip_image014.jpg?raw=true)

​																	图4 安全装备检测系统-图片检测界面

![img](https://github.com/wztsir/security_status_detection/blob/main/img/clip_image016.jpg?raw=true)

​																图5 火灾烟雾检测系统-图片检测界面

