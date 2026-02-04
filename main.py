"""CLI интерфейс для сервиса суммаризации документов."""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from ocr_app.config.factory import ComponentFactory
from ocr_app.config.loader import load_config

# Добавляем src в путь для запуска из корня
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))




def parse_args():
    """Парсит аргументы командной строки."""
    parser = argparse.ArgumentParser(
        description="Сервис суммаризации документов: извлекает текст из PDF/изображений и создаёт саммари через LLM",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Путь к файлу конфигурации (по умолчанию: config.yaml)"
    )
    
    parser.add_argument(
        "--source",
        type=str,
        help="Путь к папке с документами (переопределяет source_dir из конфига)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Путь к директории для результатов (переопределяет output_dir из конфига)"
    )
    
    parser.add_argument(
        "--strategy",
        choices=["hierarchical", "simple"],
        help="Стратегия суммаризации (переопределяет конфиг)"
    )
    
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Показать список доступных моделей и выйти"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="ocr-app 0.1.0"
    )
    
    return parser.parse_args()


def save_results(result: dict, output_dir: Path, source_dir: str):
    """Сохраняет результаты в файлы."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Основной отчёт в читаемом формате
    report_path = output_dir / f"summary_{timestamp}.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("ОТЧЁТ СУММАРИЗАЦИИ ДОКУМЕНТОВ\n")
        f.write(f"Источник: {source_dir}\n")
        f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Стратегия: {result['metadata']['strategy']}\n")
        f.write("=" * 70 + "\n\n")
        
        if result["overview"]:
            f.write("ОБЩИЙ ОБЗОР СОДЕРЖИМОГО:\n")
            f.write("=" * 70 + "\n\n")
            f.write(result["overview"] + "\n\n")
        else:
            f.write("ОБЩИЙ ОБЗОР: отсутствует (стратегия 'simple')\n\n")
        
        f.write("ДЕТАЛИ ПО ФАЙЛАМ:\n")
        f.write("=" * 70 + "\n\n")
        for i, file_summary in enumerate(result["file_summaries"], 1):
            f.write(f"📄 Файл {i}: {Path(file_summary['file']).name}\n")
            f.write(f"   Статус: {file_summary['status']}\n")
            if file_summary["status"] == "success":
                f.write(f"   Длина оригинала: {file_summary['original_length']} симв.\n")
                f.write(f"   Длина саммари: {file_summary['summary_length']} симв.\n")
                f.write(f"   Модель: {file_summary['model_used']}\n")
                f.write(f"   Саммари:\n{file_summary['summary']}\n")
            elif "error" in file_summary:
                f.write(f"   Ошибка: {file_summary['error']}\n")
            f.write("\n")
        
        f.write("=" * 70 + "\n")
        f.write("МЕТАДАННЫЕ:\n")
        f.write("=" * 70 + "\n")
        f.write(f"Всего файлов: {result['metadata']['total_files']}\n")
        f.write(f"Обработано: {result['metadata']['processed']}\n")
        f.write(f"Ошибок: {len(result['metadata']['failed'])}\n")
        f.write(f"Время обработки: {result['metadata']['processing_time']} сек\n")
    
    # Машинно-читаемый формат (JSON)
    json_path = output_dir / f"summary_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return report_path, json_path


def main():
    args = parse_args()
    
    # Загрузка конфигурации
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        sys.exit(1)
    
    # Переопределение параметров из аргументов
    if args.source:
        config.source_dir = args.source
    if args.output:
        config.output_dir = args.output
    if args.strategy:
        config.summarization.strategy = args.strategy
    
    # Инициализация фабрики
    factory = ComponentFactory(config)
    logger = factory.get_logger()
    
    # Вывод информации о запуске
    print("=" * 70)
    print("🚀 OCR-APP: СУММАРИЗАЦИЯ ДОКУМЕНТОВ")
    print("=" * 70)
    print(f"📁 Источник: {config.source_dir}")
    print(f"💾 Результаты: {config.output_dir}")
    print(f"🧠 Стратегия: {config.summarization.strategy}")
    print(f"⏱️  Пауза между файлами: {config.summarization.pause_between_files} сек")
    print("=" * 70 + "\n")
    
    # Проверка существования папки с документами
    source_path = Path(config.source_dir)
    if not source_path.exists() or not source_path.is_dir():
        print(f"❌ Папка не найдена: {source_path.resolve()}")
        sys.exit(1)
    
    # Создание движка и запуск суммаризации
    try:
        engine = factory.get_engine()
        logger.info(f"Запуск суммаризации папки: {source_path}")
        
        start_time = time.time()
        result = engine.summarize_folder(
            folder_path=source_path,
            recursive=config.extraction.recursive,
            pause_between_files=config.summarization.pause_between_files
        )
        elapsed = time.time() - start_time
        
        # Вывод результатов в консоль
        print("\n" + "=" * 70)
        print("✅ СУММАРИЗАЦИЯ ЗАВЕРШЕНА")
        print("=" * 70)
        print(f"📄 Обработано файлов: {result['metadata']['processed']} из {result['metadata']['total_files']}")
        print(f"⏱️  Время: {elapsed:.2f} сек")
        
        if result["overview"]:
            print("\n📊 ОБЩИЙ ОБЗОР СОДЕРЖИМОГО:")
            print("-" * 70)
            print(result["overview"])
            print("-" * 70)
        else:
            print("\nℹ️  Общий обзор отсутствует (стратегия 'simple')")
        
        # Сохранение результатов
        output_dir = factory.get_output_dir()
        report_path, json_path = save_results(result, output_dir, str(source_path))
        
        print("\n" + "=" * 70)
        print("💾 РЕЗУЛЬТАТЫ СОХРАНЕНЫ")
        print("=" * 70)
        print(f"📄 Текстовый отчёт: {report_path.name}")
        print(f"⚙️  JSON (машинный формат): {json_path.name}")
        print(f"📁 Директория: {output_dir}")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Обработка прервана пользователем")
        sys.exit(130)
    except Exception as e:
        logger.exception("Критическая ошибка при суммаризации")
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()