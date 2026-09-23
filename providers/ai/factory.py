import os


def get_ai_provider():
    provider = os.getenv("AI_PROVIDER", "none").lower()

    if provider == "none":
        from providers.ai.none import NoAIProvider
        return NoAIProvider()

    if provider == "gemini":
        from providers.ai.gemini import GeminiProvider
        return GeminiProvider()

    if provider == "bedrock":
        from providers.ai.bedrock import BedrockProvider
        return BedrockProvider()

    raise ValueError(
        f"Unsupported AI provider: {provider}"
    )
