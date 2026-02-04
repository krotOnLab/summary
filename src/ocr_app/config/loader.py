"""Загрузка и валидация конфигурации из YAML + .env."""
from pathlib import Path
import yaml
import os
from dotenv import load_dotenv
from pydantic import ValidationError
from ocr_app.config.models import AppConfig



def load_config(config_path: str | Path | None = None) -> AppConfig:
    """
    Загружает конфигурацию из YAML и дополняет значениями из .env.
    
    Parameters
    ----------
    config_path : str | Path, optional
        Путь к файлу конфигурации. Если None — ищет config.yaml в корне проекта.
    
    Returns
    -------
    AppConfig
        Валидированная конфигурация.
    
    Raises
    ------
    FileNotFoundError
        Если файл конфигурации не найден.
    ValueError
        Если конфигурация не прошла валидацию.
    """
    # 1. Загружаем .env
    load_dotenv()
    
    # 2. Определяем путь к конфигу
    config_path = Path(config_path) if config_path else Path("config.yaml")
    
    if not config_path.exists():
        raise FileNotFoundError(
            f"Файл конфигурации не найден: {config_path.resolve()}\n"
            f"Создайте config.yaml в корне проекта"
        )
    
    # 3. Загружаем YAML
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Ошибка парсинга YAML: {e}") from e
    
    # 4. Дополняем конфиг значениями из .env (только для секретов)
    # Это безопаснее, чем использовать плейсхолдеры ${VAR} в YAML
    if "openrouter" not in yaml_config:
        yaml_config["openrouter"] = {}
    
    # API ключ из .env (обязательный)
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY не найден в .env файле.\n"
            "Добавьте строку: OPENROUTER_API_KEY=sk-or-v1-..."
        )
    yaml_config["openrouter"]["api_key"] = api_key
    
    # Путь к Tesseract из .env (опциональный)
    if "extraction" not in yaml_config:
        yaml_config["extraction"] = {}
    
    tesseract_cmd = os.getenv("PATH_TESSERACT")
    if tesseract_cmd:
        yaml_config["extraction"]["tesseract_cmd"] = tesseract_cmd
    
    # 5. Валидируем конфигурацию
    try:
        config = AppConfig(**yaml_config)
        return config
    except ValidationError as e:
        error_lines = ["Ошибка валидации конфигурации:"]
        for error in e.errors():
            loc = " → ".join(str(part) for part in error["loc"])
            msg = error["msg"]
            error_lines.append(f"  • [{loc}] {msg}")
        raise ValueError("\n".join(error_lines)) from e