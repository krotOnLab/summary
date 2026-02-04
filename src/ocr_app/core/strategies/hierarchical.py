"""Иерархическая стратегия суммаризации: файлы → агрегация."""
import time
from pathlib import Path
from typing import Any
from ocr_app.core.strategies.base import BaseSummarizationStrategy


class HierarchicalSummarizationStrategy(BaseSummarizationStrategy):
    """
    Стратегия иерархической суммаризации.
    
    Алгоритм:
        1. Суммаризация каждого файла отдельно
        2. Агрегация всех саммари в единый обзор содержимого папки
    
    Подходит для:
        - Папок с разнородными документами
        - Сценариев, где важен общий контекст коллекции документов
    """
    
    def __init__(self, extractor, client, min_files_for_aggregation: int = 2) -> None:
        """
        Parameters
        ----------
        min_files_for_aggregation : int, optional
            Минимальное количество файлов для запуска агрегации (по умолчанию 2).
            Если файлов меньше — возвращается только список саммари без общего обзора.
        """
        super().__init__(extractor, client)
        self.min_files_for_aggregation = min_files_for_aggregation
    
    def summarize_folder(
        self,
        folder_path: str | Path,
        recursive: bool = True,
        pause_between_files: float = 2.0,
        **kwargs
    ) -> dict[str, Any]:
        start_time = time.time()
        folder = Path(folder_path)
        
        if not folder.exists() or not folder.is_dir():
            raise ValueError(f"Папка не найдена: {folder_path}")
        
        # Извлечение всех файлов
        pattern = "**/*" if recursive else "*"
        all_files = [f for f in folder.glob(pattern) if f.is_file()]
        
        # Фильтрация по поддерживаемым расширениям
        supported_exts = set(self.extractor.supported_extensions)
        target_files = [
            f for f in all_files 
            if f.suffix.lower() in supported_exts
        ]
        
        if not target_files:
            return self._build_empty_result(folder, start_time)
        
        # Обработка каждого файла
        file_summaries = []
        failed_files = []
        
        for i, file_path in enumerate(target_files, 1):
            summary = self._summarize_single_file(file_path)
            file_summaries.append(summary)
            
            if summary["status"] != "success":
                failed_files.append(str(file_path.relative_to(folder)))
            
            # Пауза между файлами для соблюдения рейт-лимитов
            if i < len(target_files) and pause_between_files > 0:
                time.sleep(pause_between_files)
        
        # Агрегация в единый обзор (если достаточно файлов)
        overview = None
        if len([s for s in file_summaries if s["status"] == "success"]) >= self.min_files_for_aggregation:
            overview = self._aggregate_summaries(file_summaries)
        
        return self._build_result(
            folder=folder,
            file_summaries=file_summaries,
            overview=overview,
            failed_files=failed_files,
            processing_time=time.time() - start_time
        )
    
    def _summarize_single_file(self, file_path: Path) -> dict[str, Any]:
        """Суммаризирует один файл."""
        text = self.extractor.extract_file(str(file_path))
        
        if not text.strip():
            return {
                "file": str(file_path),
                "status": "empty",
                "summary": None,
                "original_length": 0,
                "summary_length": 0
            }
        
        result = self.client.summarize(text, temperature=0.3)
        
        if result["success"] and result["summary"]:
            return {
                "file": str(file_path),
                "status": "success",
                "summary": result["summary"],
                "model_used": result["model_used"],
                "original_length": len(text),
                "summary_length": len(result["summary"]),
                "metadata": result.get("metadata", {})
            }
        else:
            return {
                "file": str(file_path),
                "status": "error",
                "error": result.get("error", "Неизвестная ошибка"),
                "summary": None,
                "original_length": len(text),
                "summary_length": 0,
                "metadata": result.get("metadata", {})
            }
    
    def _aggregate_summaries(self, file_summaries: list[dict[str, Any]]) -> str | None:
        """Агрегирует успешные саммари в единый обзор."""
        successful = [
            s for s in file_summaries 
            if s["status"] == "success" and s["summary"]
        ]
        
        if not successful:
            return None
        
        # Формируем текст для агрегации
        aggregation_text = "Саммари отдельных документов:\n\n"
        for i, summary in enumerate(successful, 1):
            filename = Path(summary["file"]).name
            aggregation_text += f"Документ {i} ({filename}):\n{summary['summary']}\n\n"
        
        result = self.client.summarize(aggregation_text, temperature=0.4)
        
        if result["success"] and result["summary"]:
            return result["summary"]
        else:
            return (
                f"Не удалось создать общий обзор.\n"
                f"Причина: {result.get('error', 'неизвестно')}"
            )
    
    def _build_empty_result(self, folder: Path, start_time: float) -> dict[str, Any]:
        """Строит результат для пустой папки."""
        return {
            "overview": "В папке не найдено поддерживаемых документов (.pdf, .jpg, .webp и др.)",
            "file_summaries": [],
            "metadata": {
                "strategy": self.get_strategy_name(),
                "strategy_description": self.get_strategy_description(),
                "folder": str(folder),
                "total_files": 0,
                "processed": 0,
                "failed": [],
                "processing_time": round(time.time() - start_time, 2)
            }
        }
    
    def _build_result(
        self,
        folder: Path,
        file_summaries: list[dict[str, Any]],
        overview: str | None,
        failed_files: list[str],
        processing_time: float
    ) -> dict[str, Any]:
        """Строит финальный результат в едином формате."""
        successful_count = sum(1 for s in file_summaries if s["status"] == "success")
        
        return {
            "overview": overview,
            "file_summaries": file_summaries,
            "metadata": {
                "strategy": self.get_strategy_name(),
                "strategy_description": self.get_strategy_description(),
                "folder": str(folder),
                "total_files": len(file_summaries),
                "processed": successful_count,
                "failed": failed_files,
                "processing_time": round(processing_time, 2)
            }
        }
    
    def get_strategy_name(self) -> str:
        return "hierarchical"
    
    def get_strategy_description(self) -> str:
        return (
            "Иерархическая суммаризация: каждый файл суммаризируется отдельно, "
            "затем все саммари агрегируются в единый обзор содержимого папки."
        )