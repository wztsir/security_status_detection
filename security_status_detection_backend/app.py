from flask import Flask, request
from flask_cors import CORS
import threading
import asyncio
from websockets.server import serve, WebSocketServerProtocol
import json
import cv2
import base64
import numpy as np
import os
import time
from utils.detect import detect_img, DetectionResult
from utils.utilities import Atomic, MySQLConnection, get_remote_addr
from utils.dao import query_detection_logs, save_screenshot_and_addto_database
from utils.fireDetect import fire_detection  # 请替换成你的模块名称

import yaml
import typing

# 一些服务器参数
HTTP_PORT = 5000
WS_PORT = 5001
PUSH_SLEEP = 0.2  # 0.2s

# 读取配置文件，并连接数据库
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)
stream_source = str(config['stream']['source'])
stream_fps = float(config['stream']['fps'])
mysql = config['mysql']
dbconn = MySQLConnection(host=mysql['host'], port=mysql['port'], user=mysql['user'], password=mysql['password'],
                         database=mysql['database'])

# 初始化 Flask 服务器
app = Flask(
    __name__,
    static_url_path='',
    static_folder='./static',
    template_folder='./templates',
)
app.config['JSON_SORT_KEYS'] = False
CORS(app)

# 初始化 WebSocket 客户端集合
websocket_clients = set()

# 全局维护的启动标志
ALLOW_RUNNING = Atomic(False)
th1 = None  # 拉流线程
th2 = None  # 检测线程

# 全局维护的当前帧
global_frame = Atomic(None)
global_pulling = Atomic(False)

# 全局维护的检测结果
global_detect_frame = Atomic(None)
global_detection_result = Atomic(DetectionResult())
database_recording_lock = threading.Lock()
global_last_detection_result = Atomic(DetectionResult())


def read_image_as_base64(file_path):
    with open(file_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return encoded_string


def get_image_paths_from_folder(folder_path):
    image_paths = []
    supported_formats = ['.bmp', '.jpg', '.jpeg', '.png', '.tif', '.tiff', '.dng']

    for file_name in os.listdir(folder_path):
        if os.path.isfile(os.path.join(folder_path, file_name)):
            _, file_extension = os.path.splitext(file_name)
            if file_extension.lower() in supported_formats:
                image_paths.append(os.path.join(folder_path, file_name))

    return image_paths


@app.post('/detect_fire')
def detect_fire():
    try:
        # 获取请求中的数据
        data = request.json
        source = data.get('source', '../inference/images')
        output_folder = '../output'
        conf_thres = data.get('conf_thres', 0.4)
        iou_thres = data.get('iou_thres', 0.5)

        # 调用 fire_detection 函数
        fire_detection(source=source, output_folder=output_folder, conf_thres=conf_thres, iou_thres=iou_thres)

        # 从output_folder中获取所有图片文件路径
        image_paths = get_image_paths_from_folder(output_folder)

        # 读取图片并以 base64 编码形式返回
        images_data = []
        for image_path in image_paths:
            image_base64 = read_image_as_base64(image_path)
            images_data.append({'path': image_path, 'data': image_base64})

        # 返回成功的响应，并附带图片数据列表
        return {'status': 'success', 'images_data': images_data}
    except Exception as ex:
        # 返回错误的响应
        return {'status': 'error', 'message': str(ex)}, 500

@app.post('/detect_image')
def detect_image_route():
    try:
        # 从请求中获取图像数据（这里假设请求是通过 form-data 发送的图像）
        image_file = request.json['image']
        image_data = base64.b64decode(image_file)
        nparr = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        # 调用图像检测函数
        detect_frame, result = detect_img(frame)  # !!! 穿戴安全检测，返回检测到的类别、以及画上检测框后的帧

        image_data = None
        resized_frame = cv2.resize(detect_frame, (800, 450))  # resize 绘制了检测框的帧图
        success, buffer = cv2.imencode('.jpg', resized_frame)
        if success:
            image_data = base64.b64encode(buffer).decode('utf-8')  # base64 image data for response

        # 3. respond data to websocket client
        return {'type': 'image_and_status', 'image': image_data, 'person': result.person, 'no_helmet': result.no_helmet,
                'no_cloth': result.no_cloth}

    except Exception as ex:
        print("[ERRO] detect_image_route:", ex)
        return {'status': 'error', 'message': str(ex)}, 500


@app.get('/status')
def get_detection_status():
    """
    查看当前的检测状态，包括是否已启用检测功能、以及当前的安全检测结果
    """
    running = ALLOW_RUNNING.get()
    result = global_detection_result.get()
    return {
        'running': running,
        'person': 0 if not running else result.person,
        'no_helmet': 0 if not running else result.no_helmet,
        'no_cloth': 0 if not running else result.no_cloth,
    }


@app.post('/enable')
def enable_detection():
    """
    启用检测，创建一个拉流线程来连接视频流，并创建一个检测线程来进行安全检测
    """
    if ALLOW_RUNNING.get():
        return {'status': 'already enabled'}

    global th1
    global th2
    ALLOW_RUNNING.set(True)
    th1 = threading.Thread(target=pull_stream_thread)
    th1.start()
    th2 = threading.Thread(target=detection_thread)
    th2.start()
    return {'status': 'enabled'}


@app.post('/disable')
def disable_detection():
    """
    禁用检测，关闭拉流线程断开视频流链接，并关闭一个检测线程结束安全检测
    """
    if not ALLOW_RUNNING.get():
        return {'status': 'not enabled yet'}

    global th1
    global th2
    ALLOW_RUNNING.set(False)
    if th1 is not None:
        th1.join()
        th1 = None
    if th2 is not None:
        th2.join()
        th2 = None
    return {'status': 'disabled'}


@app.get('/logs')
def get_detection_logs():
    """
    数据库查询检测日志，支持分页查询、按仓库编号查询，并返回查询结果
    """
    given_page = request.args.get('page', default='1', type=int)
    given_page = max(1, int(given_page))
    given_limit = request.args.get('limit', default='20', type=int)
    given_limit = max(1, min(50, int(given_limit)))
    given_base_code = request.args.get('base_code', default='', type=str)

    try:
        # 分页查询，不提供 base_code 则查询所有仓库，否则查询指定仓库
        count, logs = query_detection_logs(dbconn=dbconn, base_code=given_base_code, page=given_page, limit=given_limit)
    except Exception as ex:
        print("[ERRO] get_detection_logs: query logs from database:", ex)
        return {'status': 'error', 'code': 500, 'info': str(ex)}, 500

    logs = [{
        'log_id': log.log_id,
        'base_code': log.base_code,
        'device_id': log.device_id,
        'person': log.person,
        'no_helmet': log.no_helmet,
        'no_cloth': log.no_cloth,
        'image_url': log.image_url,
        'add_nam': log.add_nam,
        'add_tim': log.add_tim.isoformat(),
        'update_nam': log.update_nam,
        'update_tim': log.update_tim.isoformat(),
    } for log in logs]

    return {
        'page': given_page,
        'limit': given_limit,
        'total': count,
        'data': logs,
    }


def pull_stream_thread():
    """
    拉流线程，支持离线视频或视频流，并将当前帧实时推送到全局的 global_frame、global_pulling 变量
    """
    cap = cv2.VideoCapture(stream_source)
    while ALLOW_RUNNING.get():
        if not cap.isOpened():
            print('[INFO] pull_stream_thread: cap is closed')
            break  # 视频流已被关闭，结束线程
        time.sleep(1 / stream_fps)
        success, frame = cap.read()
        if not success:
            print('[ERRO] pull_stream_thread: cap.read failed')
            break  # 读取视频流失败，结束线程

        # print(f'[INFO] frame_size: {frame.size()}')
        global_frame.set(frame)  # save the current frame to global
        global_pulling.set(True)

    # global_frame.set(None)  # do not reset frame
    global_pulling.set(False)  # set pulling to false
    print('[INFO] pull_stream_thread exited')


def detection_thread():
    """
    安全检测线程，获取当前全局帧 global_frame 进行安全检测
    """
    frame_has_existed_once = False  # 曾经是否存在过正常帧
    while ALLOW_RUNNING.get():
        frame = global_frame.get() if global_pulling.get() else None  # 如果当前正在拉流则获取当前帧，否则未空
        if frame is None:
            if frame_has_existed_once:
                print('[INFO] detection_thread: Got unexpected empty frame.')
                break  # 期望获取到正常的帧，但当前帧为帧、或者当前不在拉流，结束线程
            time.sleep(PUSH_SLEEP)
            continue

        frame_has_existed_once = True
        try:
            frame, result = detect_img(frame)  # !!! 穿戴安全检测，返回检测到的类别、以及画上检测框后的帧
            # print(f'[INFO] result: {result}')
            global_detect_frame.set(frame)  # save the drawn frame to global
            global_detection_result.set(result)
        except Exception as ex:
            print('[ERRO] detection_thread:', ex)

    global_detect_frame.set(None)  # reset detection frame
    global_detection_result.set(DetectionResult())  # reset detection result
    print('[INFO] press_line_detection_thread exited')


async def websocket_handler(client: WebSocketServerProtocol, remote_addr: typing.Union[str, typing.Any]):
    """
    单个 WebSocket 客户端的连接处理器，轮询全局的帧和检测结果来推送给客户端，并由单个连接来将检测日志写入数据库中
    """
    while not client.closed:
        await asyncio.sleep(PUSH_SLEEP)  # 每次推送都需要等待 PUSH_SLEEP 秒
        if not ALLOW_RUNNING.get():
            continue  # 如果当前的检测功能没开启，则继续等待

        # 1. get current detection results
        frame = global_frame.get()
        if frame is None or not global_pulling.get():
            continue  # 如果当前帧为空、或当前不在拉流，则继续等待
        result = global_detection_result.get()
        detect_frame = global_detect_frame.get()
        if detect_frame is None:
            continue  # 当前检测结果未出来，继续等待

        # 2. resize current frame and encode it to base64
        image_data = None
        resized_frame = cv2.resize(detect_frame, (800, 450))  # resize 绘制了检测框的帧图
        success, buffer = cv2.imencode('.jpg', resized_frame)
        if success:
            image_data = base64.b64encode(buffer).decode('utf-8')  # base64 image data for response

        # 3. respond data to websocket client
        obj = {'type': 'image_and_status', 'image': image_data, 'person': result.person, 'no_helmet': result.no_helmet,
               'no_cloth': result.no_cloth}
        # print(f'[INFO] Respond "{result}" to client "{remove_addr}".')
        try:
            await client.send(json.dumps(obj))
        except Exception as ex:
            print("[ERRO] websocket_thread: respond to client:", ex)

        # 4. check whether status are changed or not
        with database_recording_lock:  # 加互斥锁，使得当前只有一个连接能够操作数据库
            last_detection_result = global_last_detection_result.get()
            if not last_detection_result.equals(result):  # TODO 需要过滤检测有误的离群点
                print('[INFO] Status changed, result: {}->{}, for client "{}".'.format(last_detection_result, result,
                                                                                       remote_addr))
                global_last_detection_result.set(result)  # 更新 last 状态为最新的状态
                person, no_helmet, no_cloth = result.person, result.no_helmet, result.no_cloth

                # 将变化的状态保存到数据库
                inserted = save_screenshot_and_addto_database(dbconn=dbconn, person=person, no_helmet=no_helmet,
                                                              no_cloth=no_cloth, frame=resized_frame)
                if inserted is None:
                    print('[ERRO] save_screenshot_and_addto_database failed')

                # 将变化的状态推送给所有客户端
                async def send_to_all_clients():
                    for client in websocket_clients:
                        obj = {'type': 'status_changed', 'person': inserted.person, 'no_helmet': inserted.no_helmet,
                               'no_cloth': inserted.no_cloth, 'created_at': inserted.add_tim.isoformat()}
                        try:
                            await client.send(json.dumps(obj))
                        except:
                            pass

                event_loop = asyncio.get_event_loop()
                event_loop.create_task(send_to_all_clients())
    # end while not client.closed

    print('[INFO] Websocket client "{}" gone.'.format(remote_addr))


def websocket_thread():
    """
    WebSocket 服务端线程
    """

    async def asyncio_main():
        async def handler(client: WebSocketServerProtocol):
            websocket_clients.add(client)  # 添加至全局集合
            remote_addr = get_remote_addr(client)
            print('[INFO] New websocket client "{}" come.'.format(remote_addr))
            try:
                await websocket_handler(client=client, remote_addr=remote_addr)
            except Exception as ex:
                print('[ERRO] websocket_thread handler:', ex)
            finally:
                print('[INFO] Websocket client "{}" gone.'.format(remote_addr))
                if client in websocket_clients:
                    websocket_clients.remove(client)  # 从全局集合移出

        # end async def handler

        async with serve(handler, '0.0.0.0', WS_PORT):
            await asyncio.Future()

    asyncio.run(asyncio_main())


def flask_thread():
    """
    HTTP 服务端线程
    """
    app.run(host='0.0.0.0', port=HTTP_PORT)


def main():
    th1 = threading.Thread(target=websocket_thread)
    th1.start()
    th2 = threading.Thread(target=flask_thread)
    th2.start()

    # 主线程死循环，用于支持 Ctrl+C 退出程序
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            os._exit(1)


if __name__ == '__main__':
    main()
