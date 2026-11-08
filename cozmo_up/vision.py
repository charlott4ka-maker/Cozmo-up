"""Зрение: камера Козмо и распознавание маркеров через OpenCV.

Про кубики честно: pycozmo НЕ умеет распознавать родные символы на гранях
кубиков Anki — этого в библиотеке просто нет. Зато кубик сообщает о себе
по радио (пакеты ObjectAvailable / ObjectTapped), а для «вижу и еду к
цели» отлично работают ArUco-маркеры: их надо распечатать на бумаге,
зато распознаются они надёжно и стандартными средствами OpenCV.

Напечатать лист с маркерами: python scripts/make_markers.py
"""

from typing import List, NamedTuple, Optional

#: Словарь маркеров. 4x4 с 50 вариантами — крупные клетки, читается
#: с плохонькой камеры Козмо лучше, чем более подробные словари.
ARUCO_DICT = "DICT_4X4_50"


class Marker(NamedTuple):
    """Найденный маркер."""
    id: int
    #: Центр в пикселях.
    cx: float
    cy: float
    #: Сторона в пикселях — грубая мера расстояния: чем больше, тем ближе.
    size: float
    #: Смещение от центра кадра: -1.0 слева, 0.0 по центру, +1.0 справа.
    offset: float


def to_cv(image):
    """PIL.Image -> массив OpenCV (оттенки серого)."""
    import numpy as np

    return np.array(image.convert("L"))


class MarkerDetector:
    """Ищет ArUco-маркеры в кадрах с камеры.

    Пример:
        detector = MarkerDetector()
        for marker in detector.find(image):
            print(marker.id, marker.offset)
    """

    def __init__(self, dictionary: str = ARUCO_DICT) -> None:
        import cv2

        self.cv2 = cv2
        name = getattr(cv2.aruco, dictionary)
        self._dict = cv2.aruco.getPredefinedDictionary(name)
        params = cv2.aruco.DetectorParameters()
        self._detector = cv2.aruco.ArucoDetector(self._dict, params)

    def find(self, image) -> List[Marker]:
        """Найти все маркеры в кадре. image — PIL.Image или массив OpenCV."""
        import numpy as np

        frame = image if isinstance(image, np.ndarray) else to_cv(image)
        corners, ids, _ = self._detector.detectMarkers(frame)
        if ids is None:
            return []

        height, width = frame.shape[:2]
        found = []
        for quad, marker_id in zip(corners, ids.flatten()):
            pts = quad.reshape(4, 2)
            cx, cy = pts[:, 0].mean(), pts[:, 1].mean()
            # Средняя длина стороны квадрата.
            size = float(np.mean([
                np.linalg.norm(pts[i] - pts[(i + 1) % 4]) for i in range(4)
            ]))
            offset = (cx - width / 2) / (width / 2)
            found.append(Marker(int(marker_id), float(cx), float(cy),
                                size, float(offset)))
        return found

    def nearest(self, image) -> Optional[Marker]:
        """Самый близкий маркер (наибольший в кадре) или None."""
        markers = self.find(image)
        return max(markers, key=lambda m: m.size) if markers else None

    def draw(self, image):
        """Вернуть цветной кадр с обведёнными маркерами — для показа в окне."""
        import numpy as np

        frame = image if isinstance(image, np.ndarray) else to_cv(image)
        color = self.cv2.cvtColor(frame, self.cv2.COLOR_GRAY2BGR)
        corners, ids, _ = self._detector.detectMarkers(frame)
        if ids is not None:
            self.cv2.aruco.drawDetectedMarkers(color, corners, ids)
        return color


def generate_marker(marker_id: int, size_px: int = 400):
    """Нарисовать один маркер. Возвращает массив OpenCV."""
    import cv2

    d = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, ARUCO_DICT))
    return cv2.aruco.generateImageMarker(d, marker_id, size_px)
