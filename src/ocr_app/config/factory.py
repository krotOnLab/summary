"""Фабрика для создания компонентов из конфигурации."""
from logging import Logger
from pathlib import Path

from ocr_app.clients import OpenRouterClient
from ocr_app.config.models import AppConfig
from ocr_app.core import DocumentExtractor, SummarizationEngine
from ocr_app.core.strategies import (
    HierarchicalSummarizationStrategy,
    SimpleSummarizationStrategy,
)
from ocr_app.utils import get_logger


class ComponentFactory:
    """
    Фабрика компонентов — создаёт все части системы из конфигурации.
    """
    
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._logger = None
    
    def get_logger(self) -> Logger:
        """Создаёт или возвращает кэшированный логгер."""
        if self._logger is None:
            logger_config = {
                "log_dir_async": self.config.logging.log_dir,
                "level": self.config.logging.level,
                "max_log_days": self.config.logging.max_log_days
            }
            self._logger = get_logger(logger_config, "ocr_app")
        return self._logger
    
    def get_extractor(self) -> DocumentExtractor:
        """Создаёт экстрактор документов."""
        logger = self.get_logger()
        return DocumentExtractor(
            logger=logger,
            tesseract_cmd=self.config.extraction.tesseract_cmd,
            ocr_lang=self.config.extraction.ocr_lang
        )
    
    def get_client(self) -> OpenRouterClient:
        """Создаёт клиент суммаризации."""
        logger = self.get_logger()
        return OpenRouterClient(
            logger=logger,
            api_key=self.config.openrouter.api_key,  # ← Теперь берётся из конфига
            default_strategy="balanced",
            request_delay=self.config.openrouter.request_delay
        )
    
    def get_strategy(self):
        """Создаёт стратегию суммаризации в зависимости от конфига."""
        extractor = self.get_extractor()
        client = self.get_client()
        
        if self.config.summarization.strategy == "hierarchical":
            return HierarchicalSummarizationStrategy(
                extractor=extractor,
                client=client,
                min_files_for_aggregation=self.config.summarization.min_files_for_aggregation
            )
        elif self.config.summarization.strategy == "simple":
            return SimpleSummarizationStrategy(
                extractor=extractor,
                client=client
            )
        else:
            raise ValueError(f"Неизвестная стратегия: {self.config.summarization.strategy}")
    
    def get_engine(self) -> SummarizationEngine:
        """Создаёт движок суммаризации с выбранной стратегией."""
        strategy = self.get_strategy()
        return SummarizationEngine(strategy)
    
    def get_output_dir(self) -> Path:
        """Возвращает директорию для сохранения результатов."""
        return Path(self.config.output_dir).resolve()