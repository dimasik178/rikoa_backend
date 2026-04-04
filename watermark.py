"""
Модуль для работы с водяными знаками на изображениях
"""
from PIL import Image, ImageDraw, ImageFont
import os
import logging
import random
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
        font_size = max(WatermarkConfig.WATERMARK_MIN_FONT_SIZE, 
                        int(img.width * WatermarkConfig.WATERMARK_FONT_SIZE_RATIO))
        
        # Пути к шрифтам в порядке приоритета
        font_paths = [
            WatermarkConfig.WATERMARK_FONT_PATH,                    # Локальный шрифт проекта
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",      # Linux (Debian/Ubuntu)
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",  # Linux
            "/System/Library/Fonts/Helvetica.ttc",                  # macOS
            "C:\\Windows\\Fonts\\Arial.ttf",                        # Windows
            "C:\\Windows\\Fonts\\Roboto.ttf",                       # Windows (альтернатива)
        ]
        
        # Пытаемся загрузить шрифт
        font = None
        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, font_size)
                    logger.debug(f"Загружен шрифт: {font_path}")
                    break
            except Exception as e:
                logger.debug(f"Не удалось загрузить шрифт {font_path}: {e}")
                continue
        
        # Если ни один шрифт не загрузился, используем дефолтный
        if font is None:
            logger.warning("Не удалось загрузить ни один шрифт, используется дефолтный")
            font = ImageFont.load_default()
        
        # Текст водяного знака
        if img.width < 100:
            text = "DEMO"
        else:
            text = WatermarkConfig.WATERMARK_TEXT
        
        # Позиция: центр изображения
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (img.width - text_width) // 2
        y = (img.height - text_height) // 2
        
        # Основной цвет текста
        alpha = int(255 * WatermarkConfig.WATERMARK_OPACITY)
        text_color = (255, 255, 255, alpha)
        
        # Цвет обводки - негатив от фона (вычисляем из центра изображения)
        center_x = img.width // 2
        center_y = img.height // 2
        bg_color = img.getpixel((center_x, center_y))
        
        # Негатив цвета фона
        outline_color = (255 - bg_color[0], 255 - bg_color[1], 255 - bg_color[2], alpha)
        
        # Рисуем обводку (8 направлений + случайные смещения)
        outline_offsets = [
            (-2, -2), (-2, -1), (-2, 0), (-2, 1), (-2, 2),
            (-1, -2), (-1, -1), (-1, 0), (-1, 1), (-1, 2),
            (0, -2), (0, -1), (0, 1), (0, 2),
            (1, -2), (1, -1), (1, 0), (1, 1), (1, 2),
            (2, -2), (2, -1), (2, 0), (2, 1), (2, 2),
        ]
        
        # Добавляем случайные хаотичные смещения
        for _ in range(random.randint(5, 15)):
            ox = random.randint(-3, 3)
            oy = random.randint(-3, 3)
            if (ox, oy) not in outline_offsets:
                outline_offsets.append((ox, oy))
        
        # Рисуем обводку
        for offset_x, offset_y in outline_offsets:
            draw.text((x + offset_x, y + offset_y), text, fill=outline_color, font=font)
        
        # Рисуем основной текст поверх обводки
        draw.text((x, y), text, fill=text_color, font=font)
        
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
