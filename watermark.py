"""
Модуль для работы с водяными знаками на изображениях
"""
from PIL import Image, ImageDraw, ImageFont
import os
import logging
from config import WatermarkConfig

logger = logging.getLogger(__name__)


def add_watermark(image_path: str, output_path: str) -> bool:
    """
    Накладывает водяной знак на изображение
    
    Args:
        image_path: путь к исходному изображению
        output_path: путь для сохранения изображения с водяным знаком
        
    Returns:
        bool: True если успешно, False если ошибка
    """
    try:
        # Открываем изображение
        img = Image.open(image_path).convert('RGBA')
        
        # Создаем слой для водяного знака
        watermark = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(watermark)
        
        # Рассчитываем размер шрифта (5% от ширины изображения)
        font_size = int(img.width * WatermarkConfig.WATERMARK_FONT_SIZE_RATIO)
        
        # Пытаемся загрузить шрифт, если нет - используем дефолтный
        try:
            # Пробуем разные пути для шрифтов в Linux
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/System/Library/Fonts/Helvetica.ttc",  # macOS
                "C:\\Windows\\Fonts\\Arial.ttf"        # Windows
            ]
            font = None
            for font_path in font_paths:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, font_size)
                    break
            if font is None:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        
        # Текст водяного знака
        text = WatermarkConfig.WATERMARK_TEXT
        
        # Позиция: центр изображения
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (img.width - text_width) // 2
        y = (img.height - text_height) // 2
        
        # Рисуем текст с прозрачностью
        alpha = int(255 * WatermarkConfig.WATERMARK_OPACITY)
        draw.text((x, y), text, fill=(255, 255, 255, alpha), font=font)
        
        # Объединяем изображения
        combined = Image.alpha_composite(img, watermark)
        
        # Конвертируем в RGB для сохранения
        if combined.mode == 'RGBA':
            background = Image.new('RGB', combined.size, (255, 255, 255))
            background.paste(combined, mask=combined.split()[3])
            combined = background
        
        # Сохраняем
        combined.save(output_path, quality=85, optimize=True)
        
        logger.debug(f"Водяной знак добавлен: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка добавления водяного знака: {e}")
        return False
