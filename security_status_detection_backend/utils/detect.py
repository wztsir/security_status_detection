import cv2
from ultralytics import YOLO
import colorsys
from PIL import ImageDraw, ImageFont, Image

# Load the YOLOv8 model
print('[INFO] Loading two detection models...')
model = YOLO('./models/best.pt')
_ = model('./models/test_img.jpg', save=False, verbose=False)  # test model, 等待让模型载入到显存内
model_person = YOLO('./models/yolov8m.pt')
_ = model_person('./models/test_img.jpg', save=False, verbose=False)
print('[INFO] Detection models loaded.')

color = {(0, 255, 255), (255, 0, 255), (255, 255, 0), (255, 255, 255), (255, 255, 255)}


def detect_video(video_path):
    cap = cv2.VideoCapture(video_path)
    out = {}
    # Loop through the video frames
    while cap.isOpened():
        # Read a frame from the video
        success, frame = cap.read()

        if success:
            # Run YOLOv8 inference on the frame
            results = model(frame)
            temp = model.names
            temp2 = results[0].boxes.cls.numpy().tolist()
            for key in temp:
                out[temp[key]] = 0
            for key in temp2:
                out[temp[key]] += 1

            # Visualize the results on the frame
            print(out)
            annotated_frame = results[0].plot()

            # Display the annotated frame
            cv2.imshow("YOLOv8 Inference", annotated_frame)
            cv2.imshow("YOLOv8 Inference", frame)

            # Break the loop if 'q' is pressed
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        else:
            # Break the loop if the end of the video is reached
            break
    cap.release()
    cv2.destroyAllWindows()


class DetectionResult:
    """
    detect_img 的检测结果
    """

    def __init__(self, person: int = 0, no_helmet: int = 0, no_cloth: int = 0):
        self.person = person if person is not None else 0
        self.no_helmet = no_helmet if no_helmet is not None else 0
        self.no_cloth = no_cloth if no_cloth is not None else 0

    def equals(self, o) -> bool:
        if type(o) is not DetectionResult:
            return False
        return self.person == o.person and self.no_helmet == o.no_helmet and self.no_cloth == o.no_cloth

    def __str__(self) -> str:
        return f'DetectionResult({self.person}, {self.no_helmet}, {self.no_cloth})'


def detect_img(frame):
    """
    安全帽与反光衣检测
    """
    results = model.predict(source=frame, conf=0.65, classes=[1, 2, 3, 4], augment=True, agnostic_nms=True)
    result_person = model_person.predict(source=frame, conf=0.65, classes=0, augment=True, agnostic_nms=True)
    keys = model.names  # {}

    temp2 = results[0].boxes.cls.cpu().numpy().tolist()
    temp1 = result_person[0].boxes.cls.cpu().numpy().tolist()
    out = {}
    # temp = model.names
    for key in keys:
        out[keys[key]] = 0
    for category_num in temp2:
        if category_num != 0:
            out[keys[category_num]] += 1
    for category_num in temp1:
        if category_num == 0:
            out[keys[category_num]] += 1

    # frame1 = result_person[0].plot(font_size=0.5, conf=False)
    frame1 = results[0].plot(font_size=0.5, conf=False)
    # frame1 = results[0].plot(line_width=8, labels=False, conf=False) # ppt 中的截图使用了该配置
    num = out['person'] - out['helmet'] if out['person'] - out['helmet'] > 0 else 0
    num1 = out['person'] - out['reflective_clothes'] if out['person'] - out['reflective_clothes'] > 0 else 0
    res = DetectionResult(person=out['person'], no_helmet=num, no_cloth=num1)
    return frame1, res
