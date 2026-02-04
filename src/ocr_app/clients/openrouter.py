"""Клиент для работы с OpenRouter API — только проверенные бесплатные модели."""
import logging
import os
import time
from typing import Any

import requests
from pydantic import SecretStr
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ocr_app.protocols import LoggerProtocol, SummarizationClientProtocol

logger = logging.Logger('tries', logging.ERROR)

class OpenRouterClient(SummarizationClientProtocol):
    """
    Клиент для взаимодействия с OpenRouter API.
    
    Использует ТОЛЬКО проверенные бесплатные модели (февраль 2026).
    Автоматически обходит рейт-лимиты и недоступные эндпоинты.
    """
    
    # Проверенные БЕСПЛАТНЫЕ модели (без списания кредитов)
    MODEL_HIERARCHY = {
        "premium": [
            "nousresearch/hermes-3-llama-3.1-405b:free",  # Лучшее качество для русского
        ],
        "balanced": [
            "mistralai/mistral-7b-instruct:nitro"
            # "meta-llama/llama-3.3-70b-instruct:free",              # Хороший баланс
            # "meta-llama/llama-3.2-3b-instruct:free",                  # Стабильная, быстрая
            # "google/gemma-3n-e4b-it:free",
            # "deepseek/deepseek-r1-0528:free"
        ],
        "fast": [
            "mistralai/mistral-7b-instruct:nitro",        # Макс. скорость
            "google/gemma-2-9b-it:free",
        ]
    }
    
    # Консервативные лимиты контекста (в символах)
    MODEL_CONTEXT_LIMITS = {
        "meta-llama/llama-3.3-70b-instruct:free": 100_000,
        "meta-llama/llama-3.2-3b-instruct:free": 100_000,
        "google/gemma-3n-e4b-it:free": 6_000,
        "deepseek/deepseek-r1-0528:free": 100_000,
        "mistralai/mistral-7b-instruct:nitro": 28_000,
    }

    def __init__(
        self,
        logger: LoggerProtocol,
        api_key: SecretStr | str | None = None,
        app_name: str = "ocr-app",
        default_strategy: str = "balanced",
        request_delay: float = 5.0  # ⚠️ КРИТИЧНО: 5+ сек для бесплатных моделей
    ) -> None:
        """
        Инициализация клиента с консервативными настройками для бесплатного использования.
        
        Parameters
        ----------
        request_delay : float
            Задержка между запросами в секундах. Для бесплатных моделей рекомендуется 5.0+.
        """
        self.logger = logger
        
        if api_key is None:
            api_key = os.getenv("OPENROUTER_API_KEY")
        
        # Обработка случая, когда ключ пришёл как объект SecretStr
        if isinstance(api_key, SecretStr) and hasattr(api_key, 'get_secret_value'):
            api_key = api_key.get_secret_value()
        elif isinstance(api_key, str) and api_key.startswith("SecretStr("):
            # Защита от ошибки преобразования SecretStr в строку
            raise ValueError(
                "OPENROUTER_API_KEY передан как строка 'SecretStr(...)' вместо реального значения. "
                "Убедитесь, что в конфигурации используется .get_secret_value() или передаётся чистая строка."
            )
        
        if not api_key or (isinstance(api_key, str) and not api_key.startswith("sk-")):
            raise ValueError(
                "OPENROUTER_API_KEY недействителен. Убедитесь, что:\n"
                "  1. В .env есть строка: OPENROUTER_API_KEY=sk-or-v1-...\n"
                "  2. Ключ начинается с 'sk-'\n"
                f"  Текущее значение (первые 10 симв.): {str(api_key)[:10] if api_key else 'None'}"
            )
        
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY не найден. Укажите его в .env файле."
            )
        
        self.app_name = app_name
        self.default_strategy = default_strategy
        self.request_delay = request_delay
        self.last_request_time = 0.0
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {str(self.api_key)}",
            "HTTP-Referer": f"{app_name}.local",
            "X-Title": app_name,
            "Content-Type": "application/json"
        })
        
        self.logger.info(
            f"OpenRouter клиент инициализирован | Стратегия: '{default_strategy}' | "
            f"Задержка: {request_delay}s (обязательно для бесплатных моделей)"
        )

    def _enforce_rate_limit(self) -> None:
        """Строгая задержка между запросами для избежания 429 ошибок."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            sleep_time = self.request_delay - elapsed
            self.logger.debug(f"Ожидание {sleep_time:.1f}с для соблюдения рейт-лимита...")
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    @retry(
        stop=stop_after_attempt(2),  # Меньше попыток — быстрее фолбэк
        wait=wait_exponential(multiplier=1, min=8, max=20),  # Длинные задержки при ошибках
        retry=retry_if_exception_type((requests.exceptions.RequestException, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def _request(self, prompt: str, model: str, temperature: float = 0.3) -> str:
        """Выполняет запрос с защитой от рейт-лимитов."""
        self._enforce_rate_limit()
        
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": 1500
        }
        
        try:
            self.logger.info(f"→ Запрос к '{model}' ({len(prompt)} симв.)")
            response = self.session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=payload,
                timeout=120
            )
            
            # Обработка специфичных ошибок OpenRouter
            if response.status_code == 429:
                self.logger.warning(f"429 Rate limit для '{model}' — повтор через задержку")
                raise requests.exceptions.RequestException("Rate limit (429)")
            elif response.status_code == 402:
                self.logger.error("402 Payment Required — исчерпан лимит кредитов аккаунта")
                self.logger.error("Решение: используйте только 100% бесплатные модели (см. документацию)")
                raise requests.exceptions.RequestException("Credit limit exceeded (402)")
            elif response.status_code == 400 and "not a valid model ID" in response.text:
                self.logger.error(f"400 Неверный ID модели: '{model}'")
                self.logger.error("Модель недоступна бесплатно — переключаемся на фолбэк")
                raise requests.exceptions.RequestException("Invalid model ID (400)")
            elif response.status_code >= 400:
                self.logger.error(f"Ошибка API {response.status_code}: {response.text[:300]}")
                response.raise_for_status()
            
            result = response.json()
            if "choices" not in result or not result["choices"]:
                raise ValueError(f"Некорректный ответ API: {result}")
            
            answer = result["choices"][0]["message"]["content"].strip()
            self.logger.info(f"← Ответ от '{model}' получен ({len(answer)} симв.)")
            return answer
            
        except Exception as e:
            self.logger.error(f"Ошибка запроса к '{model}': {e}")
            raise

    def _prepare_prompt(self, text: str) -> str:
        """Промпт, оптимизированный для работы с шумным текстом от OCR."""
        return f"""Ты — эксперт по анализу документов на русском языке.
Текст может содержать артефакты распознавания: разорванные слова, лишние символы (|, #), опечатки.

Задача:
1. Проигнорируй мусорные символы и артефакты
2. Восстанови смысл там, где это возможно
3. Создай краткое саммари на русском языке
4. Выдели ключевые факты: даты, суммы, стороны, предмет документа
5. Ответ должен содержать ТОЛЬКО саммари, без вводных фраз

Текст:
{text}

Саммари:"""

    def summarize(
        self,
        text: str,
        max_length: int | None = None,
        strategy: str | None = None,
        temperature: float = 0.3,
        **kwargs
    ) -> dict[str, Any]:
        """
        Суммаризирует текст с фолбэком по моделям.
        
        Returns
        -------
        dict
            С результатами (см. описание в базовой версии)
        """
        strategy = strategy or self.default_strategy
        models_to_try = self.MODEL_HIERARCHY.get(strategy, self.MODEL_HIERARCHY["balanced"])
        
        # Ограничение контекста по первой модели
        context_limit = self.MODEL_CONTEXT_LIMITS.get(models_to_try[0], 25_000)
        truncated = False
        
        if len(text) > context_limit:
            # Сохраняем начало (заголовки) и конец (подписи) — там часто ключевая информация
            keep_start = min(15_000, int(context_limit * 0.6))
            keep_end = context_limit - keep_start - 100  # минус буфер под разделитель
            text = (
                text[:keep_start] +
                "\n\n[... ПРОПУЩЕНО ИЗ-ЗА ОГРАНИЧЕНИЯ КОНТЕКСТА ...]\n\n" +
                text[-keep_end:]
            )
            truncated = True
            self.logger.warning(f"Текст обрезан до {context_limit} симв. (было {len(text)})")
        
        prompt = self._prepare_prompt(text)
        last_error = None
        
        for i, model in enumerate(models_to_try):
            try:
                summary = self._request(prompt, model, temperature=temperature)
                summary = summary.lstrip("Саммари:").lstrip("Summary:").strip()
                
                return {
                    "summary": summary,
                    "model_used": model,
                    "success": True,
                    "fallback_used": i > 0,
                    "metadata": {
                        "fallback_used": i > 0,
                        "truncated": truncated,
                        "tokens_input": len(prompt) // 4,
                        "tokens_output": len(summary) // 4
                    },
                    "error": None
                }
                
            except Exception as e:
                last_error = str(e)
                self.logger.warning(f"Модель '{model}' недоступна: {e}")
                if i < len(models_to_try) - 1:
                    self.logger.info(f"Переключение на запасную модель: {models_to_try[i + 1]}")
                continue
        
        return {
            "summary": None,
            "model_used": models_to_try[0] if models_to_try else "unknown",
            "success": False,
            "fallback_used": True,
            "metadata": {
                "fallback_used": True,
                "truncated": truncated,
                "attempted_models": models_to_try
            },
            "error": f"Все модели недоступны. Последняя ошибка: {last_error}"
        }

    def get_available_models(self) -> list[str]:
        """Возвращает список проверенных бесплатных моделей."""
        models = set()
        for strategy_models in self.MODEL_HIERARCHY.values():
            models.update(strategy_models)
        return sorted(models)