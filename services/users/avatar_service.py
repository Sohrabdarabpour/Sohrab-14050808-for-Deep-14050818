"""برش و استانداردسازی آواتار کاربر.

اگر OpenCV نصب باشد، چهره تشخیص داده می‌شود و برش حول آن انجام می‌گیرد؛
در غیر این صورت یک برش مربعی از مرکز تصویر با Pillow زده می‌شود.
به این ترتیب آپلود آواتار هرگز به‌خاطر نبود یک کتابخانه‌ی سنگین نمی‌شکند.
"""

try:  # pragma: no cover - بستگی به محیط نصب دارد
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None

from PIL import Image


class AvatarService:
    """آماده‌سازی تصویر پروفایل برای نمایش در سامانه."""

    OUTPUT_SIZE = (300, 300)
    JPEG_QUALITY = 90

    # ============================================================
    # ★ ورودی اصلی
    # ============================================================
    @staticmethod
    def process_avatar(input_path, output_path):
        """برش و تغییر اندازه‌ی آواتار؛ True در صورت موفقیت."""
        try:
            if cv2 is not None:
                crop = AvatarService._detect_face_crop(input_path)
                if crop is not None:
                    cv2.imwrite(output_path, crop)
                    AvatarService._resize_in_place(output_path)
                    return True

            AvatarService._center_crop(input_path, output_path)
            return True
        except Exception:
            return False

    # ============================================================
    # ★ برش بر اساس چهره (OpenCV)
    # ============================================================
    @staticmethod
    def _detect_face_crop(input_path):
        """بزرگ‌ترین چهره را پیدا و با حاشیه برش می‌دهد؛ در نبود چهره None."""
        image = cv2.imread(input_path)
        if image is None:
            return None

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        faces = cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)

        if len(faces) == 0:
            return image

        height, width = image.shape[:2]
        x, y, w, h = max(faces, key=lambda face: face[2] * face[3])
        padding = int(max(w, h) * 0.8)

        x1, y1 = max(0, x - padding), max(0, y - padding)
        x2, y2 = min(width, x + w + padding), min(height, y + h + padding)
        return image[y1:y2, x1:x2]

    # ============================================================
    # ★ برش مرکزی (Pillow) — جایگزین بدون OpenCV
    # ============================================================
    @staticmethod
    def _center_crop(input_path, output_path):
        """برش مربعی از مرکز تصویر و تغییر اندازه به ۳۰۰×۳۰۰."""
        with Image.open(input_path) as source:
            image = source.convert("RGB")

            width, height = image.size
            side = min(width, height)
            left = (width - side) // 2
            top = (height - side) // 2
            image = image.crop((left, top, left + side, top + side))

            image = image.resize(AvatarService.OUTPUT_SIZE, Image.LANCZOS)
            image.save(output_path, format="JPEG", quality=AvatarService.JPEG_QUALITY)

    # ============================================================
    # ★ تغییر اندازه‌ی فایل خروجی (بعد از ذخیره با OpenCV)
    # ============================================================
    @staticmethod
    def _resize_in_place(path):
        with Image.open(path) as source:
            image = source.convert("RGB")
            image = image.resize(AvatarService.OUTPUT_SIZE, Image.LANCZOS)
            image.save(path, format="JPEG", quality=AvatarService.JPEG_QUALITY)
