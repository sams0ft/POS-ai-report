"""Cliente unificado para LLMs (Gemini Flash + Claude Sonnet + LM Studio)."""

from abc import ABC, abstractmethod

import httpx

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
            "max_tokens": 2048,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


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


class ClaudeClient(BaseLLMClient):
    """Cliente para Claude Sonnet 4.6 (reportes premium)."""

    def __init__(self):
        # TODO: inicializar anthropic.AsyncAnthropic con settings.anthropic_api_key
        self.model_name = "claude-sonnet-4-6-20250514"

    async def generate(self, prompt: str, system: str = "") -> str:
        """Genera texto con Claude Sonnet."""
        # TODO: implementar llamada a Anthropic API
        # import anthropic
        # client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        # message = await client.messages.create(
        #     model=self.model_name,
        #     max_tokens=2048,
        #     system=system,
        #     messages=[{"role": "user", "content": prompt}],
        # )
        # return message.content[0].text
        raise NotImplementedError("Pendiente: implementar Claude client")
