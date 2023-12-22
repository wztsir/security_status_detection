import pymysql
import threading
import datetime
from os import path as ospath
import shutil
import os
import websockets.server


class Atomic:
    """
    用于并发原子读写的辅助类
    """

    def __init__(self, initial_value):
        self.value = initial_value
        self.lock = threading.Lock()

    def get(self):
        with self.lock:
            return self.value

    def set(self, new_value):
        if type(new_value) is Atomic:
            raise Exception('can not use Atomic object as `set`\'s argument')
        with self.lock:
            self.value = new_value


def generate_image_filename(time: datetime.datetime, mkdir=True):
    """
    生成用于保存图片的文件名，如果将 mkdir 设置为 True 则会在生成文件名的同时，创建对应的目录
    "./images/2023-06-19/20230619_143804_904954.jpg"
    """
    dirpath = ospath.join('images', time.strftime('%Y-%m-%d'))
    if mkdir and ospath.exists(dirpath) and not ospath.isdir(dirpath):
        shutil.rmtree(dirpath)
    if mkdir and not ospath.exists(dirpath):
        os.makedirs(dirpath)
    return ospath.join(dirpath, time.strftime('%Y%m%d_%H%M%S_%f.jpg'))


class MySQLConnection:
    """
    数据库连接器，支持读和写操作 (暂没添加连接池，觉得现阶段还没必要用到池)
    """

    def __init__(self, host='localhost', port=3306, user='root', password='123', database='db'):
        self.connection = pymysql.connect(
            host=host, port=port, user=user, password=password, database=database,
            cursorclass=pymysql.cursors.DictCursor,
        )
        # For connection pool, refers to https://github.com/18651440358/ThemisPool/blob/main/ThemisPool.py.

    def query(self, sql, args):
        if not self.connection.open:
            self.connection.connect()
        with self.connection.cursor() as cursor:
            cursor.execute(sql, args)
            return cursor.fetchall()

    def update(self, sql, args):
        if not self.connection.open:
            self.connection.connect()
        with self.connection.cursor() as cursor:
            cursor.execute(sql, args)
            self.connection.commit()
            return cursor.lastrowid


def get_remote_addr(client: websockets.server.WebSocketServerProtocol):
    """
    获取与服务端建连的 WebSocket 客户端信息，若为 IPv4 则返回 "ip:port" 字符串
    """
    remove_addr = client.remote_address
    if type(remove_addr) is tuple and len(remove_addr) == 2:
        remove_addr = f'{remove_addr[0]}:{remove_addr[1]}'
    return remove_addr
