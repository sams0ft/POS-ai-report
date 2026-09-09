"""Cliente unificado para LLMs (Gemini Flash + Claude Sonnet + OpenAI + LM Studio)."""

from abc import ABC, abstractmethod

import httpx
from openai import AsyncOpenAI

from app.core.config import get_settings

settings = get_settings()


class BaseLLMClient(ABC):
    """Interfaz base para clientes LLM."""

    @abstractmethod
    async def generate(self, prompt: str, system: str = "") -> str:
        """Genera texto a partir de un prompt."""
        ...


class LMStudioClient(BaseLLMClient):
    """Cliente para LM Studio (servidor local, API compatible con OpenAI).

    Usado en desarrollo cuando USE_LMSTUDIO=true en .env.
    Reemplaza tanto Gemini como Claude con el modelo local configurado.
    """

    def __init__(self):
        self.base_url = settings.lmstudio_url.rstrip("/")
        self.model = settings.lmstudio_model

    async def generate(self, prompt: str, system: str = "") -> str:
        """Genera texto llamando al endpoint /v1/chat/completions de LM Studio."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 4096,
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            message = data["choices"][0]["message"]
            # Modelos con reasoning (ej: Gemma 4) ponen la respuesta en
            # reasoning_content cuando content viene vacío
            return message.get("content") or message.get("reasoning_content", "")


class GeminiClient(BaseLLMClient):
    """Cliente para Google Gemini 2.5 Flash (reportes rutinarios)."""

    def __init__(self):
        # TODO: inicializar google.genai con settings.gemini_api_key
        self.model_name = "gemini-2.5-flash"

    async def generate(self, prompt: str, system: str = "") -> str:
        """Genera texto con Gemini Flash."""
        # TODO: implementar llamada a Gemini API
        # from google import genai
        # client = genai.Client(api_key=settings.gemini_api_key)
        # response = await client.aio.models.generate_content(
        #     model=self.model_name,
        #     contents=prompt,
        #     config=genai.types.GenerateContentConfig(
        #         system_instruction=system,
        #         temperature=0.3,
        #     ),
        # )
        # return response.text
        raise NotImplementedError("Pendiente: implementar Gemini client")


class OpenAIClient(BaseLLMClient):
    """Cliente para OpenAI (GPT-4o por defecto)."""

    def __init__(self):
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    async def generate(self, prompt: str, system: str = "") -> str:
        """Genera texto con OpenAI."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
        )
        return response.choices[0].message.content


class ClaudeClient(BaseLLMClient):
    """Cliente para Claude Sonnet 4.6 (reportes premium)."""

    def __init__(self):
        import anthropic
        self._anthropic = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model_name = "claude-sonnet-4-6-20250514"

    async def generate(self, prompt: str, system: str = "") -> str:
        """Genera texto con Claude Sonnet."""
        kwargs = {
            "model": self.model_name,
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        message = await self._anthropic.messages.create(**kwargs)
        return message.content[0].text
