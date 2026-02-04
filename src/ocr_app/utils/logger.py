import logging
import os
from logging.handlers import TimedRotatingFileHandler


def get_logger(config: dict, process_name: str, logger_name: str | None = None) -> logging.Logger:
    """
    Настраивает асинхронный логгер для конкретного процесса с изолированной директорией и файлами логов.
    
    Создает отдельную директорию для каждого процесса и настраивает три хэндлера:
    основной файловый с ротацией, консольный и отдельный файл для критических событий.
    Используется в многопроцессных приложениях для изоляции логов каждого процесса.

    Parameters
    ----------
    config : dict
        Конфигурационный словарь с параметрами логирования:
        
        - log_dir_async : str
            Корневая директория для асинхронных логов
        - level : str, optional
            Уровень логирования ('info', 'debug', по умолчанию 'debug')
        - max_log_days : int
            Количество дней хранения архивных лог-файлов
            
    process_name : str
        Уникальное имя или ID процесса (например, 'worker_123'),
        используется для создания изолированной директории и именования файлов
    logger_name : Optional[str], optional
        Имя логгера. Если не указано, используется process_name

    Returns
    -------
    logging.Logger
        Настроенный экземпляр логгера с тремя хэндлерами для конкретного процесса

    Raises
    ------
    OSError
        Возникает при проблемах с созданием директории логов или файлов

    Notes
    -----
    - Создает изолированную директорию для каждого процесса в log_dir_async
    - Основной лог-файл ротируется ежедневно в полночь
    - Имена файлов формируются как {process_name}.log и {process_name}_critical.log
    - Консольный вывод включает имя процесса для идентификации источника логов
    - При повторном вызове с тем же именем очищает старые хэндлеры
    - Использует форматирование с датой/временем, уровнем и именем модуля
    """
    
    # Базовая директория для всех асинхронных логов
    LOG_ROOT = config.get("log_dir_async", 'logs')
    
    # Создаем изолированную директорию для логов текущего процесса
    process_log_dir = os.path.join(LOG_ROOT, process_name)
    os.makedirs(process_log_dir, exist_ok=True)

    # Определяем уровень логирования из конфига
    logger_level = config.get("level", "debug")
    level = logging.INFO if logger_level == "info" else logging.DEBUG

    # === Настройка основного файлового хэндлера с ротацией ===
    # Создает отдельный лог-файл для каждого процесса
    log_file_path = os.path.join(process_log_dir, f"{process_name}.log")
    file_handler = TimedRotatingFileHandler(
        log_file_path,
        when="midnight",                            # Ротация в полночь
        interval=1,                                 # Интервал в 1 день
        backupCount=config.get("max_log_days", 7),  # Количество дней хранения архивов
        encoding="utf-8"                            # Кодировка файлов
    )
    # Формат сообщений для файлового лога
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(module)s] %(message)s')
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(level)

    # === Настройка консольного хэндлера ===
    # Выводит логи в консоль с идентификацией процесса
    console_handler = logging.StreamHandler()
    # Формат включает имя процесса для различения источников логов
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - {%(processName)s} [%(name)s] [%(module)s] %(message)s')
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(level)

    # === Настройка хэндлера для не критических событий ===
    # Отдельный файл для предупреждений и ошибок конкретного процесса
    warning_log_path = os.path.join(process_log_dir, f"{process_name}_warning.log")
    warning_handler = logging.FileHandler(warning_log_path)
    warning_handler.setLevel(logging.WARNING)  # Только WARNING и выше
    warning_handler.setFormatter(file_formatter)  # Использует тот же формат, что и основной файл
    
    # === Настройка хэндлера для критических событий ===
    # Отдельный файл для предупреждений и ошибок конкретного процесса
    error_log_path = os.path.join(process_log_dir, f"{process_name}_error.log")
    error_handler = logging.FileHandler(error_log_path)
    error_handler.setLevel(logging.ERROR)  # Только WARNING и выше
    error_handler.setFormatter(file_formatter)  # Использует тот же формат, что и основной файл

    # === Создание и настройка основного логгера ===
    # Если имя логгера не указано, используем имя процесса
    logger_name = logger_name or process_name
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    # Удаляем старые хэндлеры, чтобы избежать дублирования при повторном вызове
    if logger.hasHandlers():
        logger.handlers.clear()

    # Добавляем все настроенные хэндлеры к логгеру
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.addHandler(warning_handler)
    logger.addHandler(error_handler)
    
    # Отключаем передачу сообщений в root логгер, чтобы избежать дублирования
    logger.propagate = False

    return logger