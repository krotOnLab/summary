
from pathlib import Path

import pdfplumber
import pytesseract
from PIL import Image
from typing import cast

from ocr_app.protocols import DocumentExtractorProtocol, LoggerProtocol


class DocumentExtractor(DocumentExtractorProtocol):
    """Извлекает текст из документов разных форматов"""
    
    SUPPORTED_IMAGE_EXTS = {'.jpg', '.jpeg', '.webp', '.png', '.bmp', '.tiff'}
    SUPPORTED_PDF_EXTS = {'.pdf'}
    
    def __init__(self, logger: LoggerProtocol, tesseract_cmd: Path | str | None = None, ocr_lang: str = 'rus+eng') -> None:
        """
        Args:
            tesseract_cmd: путь к tesseract.exe (если не в PATH)
            ocr_lang: языки для OCR, например 'rus+eng'
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self.ocr_lang = ocr_lang
        self.logger = logger
    
    def extract_file(self, file_path: str) -> str:
        """
        Извлекает текст из одного файла.
        
        Returns:
            Текст документа или пустая строка при ошибке.
        """
        path = Path(file_path)
        if not path.exists():
            self.logger.warning(f"Файл не найден: {file_path}")
            return ""
        
        ext = path.suffix.lower()
        
        try:
            if ext in self.SUPPORTED_PDF_EXTS:
                return self._extract_pdf(path)
            elif ext in self.SUPPORTED_IMAGE_EXTS:
                return self._extract_image(path)
            else:
                self.logger.info(f"Пропущен неподдерживаемый формат: {file_path}")
                return ""
                
        except Exception as e:
            self.logger.error(f"Ошибка обработки {file_path}: {e}")
            return ""
    
    def _extract_pdf(self, path: Path) -> str:
        """Извлечение текста из PDF через pdfplumber"""
        text = ""
        try:
            with pdfplumber.open(path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Страница {page_num} ---\n{page_text}\n"
            self.logger.info(f"PDF извлечён: {path.name} ({len(text)} символов)")
        except Exception as e:
            self.logger.error(f"Ошибка PDF {path.name}: {e}")
            # Попытка альтернативного метода для сканов (если нужно — добавим позже)
        return text.strip()
    
    def _extract_image(self, path: Path) -> str:
        """Извлечение текста из изображения через Tesseract"""
        try:
            # Открываем изображение (поддержка WebP через Pillow)
            img = Image.open(path)
            
            # Конвертация в RGB если нужно (для WebP с прозрачностью)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            
            # Распознавание
            tesseract_text = pytesseract.image_to_string(img, lang=self.ocr_lang)
            text = cast(str, tesseract_text)
            self.logger.info(f"Изображение распознано: {path.name} ({len(text)} символов)")
            return text.strip()
            
        except Exception as e:
            self.logger.error(f"Ошибка OCR {path.name}: {e}")
            return ""
    
    def extract_folder(self, folder_path: str, recursive: bool = True) -> dict:
        """
        Рекурсивно извлекает текст из всех поддерживаемых файлов в папке.
        
        Returns:
            Словарь с агрегированными результатами.
        """
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            raise ValueError(f"Папка не найдена: {folder_path}")
        
        content: dict[str, str] = {}
        failed_files: list[str] = []
        
        # Сбор всех файлов
        pattern = "**/*" if recursive else "*"
        files = [f for f in folder.glob(pattern) if f.is_file()]
        
        self.logger.info(f"Найдено файлов: {len(files)}")
        
        for file_path in files:
            text = self.extract_file(str(file_path))
            rel_path = file_path.relative_to(folder)
            
            if text.strip():
                content[str(rel_path)] = text
            else:
                failed_files.append(str(rel_path))
        
        return {
            "total_files": len(files),
            "processed": len(content),
            "failed": failed_files,
            "content": content
        }
        
    @property
    def supported_extensions(self) -> list[str]:
        """Реализация обязательного свойства протокола."""
        return list(self.SUPPORTED_IMAGE_EXTS | self.SUPPORTED_PDF_EXTS)