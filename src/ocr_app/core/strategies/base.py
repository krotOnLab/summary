"""Базовые абстракции для стратегий суммаризации."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from ocr_app.protocols.extractor import DocumentExtractorProtocol
from ocr_app.protocols.client import SummarizationClientProtocol


class BaseSummarizationStrategy(ABC):
    """
    Абстрактная стратегия суммаризации.
    
    Определяет единый интерфейс для всех алгоритмов суммаризации папок.
    Позволяет легко добавлять новые подходы без изменения ядра системы.
    
    Примеры реализаций:
        - HierarchicalSummarizationStrategy: чанки → агрегация
        - SimpleSummarizationStrategy: суммаризация каждого файла без агрегации
        - SemanticClusteringStrategy: кластеризация по смыслу перед агрегацией
    """
    
    def __init__(
        self,
        extractor: DocumentExtractorProtocol,
        client: SummarizationClientProtocol
    ) -> None:
        """
        Parameters
        ----------
        extractor : DocumentExtractorProtocol
            Экстрактор текста из документов.
        client : SummarizationClientProtocol
            Клиент для создания саммари.
        """
        self.extractor = extractor
        self.client = client
    
    @abstractmethod
    def summarize_folder(
        self,
        folder_path: str | Path,
        recursive: bool = True,
        **kwargs
    ) -> dict[str, Any]:
        """
        Суммаризирует содержимое папки.
        
        Parameters
        ----------
        folder_path : str | Path
            Путь к папке с документами.
        recursive : bool, optional
            Рекурсивная обработка подпапок (по умолчанию True).
        **kwargs : dict
            Стратегия-специфичные параметры.
        
        Returns
        -------
        dict
            Единый формат результата для всех стратегий:
            {
                "overview": str | None,          # Общий обзор папки (может быть None)
                "file_summaries": List[dict],    # Саммари по каждому файлу
                "metadata": {
                    "strategy": str,             # Имя стратегии
                    "total_files": int,
                    "processed": int,
                    "failed": List[str],
                    "processing_time": float
                }
            }
        
        Raises
        ------
        ValueError
            Если папка не существует.
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """
        Возвращает уникальное имя стратегии.
        
        Returns
        -------
        str
            Имя стратегии (например, 'hierarchical', 'simple').
        """
        pass
    
    @abstractmethod
    def get_strategy_description(self) -> str:
        """
        Возвращает описание стратегии для логирования и документации.
        
        Returns
        -------
        str
            Описание алгоритма работы.
        """
        pass