import os
from dotenv import load_dotenv

load_dotenv()

# ========== TELEGRAM ==========
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_API_URL = os.getenv("TELEGRAM_API_URL", "https://api.telegram.org")
TELEGRAM_PROXY = os.getenv("TELEGRAM_PROXY", "")  # e.g. socks5://127.0.0.1:1080

# ========== APIFY (for X/Twitter and Reddit) ==========
APIFY_API_KEY = os.getenv("APIFY_API_KEY", "")

# ========== LLM PROVIDERS ==========
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "nvidia/llama-3.3-nemotron-super-49b-v1")

OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

LMSTUDIO_ENDPOINT = os.getenv("LMSTUDIO_ENDPOINT", "http://localhost:1234/v1")
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "llama-3.1-8b-instruct")

LLM_PROVIDER_ORDER = os.getenv(
    "LLM_PROVIDER_ORDER", "gemini,nvidia,openrouter,groq,ollama,lmstudio"
).split(",")

# ========== SOURCE OPTIONS ==========
# Twitter RSS is unreliable (most Nitter instances block RSS) - set to true if you want to try
ENABLE_RSS = os.getenv("ENABLE_RSS", "true").lower() == "true"
ENABLE_APIFY_TWITTER = os.getenv("ENABLE_APIFY_TWITTER", "false").lower() == "true"
# Reddit via direct JSON API is reliable
ENABLE_APIFY_REDDIT = os.getenv("ENABLE_APIFY_REDDIT", "true").lower() == "true"
ENABLE_HN = os.getenv("ENABLE_HN", "true").lower() == "true"
ENABLE_ARXIV = os.getenv("ENABLE_ARXIV", "true").lower() == "true"
ENABLE_GITHUB = os.getenv("ENABLE_GITHUB", "false").lower() == "true"
ENABLE_YOUTUBE = os.getenv("ENABLE_YOUTUBE", "true").lower() == "true"

# Fetch options (used by dispatcher)
FETCH_OPTIONS = {
    "rss": ENABLE_RSS,
    "apify_twitter": ENABLE_APIFY_TWITTER,
    "apify_reddit": ENABLE_APIFY_REDDIT,
    "hn": ENABLE_HN,
    "arxiv": ENABLE_ARXIV,
    "github": ENABLE_GITHUB,
    "youtube": ENABLE_YOUTUBE,
}

# ========== YOUTUBE DATA API ==========
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_CHANNELS = [
    c.strip() for c in os.getenv(
        "YOUTUBE_CHANNELS",
        "okaashish,vibhavsishty,vishnuvijayan,TinaHuang,"
        "PrasadTechInTelugu,rajshamani,RawTalksWithVK,"
        "VarunMayya,AishwaryaSrinivasan,IBMTechnology,"
        "huggingface,freecodecamp,AndrejKarpathy,"
        "TwoMinutePapers,YannicKilcher,lexfridman,sentdex"
    ).split(",") if c.strip()
]
YOUTUBE_FETCH_COMMENTS = os.getenv("YOUTUBE_FETCH_COMMENTS", "true").lower() == "true"
YOUTUBE_MAX_VIDEOS_PER_CHANNEL = int(os.getenv("YOUTUBE_MAX_VIDEOS_PER_CHANNEL", "5"))
YOUTUBE_TRANSCRIPT_LANG = os.getenv("YOUTUBE_TRANSCRIPT_LANG", "en")

# ========== RSS FEEDS (21+ sources) ==========
RSS_FEEDS = [
    # Top AI Labs & Companies
    "https://openai.com/blog/rss.xml",  # OpenAI
    "https://www.anthropic.com/rss.xml",  # Anthropic
    "https://blog.google/technology/ai/rss/",  # Google AI
    "https://huggingface.co/blog/feed.xml",  # HuggingFace
    "https://mistral.ai/news/feed.xml",  # Mistral AI
    "https://nv-blogs.s3.amazonaws.com/rss.xml",  # NVIDIA
    "https://about.meta.com/blog/rss/",  # Meta AI
    "https://x.ai/blog/rss",  # xAI (Grok)
    "https://stability.ai/news/feed.xml",  # Stability AI
    "https://cohere.com/blog/rss.xml",  # Cohere
    "https://deepmind.google/blog/rss",  # DeepMind
    # Tech News
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
    # Research
    "https://www.technologyreview.com/feed/",
    "https://www.wired.com/feed/tag/ai/latest/rss",
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://www.marktechpost.com/feed/",
    "https://the-decoder.com/feed/",
]

# ========== APIFY TARGETS ==========
TWITTER_ACCOUNTS = os.getenv(
    "TWITTER_ACCOUNTS", "sama,elonmusk,satyanadella,ylecun"
).split(",")
REDDIT_SUBREDDITS = os.getenv(
    "REDDIT_SUBREDDITS", "MachineLearning,artificial,OpenAI"
).split(",")

# ========== HACKER NEWS ==========
HN_TAG = os.getenv("HN_TAG", "ai")

# ========== ARXIV CATEGORIES ==========
ARXIV_CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "cs.CV", "stat.ML"]

# ========== SCHEDULING & PERFORMANCE ==========
FETCH_INTERVAL_MINUTES = int(os.getenv("FETCH_INTERVAL_MINUTES", "30"))
MAX_LATENCY_SECONDS = int(os.getenv("MAX_LATENCY_SECONDS", "60"))
MIN_THROUGHPUT = int(os.getenv("MIN_THROUGHPUT", "1"))  # messages per minute target
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "3"))  # Lowered to conserve LLM quota
MAX_ARTICLES_PER_RUN = int(os.getenv("MAX_ARTICLES_PER_RUN", "10"))
MIN_RELEVANCE_SCORE = int(os.getenv("MIN_RELEVANCE_SCORE", "5"))

# ========== PATHS ==========
DATA_DIR = "data"
LOG_DIR = "logs"
LOG_FILE = f"{LOG_DIR}/run.log"
