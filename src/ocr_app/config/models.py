"""Pydantic V2 модели для валидации конфигурации (только BaseModel)."""
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict, FilePath, SecretStr


class LoggingConfig(BaseModel):
    """Конфигурация логирования."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)
    
    level: Literal["debug", "info", "warning", "error", "critical"] = Field(
        default="info",
        description="Уровень логирования"
    )
    log_dir: str = Field(
        default="logs",
        description="Директория для логов"
    )
    max_log_days: int = Field(
        default=7,
        ge=1,
        description="Дней хранения ротированных логов"
    )
    
    @field_validator("level", mode="before")
    @classmethod
    def validate_level(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.lower()
        allowed = {"debug", "info", "warning", "error", "critical"}
        if v not in allowed:
            raise ValueError(f"Уровень логирования должен быть одним из: {allowed}")
        return v


class OpenRouterConfig(BaseModel):
    """Конфигурация клиента OpenRouter."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)
    
    api_key: SecretStr = Field(..., description="API ключ OpenRouter")
    default_model: str = Field(
        default="mistralai/mistral-7b-instruct:nitro",
        description="Модель по умолчанию"
    )
    request_delay: float = Field(
        default=5.0,
        ge=1.0,
        description="Задержка между запросами (сек)"
    )
    max_retries: int = Field(
        default=2,
        ge=1,
        description="Макс. попыток при ошибках"
    )


class SummarizationConfig(BaseModel):
    """Конфигурация суммаризации."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)
    
    strategy: Literal["hierarchical", "simple"] = Field(
        default="hierarchical",
        description="Стратегия суммаризации"
    )
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Температура генерации"
    )
    pause_between_files: float = Field(
        default=2.0,
        ge=0.0,
        description="Пауза между файлами (сек)"
    )
    min_files_for_aggregation: int = Field(
        default=2,
        ge=1,
        description="Мин. файлов для агрегации (только для hierarchical)"
    )
    
    @field_validator("strategy", mode="before")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.lower()
        allowed = {"hierarchical", "simple"}
        if v not in allowed:
            raise ValueError(f"Стратегия должна быть одной из: {allowed}")
        return v


class ExtractionConfig(BaseModel):
    """Конфигурация извлечения текста."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)
    
    tesseract_cmd: FilePath | None = Field(
        default=None,
        description="Путь к tesseract.exe"
    )
    ocr_lang: str = Field(
        default="rus+eng",
        description="Языки OCR (например: 'rus+eng')"
    )
    recursive: bool = Field(
        default=True,
        description="Рекурсивная обработка подпапок"
    )


class AppConfig(BaseModel):
    """Корневая конфигурация приложения."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)
    
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    openrouter: OpenRouterConfig
    summarization: SummarizationConfig = Field(default_factory=SummarizationConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    
    output_dir: str = Field(
        default="output",
        description="Директория для сохранения результатов"
    )
    source_dir: str = Field(
        default="source_data",
        description="Директория с исходными документами"
    )
    
    @field_validator("output_dir", "source_dir", mode="before")
    @classmethod
    def validate_dirs(cls, v: str) -> str:
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path.resolve())