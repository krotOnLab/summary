"""Протоколы для извлечения текста из документов."""
from pathlib import Path
from typing import Protocol, runtime_checkable, Any


@runtime_checkable
class DocumentExtractorProtocol(Protocol):
    """
    Протокол для экстракторов документов.
    
    Любой класс, реализующий этот интерфейс, может извлекать текст из файлов
    и папок независимо от формата (PDF, изображения, DOCX и т.д.).
    
    Примеры реализаций:
        - DocumentExtractor (PDF + изображения через Tesseract)
        - DocxExtractor (через python-docx)
        - HtmlExtractor (через BeautifulSoup)
    """
    
    def extract_file(self, file_path: str | Path) -> str:
        """
        Извлекает текст из одного файла.
        
        Parameters
        ----------
        file_path : str | Path
            Путь к файлу.
        
        Returns
        -------
        str
            Извлечённый текст. Пустая строка при ошибке или отсутствии текста.
        
        Notes
        -----
        Реализация ДОЛЖНА обрабатывать ошибки внутри себя и возвращать
        пустую строку вместо выброса исключений (для отказоустойчивости).
        """
        ...
    
    def extract_folder(
        self,
        folder_path: str | Path,
        recursive: bool = True
    ) -> dict[str, Any]:
        """
        Рекурсивно извлекает текст из всех поддерживаемых файлов в папке.
        
        Parameters
        ----------
        folder_path : str | Path
            Путь к папке.
        recursive : bool, optional
            Рекурсивная обработка подпапок (по умолчанию True).
        
        Returns
        -------
        dict
            Словарь с результатами в формате:
            {
                "total_files": int,          # Всего найдено файлов
                "processed": int,            # Успешно обработано
                "failed": List[str],         # Относительные пути необработанных файлов
                "content": Dict[str, str]    # {относительный_путь: текст}
            }
        
        Raises
        ------
        ValueError
            Если папка не существует или не является директорией.
        """
        ...
    
    @property
    def supported_extensions(self) -> list[str]:
        """
        Возвращает список поддерживаемых расширений файлов.
        
        Returns
        -------
        List[str]
            Список расширений в формате ['.pdf', '.jpg', ...].
        """
        ...