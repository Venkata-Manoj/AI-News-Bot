"""Test LLM provider configuration and availability."""

import sys

sys.path.insert(0, ".")

import config
from modules import llm


def check_providers():
    print("=" * 50)
    print("LLM Provider Configuration Check")
    print("=" * 50)

    # Initialize providers
    llm.init_providers()

    providers = [
        ("GEMINI", config.GEMINI_API_KEY, config.GEMINI_MODEL),
        ("NVIDIA", config.NVIDIA_API_KEY, config.NVIDIA_MODEL),
        ("OPENROUTER", config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL),
        ("GROQ", config.GROQ_API_KEY, config.GROQ_MODEL),
        ("OLLAMA", config.OLLAMA_ENDPOINT, config.OLLAMA_MODEL),
    ]

    available = []
    for name, key, model in providers:
        if key:
            print(f"✅ {name}: Configured (model: {model})")
            available.append(name.lower())
        else:
            print(f"❌ {name}: Not configured")

    print(f"\nAvailable providers: {available}")
    print(f"Fallback order: {config.LLM_PROVIDER_ORDER}")

    # Check which in order are actually available
    working = []
    for p in config.LLM_PROVIDER_ORDER:
        if p in available:
            working.append(p)

    print(f"Working providers in order: {working}")

    if not working:
        print("\n⚠️ No LLM providers configured!")
        print("Add at least one API key to your .env file:")
        print("  - GEMINI_API_KEY (free tier: 20 req/day)")
        print("  - NVIDIA_API_KEY (free tier available)")
        print("  - OPENROUTER_API_KEY (free tier available)")
        print("  - GROQ_API_KEY (free tier available)")
    else:
        print(f"\n✅ {len(working)} provider(s) available for fallback")


if __name__ == "__main__":
    check_providers()
