"""Протоколы для клиентов суммаризации."""
from typing import Protocol, runtime_checkable, Any


@runtime_checkable
class SummarizationClientProtocol(Protocol):
    """
    Протокол для клиентов суммаризации.
    
    Любой класс, реализующий этот интерфейс, может создавать саммари текста
    независимо от провайдера (OpenRouter, локальная LLM, Azure OpenAI и т.д.).
    
    Примеры реализаций:
        - OpenRouterClient (через OpenRouter API)
        - LocalLlamaClient (через llama.cpp)
        - AzureOpenAIClient (через Azure OpenAI)
    """
    
    def summarize(
        self,
        text: str,
        max_length: int | None = None,
        temperature: float = 0.3,
        **kwargs
    ) -> dict[str, Any]:
        """
        Суммаризирует текст.
        
        Parameters
        ----------
        text : str
            Исходный текст для суммаризации.
        max_length : int, optional
            Максимальная длина результата в символах (реализация может игнорировать).
        temperature : float, optional
            Температура генерации (0.0–1.0). По умолчанию 0.3.
        **kwargs : dict
            Дополнительные параметры, специфичные для реализации
            (например, 'strategy' для выбора модели).
        
        Returns
        -------
        dict
            Единый формат ответа для всех реализаций:
            {
                "summary": str | None,       # Текст саммари или None при ошибке
                "model_used": str,           # Имя модели/провайдера
                "success": bool,             # True если суммаризация успешна
                "error": str | None,         # Сообщение об ошибке (если есть)
                "metadata": Dict[str, Any]   # Доп. данные: токены, время, обрезка и т.д.
            }
        
        Notes
        -----
        Реализация ДОЛЖНА возвращать единый формат ответа даже при ошибках.
        Не должна выбрасывать исключения — все ошибки инкапсулируются в 'error'.
        """
        ...