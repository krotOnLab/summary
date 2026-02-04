"""Движок суммаризации — оркестратор стратегий."""
from pathlib import Path
from typing import Any
from ocr_app.core.strategies.base import BaseSummarizationStrategy


class SummarizationEngine:
    """
    Оркестратор процесса суммаризации.
    
    Инкапсулирует выбор и выполнение стратегии суммаризации.
    Позволяет легко переключаться между стратегиями без изменения клиентского кода.
    
    Пример использования:
        >>> engine = SummarizationEngine(hierarchical_strategy)
        >>> result = engine.summarize_folder("source_data")
        >>> print(result["overview"])
    """
    
    def __init__(self, strategy: BaseSummarizationStrategy) -> None:
        """
        Parameters
        ----------
        strategy : BaseSummarizationStrategy
            Стратегия суммаризации для использования.
        """
        self._strategy = strategy
    
    def summarize_folder(
        self,
        folder_path: str | Path,
        recursive: bool = True,
        **kwargs
    ) -> dict[str, Any]:
        """
        Запускает суммаризацию папки с использованием текущей стратегии.
        
        Parameters
        ----------
        folder_path : str | Path
            Путь к папке с документами.
        recursive : bool, optional
            Рекурсивная обработка подпапок (по умолчанию True).
        **kwargs : dict
            Дополнительные параметры, передаваемые стратегии.
        
        Returns
        -------
        dict
            Результат в едином формате (см. BaseSummarizationStrategy).
        """
        return self._strategy.summarize_folder(
            folder_path=folder_path,
            recursive=recursive,
            **kwargs
        )
    
    @property
    def strategy(self) -> BaseSummarizationStrategy:
        """Текущая стратегия суммаризации."""
        return self._strategy
    
    @strategy.setter
    def strategy(self, new_strategy: BaseSummarizationStrategy) -> None:
        """Изменение стратегии во время выполнения."""
        self._strategy = new_strategy
    
    def get_strategy_info(self) -> dict[str, str]:
        """
        Возвращает информацию о текущей стратегии.
        
        Returns
        -------
        dict
            {
                "name": str,
                "description": str
            }
        """
        return {
            "name": self._strategy.get_strategy_name(),
            "description": self._strategy.get_strategy_description()
        }