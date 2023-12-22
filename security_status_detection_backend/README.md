# helmet_cloth_detection_system

+ 安全帽与反光衣检测系统

## 简介

+ 实现对于仓库场景下工人、安全帽、反光衣的检测，目前系统的返回值是未穿戴安全帽与反光衣的人数

## 环境配置

1. 创建环境：使用 anaconda 新建基于 python3.10 的虚拟环境，命名为 yolov8，`conda create -n yolov8 python==3.10`，激活虚拟环境，`conda activate yolov8`
2. 安装依赖：使用 pip 安装 requirements.txt 文件中包含的组件依赖，`pip install -r requirements.txt`，再使用 conda 安装 Pytorch，`conda install pytorch==1.11.0 torchvision==0.12.0 cudatoolkit=11.3 -c pytorch`，这里安装了 CUDA11.3 的版本，需按情况更改
3. 启动后台服务：更新根目录下的配置文件 `config.yaml`，开启后台服务，`python app.py`
4. 访问前端页面：浏览器打开 `http://127.0.0.1:5000/index.html`
5. 开启检测功能：点击 "启动" 按钮即可开启检测功能，可在页面观察到实时处理结果 (默认会检测附带的测试视频)，点击 "结束" 按钮即可停止检测

## 前后端对接说明

+ 后端处理逻辑详见 [app.py](./app.py)，前端处理逻辑详见 [static/index.js](./static/index.js)
+ 后端开启着 HTTP 和 WS 服务，支持检测功能的启闭、状态的查询、日志的查询等功能，只有开启了检测功能，后端才会开始拉流和进行检测
+ 后端由拉流线程进行实时拉流，由安全检测线程实时判断安全帽和反光衣的穿戴状态，并定期 (目前是 200ms) 将当前的检测结果和包含检测工人框的帧通过 websocket 推送到前端
+ 服务端拉流链接、MySQL 数据库的连接信息，都配置在根目录下的 [config.yaml](./config.yaml) 文件里
+ 关于日志记录，目前仅在检测状态发生变化时，才会记录日志，包括保存当前帧的截图，并写入数据库中
+ 目前存在的一个问题：广物给的 **RTMP 视频流过于模糊**，检测效果大打折扣，推荐使用 `test02.mp4` 进行演示，效果最佳

## HTTP 服务端接口文档

+ 注：HTTP 服务链接默认为 http://\<ip>:5000/

### GET /index.html, GET /index.css, GET /index.js 返回示例前端代码

+ 略，前端代码详见 [./static](./static)

### POST /enable 连接视频流，并开启检测功能

#### 请求参数

+ 无

#### 响应参数

| 字段 | 类型 | 含义 |
| --- | ---- | ---- |
| `status` | string | `enabled` or `already enabled` |

+ 示例

```json
{
    "status": "enabled"
}
```

### POST /disable 断开视频流，并关闭检测功能

#### 请求参数

+ 无

#### 响应参数

| 字段 | 类型 | 含义 |
| --- | ---- | ---- |
| `status` | string | `disabled` or `not enabled yet` |

+ 示例

```json
{
    "status": "disabled"
}
```

### GET /status 查看当前的检测状态

#### 请求参数

+ 无

#### 响应参数

| 字段 | 类型 | 含义 |
| --- | ---- | ---- |
| `running` | boolean | 当前是否已启用检测功能 |
| `person` | integer | 检测出的工人数量 |
| `no_helmet` | integer | 检测出的未佩戴安全帽的人数 |
| `no_cloth` | integer | 检测出的未穿戴反光衣的人数 |

+ 示例

```json
{
    "running": true,
    "person": 4,
    "no_helmet": 3,
    "no_cloth": 0
}
```

### GET /logs 数据库查询检测日志

#### 请求参数

| 字段 | 位置 | 类型 | 含义 |
| --- | --- | --- | --- |
| `page` | query | int | 分页查询的页数，置空表示第1页 |
| `limit` | query | int | 分页查询的页长，置空表示1页20项，范围为1到50 |
| `base_code` | query | string | 查询特定仓库的日志，置空表示查询所有仓库 |

#### 响应参数

| 字段 | 类型 | 含义 |
| --- | ---- | ---- |
| `page` | int | 当前查询的页数 |
| `limit` | int | 当前查询的页长 |
| `total` | int | 当前查询的数据总数 |
| `data` | array | 查询到的日志列表，按时间逆序排序 |

+ `data` 字段说明 (与数据库的字段保持一致，访问 [test.sql](./test.sql) 查看详情)

| 字段 | 类型 | 含义 |
| --- | ---- | ---- |
| `log_id` | int | 日志编号 |
| `base_code` | string | 仓库编号，目前都为 CSCK |
| `device_id` | string | 设备编号，目前都为 T001 |
| `person` | integer | 检测出的工人数量 |
| `no_helmet` | integer | 检测出的未佩戴安全帽的人数 |
| `no_cloth` | integer | 检测出的未穿戴反光衣的人数 |
| `image_url` | string | 当前检测的本地截图保存路径 |
| `add_nam` | string | 未知，目前都为 python |
| `add_tim` | datetime | 日志记录时间，ISO 格式 |
| `update_nam` | string | 未知，目前都为 python |
| `update_tim` | datetime | 未知，目前同 add_tim |

+ 示例

```json
{
    "page": 1,
    "limit": 20,
    "total": 120,
    "data": [
        {
            "log_id": 120,
            "base_code": "CSCK",
            "device_id": "T001",
            "person": 4,
            "no_helmet": 3,
            "no_cloth": 0,
            "image_url": "images\\2023-06-21\\20230621_015118_904194.jpg",
            "add_nam": "python",
            "add_tim": "2023-06-21T01:51:18+08:00",
            "update_nam": "python",
            "update_tim": "2023-06-21T01:51:18+08:00"
        },
        {
            "log_id": 119,
            "base_code": "CSCK",
            "device_id": "T001",
            "person": 3,
            "no_helmet": 2,
            "no_cloth": 0,
            "image_url": "images\\2023-06-21\\20230621_015117_826262.jpg",
            "add_nam": "python",
            "add_tim": "2023-06-21T01:51:17+08:00",
            "update_nam": "python",
            "update_tim": "2023-06-21T01:51:17+08:00"
        }
        // ...
    ]
}
```

## WebSocket 服务端接口文档

+ 注：WebSocket 服务链接默认为 ws://\<ip>:5001/

### 客户端推送至服务端

+ 暂无，直接请求上述链接，建立 websocket 链接，等待来自服务端推送的消息即可

```js
let ws = new WebSocket('ws://localhost:5001');
ws.onmessage = ({ data }) => {
    let obj = JSON.parse(data);
    // ...
};
```

### 服务端推送至客户端

+ 通用字段

| 字段 | 类型 | 含义 |
| --- | ---- | ---- |
| `type` | string | 用于区分推送的消息类型，具体见以下文档 |

#### image_and_status 类型的消息

+ 当检测功能开启时，服务器会每隔 100ms 将当前检测结果与当前图像帧推送给客户端

| 字段 | 类型 | 含义 |
| --- | ---- | ---- |
| `type` | string | `image_and_status` |
| `image` | string | 图像的 base64 编码 |
| `person` | integer | 检测出的工人数量 || `no_helmet` | integer | 检测出的未佩戴安全帽的人数 |
| `no_cloth` | integer | 检测出的未穿戴反光衣的人数 |

+ 示例

```json
{
    "type": "image_and_status",
	"image": "...",
    "person": 4,
    "no_helmet": 2,
    "no_cloth": 0
}
```

#### status_changed 类型的消息

+ 当后台检测出的状态发生变更时，服务器会将变更的状态推送给客户端，可作为实时日志展示

| 字段 | 类型 | 含义 |
| --- | ---- | ---- |
| `type` | string | `status_changed` |
| `person` | integer | 检测出的工人数量 |
| `no_helmet` | integer | 检测出的未佩戴安全帽的人数 |
| `no_cloth` | integer | 检测出的未穿戴反光衣的人数 |
| `created_at` | datetime | 状态变更的时间，ISO 格式 |

+ 示例

```json
{
    "type": "status_changed",
    "person": 4,
    "no_helmet": 3,
    "no_cloth": 0,
    "created_at": "2023-06-21T02:13:09+08:00"
}
```

## ChangeLog

+ 202305??：实现初始版本，初次交付
+ 20230620：完善检测逻辑，更新后端，支持日志数据库记录，支持实时日志推送功能，新增一些新的查询接口
