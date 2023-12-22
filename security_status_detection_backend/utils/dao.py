import cv2
import datetime
from utils.utilities import generate_image_filename, MySQLConnection
import typing


class DetectionLog:
    def __init__(self, log_id: int, base_code: str, device_id: str, person: int, no_helmet: int, no_cloth: int, image_url: str, add_nam: str, add_tim: datetime.datetime, update_nam: str, update_tim: datetime.datetime):
        self.log_id = log_id
        self.base_code = base_code
        self.device_id = device_id
        self.person = person
        self.no_helmet = no_helmet
        self.no_cloth = no_cloth
        self.image_url = image_url
        self.add_nam = add_nam
        self.add_tim = add_tim
        self.update_nam = update_nam
        self.update_tim = update_tim


def query_detection_logs(dbconn: MySQLConnection, base_code: str, page: int, limit: int) -> typing.Tuple[int, typing.List[DetectionLog]]:
    """
    分页查询数据库，获取日志总数和具体的日志列表，该函数可能会抛异常
    """
    # query total count
    sql = f'''
        SELECT count(log_id) AS count FROM helmet_cloth_logs
        {'WHERE base_code = %s' if base_code != '' else ''}
    '''
    args = base_code if base_code != '' else ()
    count = dbconn.query(sql, args)
    count = int(count[0]['count'])

    # query detection logs
    sql = f'''
        SELECT log_id, base_code, device_id, person, no_helmet, no_cloth, image_url, add_nam, add_tim, update_nam, update_tim FROM helmet_cloth_logs
        {'WHERE base_code = %s' if base_code != '' else ''}
        ORDER BY add_tim DESC LIMIT %s OFFSET %s
    '''
    args = (limit, (page - 1) * limit)
    args = (base_code, args[0], args[1]) if base_code != '' else args
    logs = dbconn.query(sql, args)

    # refine logs
    logs = [DetectionLog(
        log_id=log['log_id'],
        base_code=log['base_code'],
        device_id=log['device_id'],
        person=log['person'],
        no_helmet=log['no_helmet'],
        no_cloth=log['no_cloth'],
        image_url=log['image_url'],
        add_nam=log['add_nam'],
        add_tim=log['add_tim'].astimezone(),
        update_nam=log['update_nam'],
        update_tim=log['update_tim'].astimezone(),
    ) for log in list(logs)]

    # return
    return count, logs


def save_screenshot_and_addto_database(dbconn: MySQLConnection, person: int, no_helmet: int, no_cloth: int, frame: cv2.Mat) -> typing.Union[None, DetectionLog]:
    """
    保存截图，并记录日志到数据库，该函数不抛异常，若发生错误则返回 None
    """
    now = datetime.datetime.now()
    now_string = now.strftime('%Y-%m-%d %H:%M:%S')
    try:
        filepath = generate_image_filename(now, mkdir=True)  # ./images/2023-06-19/20230619_143804_904954.jpg
        cv2.imwrite(filepath, frame)  # 将引起状态变化的帧(图片)写入本地磁盘
    except Exception as ex:
        print('[ERRO] save_screenshot:', ex)
        return None  # 写入磁盘错误，则不变更数据库

    sql = '''
        INSERT INTO helmet_cloth_logs(base_code, device_id, person, no_helmet, no_cloth, image_url, add_nam, add_tim, update_nam, update_tim)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    '''
    args = ('CSCK', 'T001', person, no_helmet, no_cloth, filepath, 'python', now_string, 'python', now_string)
    try:
        dbconn.update(sql, args)  # 将变化的状态、图片路径、变化时间等插入到数据库
    except Exception as ex:
        print('[ERRO] addto_database:', ex)
        return None

    now = now.replace(microsecond=0).astimezone()
    return DetectionLog(
        log_id=0,
        base_code=args[0],
        device_id=args[1],
        person=args[2],
        no_helmet=args[3],
        no_cloth=args[4],
        image_url=args[5],
        add_nam=args[6],
        add_tim=now,
        update_nam=args[8],
        update_tim=now,
    )
