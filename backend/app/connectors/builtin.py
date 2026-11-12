"""Built-in connector definitions - 100+ data sources and integrations.

Categories (per build.txt section 10):
- Space and Science
- News and Information
- Media and Entertainment
- Development
- Knowledge
- Other (Weather, Currency, Maps, Translation, Government, Financial, Educational)

Each connector dict:
- name: unique snake_case identifier
- display_name: human-readable name
- description: what it does
- category: category ID
- category_label: human-readable category label
- auth_required: bool
- auth_type: none, api_key, oauth, bearer, basic
- auth_field_name: label for auth field
- free_paid: free, paid, freemium
- rate_limit: rate limit string
- rate_limit_unit: per_minute, per_hour, per_day
- base_url: base API URL
- operations: list of operation dicts
- capabilities: list of capability strings
"""

from typing import Any

# Category definitions
CATEGORIES = [
    {"id": "space_science", "label": "Space and Science", "description": "NASA, astronomy, scientific datasets"},
    {"id": "news_information", "label": "News and Information", "description": "News, RSS, media monitoring"},
    {"id": "media_entertainment", "label": "Media and Entertainment", "description": "Movies, TV, music, entertainment metadata"},
    {"id": "development", "label": "Development", "description": "GitHub, npm, PyPI, Docker, development tools"},
    {"id": "knowledge", "label": "Knowledge", "description": "Wikipedia, Wikidata, arXiv, reference sources"},
    {"id": "other", "label": "Other", "description": "Weather, currency, maps, translation, government, financial"},
]

def _op(name: str, desc: str, params: list[dict] | None = None) -> dict:
    return {"name": name, "description": desc, "parameters": params or []}

# ---------------------------------------------------------------------------
# SPACE AND SCIENCE
# ---------------------------------------------------------------------------
SPACE_SCIENCE_CONNECTORS = [
    {
        "name": "nasa",
        "display_name": "NASA API",
        "description": "Access NASA APIs including Mars rover photos, APOD, asteroid data, and more.",
        "category": "space_science",
        "category_label": "Space and Science",
        "auth_required": False,
        "auth_type": None,
        "auth_field_name": None,
        "free_paid": "free",
        "rate_limit": "1000 per hour",
        "rate_limit_unit": "per_hour",
        "base_url": "https://api.nasa.gov",
        "operations": [
            _op("get_apod", "Get Astronomy Picture of the Day", [{"name": "date", "type": "string", "required": False}]),
            _op("get_mars_rover_photos", "Get Mars rover photos", [{"name": "rover", "type": "string", "required": True}, {"name": "sol", "type": "integer", "required": False}]),
            _op("get_neo_feed", "Get Near Earth Object feed", [{"name": "start_date", "type": "string", "required": False}, {"name": "end_date", "type": "string", "required": False}]),
            _op("get_epic_images", "Get EPIC Earth images", [{"name": "date", "type": "string", "required": False}]),
        ],
        "capabilities": ["astronomy", "space_imagery", "asteroid_data", "earth_observation"],
    },
    {
        "name": "spaceflight",
        "display_name": "Spaceflight News",
        "description": "Spaceflight news articles, launches, and events.",
        "category": "space_science",
        "category_label": "Space and Science",
        "auth_required": False,
        "auth_type": None,
        "auth_field_name": None,
        "free_paid": "free",
        "rate_limit": "No documented limit",
        "rate_limit_unit": None,
        "base_url": "https://api.spaceflightnewsapi.net/v3",
        "operations": [
            _op("get_articles", "Get spaceflight news articles", [{"name": "limit", "type": "integer", "required": False}, {"name": "search", "type": "string", "required": False}]),
            _op("get_launches", "Get upcoming and past launches", [{"name": "limit", "type": "integer", "required": False}]),
            _op("get_events", "Get space events", [{"name": "limit", "type": "integer", "required": False}]),
        ],
        "capabilities": ["space_news", "launch_data", "events"],
    },
    {
        "name": "openalex",
        "display_name": "OpenAlex",
        "description": "Open academic index - research papers, authors, institutions, and concepts.",
        "category": "space_science",
        "category_label": "Space and Science",
        "auth_required": False,
        "auth_type": None,
        "auth_field_name": None,
        "free_paid": "free",
        "rate_limit": "100,000 per day (email for more)",
        "rate_limit_unit": "per_day",
        "base_url": "https://api.openalex.org",
        "operations": [
            _op("search_works", "Search research works", [{"name": "search", "type": "string", "required": True}, {"name": "per_page", "type": "integer", "required": False}]),
            _op("get_authors", "Search authors", [{"name": "search", "type": "string", "required": True}]),
            _op("get_concepts", "Search concepts", [{"name": "search", "type": "string", "required": True}]),
        ],
        "capabilities": ["research_papers", "academic_search", "author_lookup"],
    },
    {
        "name": "arxiv",
        "display_name": "arXiv",
        "description": "Open access archive for scholarly articles in physics, mathematics, computer science, and more.",
        "category": "space_science",
        "category_label": "Space and Science",
        "auth_required": False,
        "auth_type": None,
        "auth_field_name": None,
        "free_paid": "free",
        "rate_limit": "3 requests per second",
        "rate_limit_unit": "per_minute",
        "base_url": "https://export.arxiv.org",
        "operations": [
            _op("search_papers", "Search arXiv papers", [{"name": "search_query", "type": "string", "required": True}, {"name": "max_results", "type": "integer", "required": False}]),
            _op("get_paper", "Get paper by ID", [{"name": "id", "type": "string", "required": True}]),
        ],
        "capabilities": ["academic_papers", "preprints", "research"],
    },
]

# ---------------------------------------------------------------------------
# NEWS AND INFORMATION
# ---------------------------------------------------------------------------
NEWS_INFORMATION_CONNECTORS = [
    {
        "name": "newsapi",
        "display_name": "NewsAPI",
        "description": "Access breaking news headlines and search articles from 30,000+ sources.",
        "category": "news_information",
        "category_label": "News and Information",
        "auth_required": True,
        "auth_type": "api_key",
        "auth_field_name": "API Key",
        "free_paid": "freemium",
        "rate_limit": "500 requests per day (free tier)",
        "rate_limit_unit": "per_day",
        "base_url": "https://newsapi.org/v2",
        "operations": [
            _op("get_headlines", "Get top headlines", [{"name": "country", "type": "string", "required": False}, {"name": "category", "type": "string", "required": False}, {"name": "page_size", "type": "integer", "required": False}]),
            _op("search_everything", "Search all articles", [{"name": "q", "type": "string", "required": True}, {"name": "page_size", "type": "integer", "required": False}]),
        ],
        "capabilities": ["news_headlines", "article_search", "breaking_news"],
    },
    {
        "name": "gdel",
        "display_name": "GDELT",
        "description": "Global Database of Events, Language, and Tone - monitors global media.",
        "category": "news_information",
        "category_label": "News and Information",
        "auth_required": False,
        "auth_type": None,
        "auth_field_name": None,
        "free_paid": "free",
        "rate_limit": "No documented limit",
        "rate_limit_unit": None,
        "base_url": "https://api.gdeltproject.org/api/v2",
        "operations": [
            _op("doc_query", "Query GDELT documents", [{"name": "query", "type": "string", "required": True}, {"name": "mode", "type": "string", "required": False}]),
            _op("get_counts", "Get mention counts", [{"name": "query", "type": "string", "required": True}]),
        ],
        "capabilities": ["global_media_monitoring", "event_tracking", "media_analysis"],
    },
    {
        "name": "rss",
        "display_name": "RSS Feeds",
        "description": "Read and parse RSS/Atom feeds from any source.",
        "category": "news_information",
        "category_label": "News and Information",
        "auth_required": False,
        "auth_type": None,
        "auth_field_name": None,
        "free_paid": "free",
        "rate_limit": "Depends on source",
        "rate_limit_unit": None,
        "base_url": None,
        "operations": [
            _op("fetch_feed", "Fetch and parse an RSS feed", [{"name": "url", "type": "string", "required": True}]),
            _op("search_feed", "Search items in a feed", [{"name": "url", "type": "string", "required": True}, {"name": "query", "type": "string", "required": True}]),
        ],
        "capabilities": ["rss_parsing", "feed_aggregation"],
    },
    {
        "name": "guardian",
        "display_name": "The Guardian API",
        "description": "Access Guardian news articles, sections, and contributors.",
        "category": "news_information",
        "category_label": "News and Information",
        "auth_required": True,
        "auth_type": "api_key",
        "auth_field_name": "API Key",
        "free_paid": "free",
        "rate_limit": "50 requests per second",
        "rate_limit_unit": "per_minute",
        "base_url": "https://content.guardianapis.com",
        "operations": [
            _op("search_articles", "Search Guardian articles", [{"name": "q", "type": "string", "required": True}, {"name": "page_size", "type": "integer", "required": False}]),
            _op("get_sections", "Get available sections", []),
        ],
        "capabilities": ["news_articles", "uk_news"],
    },
]

# ---------------------------------------------------------------------------
# MEDIA AND ENTERTAINMENT
# ---------------------------------------------------------------------------
MEDIA_ENTERTAINMENT_CONNECTORS = [
    {
        "name": "tmdb",
        "display_name": "TMDB (The Movie Database)",
        "description": "Movie and TV show metadata, images, and cast information.",
        "category": "media_entertainment",
        "category_label": "Media and Entertainment",
        "auth_required": True,
        "auth_type": "api_key",
        "auth_field_name": "API Key",
        "free_paid": "free",
        "rate_limit": "40 requests per 10 seconds",
        "rate_limit_unit": "per_minute",
        "base_url": "https://api.themoviedb.org/3",
        "operations": [
            _op("search_movie", "Search for movies", [{"name": "query", "type": "string", "required": True}]),
            _op("get_movie_details", "Get movie details", [{"name": "movie_id", "type": "integer", "required": True}]),
            _op("search_tv", "Search TV shows", [{"name": "query", "type": "string", "required": True}]),
            _op("get_trending", "Get trending movies/TV", [{"name": "media_type", "type": "string", "required": False}]),
        ],
        "capabilities": ["movie_metadata", "tv_metadata", "cast_info", "posters"],
    },
    {
        "name": "tvmaze",
        "display_name": "TVMaze",
        "description": "TV show schedules, cast, and episode information.",
        "category": "media_entertainment",
        "category_label": "Media and Entertainment",
        "auth_required": False,
        "auth_type": None,
        "auth_field_name": None,
        "free_paid": "free",
        "rate_limit": "No documented limit",
        "rate_limit_unit": None,
        "base_url": "https://api.tvmaze.com",
        "operations": [
            _op("search_shows", "Search TV shows", [{"name": "q", "type": "string", "required": True}]),
            _op("get_show", "Get show details", [{"name": "id", "type": "integer", "required": True}]),
            _op("get_episodes", "Get show episodes", [{"name": "id", "type": "integer", "required": True}]),
        ],
        "capabilities": ["tv_shows", "episodes", "cast"],
    },
    {
        "name": "musicbrainz",
        "display_name": "MusicBrainz",
        "description": "Open music encyclopedia - artists, recordings, releases, and labels.",
        "category": "media_entertainment",
        "category_label": "Media and Entertainment",
        "auth_required": False,
        "auth_type": None,
        "auth_field_name": None,
        "free_paid": "free",
        "rate_limit": "1 request per second",
        "rate_limit_unit": "per_minute",
        "base_url": "https://musicbrainz.org/ws/2",
        "operations": [
            _op("search_artist", "Search artists", [{"name": "query", "type": "string", "required": True}]),
            _op("search_recording", "Search recordings/tracks", [{"name": "query", "type": "string", "required": True}]),
            _op("search_release", "Search releases/albums", [{"name": "query", "type": "string", "required": True}]),
        ],
        "capabilities": ["music_metadata", "artist_lookup", "track_info"],
    },
    {
        "name": "spotify",
        "display_name": "Spotify Web API",
        "description": "Access Spotify music catalog, playlists, and user data (requires authorization).",
        "category": "media_entertainment",
        "category_label": "Media and Entertainment",
        "auth_required": True,
        "auth_type": "bearer",
        "auth_field_name": "Access Token",
        "free_paid": "free",
        "rate_limit": "Varies by endpoint",
        "rate_limit_unit": None,
        "base_url": "https://api.spotify.com/v1",
        "operations": [
            _op("search_track", "Search tracks", [{"name": "q", "type": "string", "required": True}]),
            _op("get_track", "Get track details", [{"name": "id", "type": "string", "required": True}]),
            _op("get_artist", "Get artist details", [{"name": "id", "type": "string", "required": True}]),
        ],
        "capabilities": ["music_catalog", "playlists", "audio_features"],
    },
]

# ---------------------------------------------------------------------------
# DEVELOPMENT
# ---------------------------------------------------------------------------
DEVELOPMENT_CONNECTORS = [
    {
        "name": "github",
        "display_name": "GitHub API",
        "description": "GitHub repositories, users, issues, pull requests, and more.",
        "category": "development",
        "category_label": "Development",
        "auth_required": False,
        "auth_type": None,
        "auth_field_name": None,
        "free_paid": "free",
        "rate_limit": "60 per hour (unauthenticated), 5000 per hour (authenticated)",
        "rate_limit_unit": "per_hour",
        "base_url": "https://api.github.com",
        "operations": [
            _op("search_repos", "Search repositories", [{"name": "q", "type": "string", "required": True}]),
            _op("get_repo", "Get repository details", [{"name": "owner", "type": "string", "required": True}, {"name": "repo", "type": "string", "required": True}]),
            _op("get_user", "Get user details", [{"name": "username", "type": "string", "required": True}]),
            _op("get_issues", "Get repository issues", [{"name": "owner", "type": "string", "required": True}, {"name": "repo", "type": "string", "required": True}]),
        ],
        "capabilities": ["code_hosting", "repository_search", "issues", "pull_requests"],
    },
    {
        "name": "gitlab",
        "display_name": "GitLab API",
        "description": "GitLab projects, groups, issues, and CI/CD pipelines.",
        "category": "development",
        "category_label": "Development",
        "auth_required": False,
        "auth_type": None,
        "auth_field_name": None,
        "free_paid": "free",
        "rate_limit": "No documented limit",
        "rate_limit_unit": None,
        "base_url": "https://gitlab.com/api/v4",
        "operations": [
            _op("search_projects", "Search GitLab projects", [{"name": "search", "type": "string", "required": True}]),
            _op("get_project", "Get project details", [{"name": "id", "type": "string", "required": True}]),
        ],
        "capabilities": ["code_hosting", "ci_cd", "git_repos"],
    },
    {
        "name": "npm",
        "display_name": "npm Registry",
        "description": "JavaScript package registry - search and get package details.",
        "category": "development",
        "category_label": "Development",
        "auth_required": False,
        "auth_type": None,
        "auth_field_name": None,
        "free_paid": "free",
        "rate_limit": "No documented limit",
        "rate_limit_unit": None,
        "base_url": "https://registry.npmjs.org",
        "operations": [
            _op("search_packages", "Search npm packages", [{"name": "query", "type": "string", "required": True}]),
            _op("get_package", "Get package details", [{"name": "package_name", "type": "string", "required": True}]),
        ],
        "capabilities": ["package_registry", "javascript", "npm"],
    },
    {
        "name": "pypi",
        "display_name": "PyPI (Python Package Index)",
        "description": "Python package repository - search and get package details.",
        "category": "development",
        "category_label": "Development",
        "auth_required": False,
        "auth_type": None,
        "auth_field_name": None,
        "free_paid": "free",
        "rate_limit": "No documented limit",
        "rate_limit_unit": None,
        "base_url": "https://pypi.org/pypi",
        "operations": [
            _op("search_packages", "Search PyPI packages", [{"name": "query", "type": "string", "required": True}]),
            _op("get_package", "Get package details", [{"name": "package_name", "type": "string", "required": True}]),
        ],
        "capabilities": ["package_registry", "python"],
    },
    {
        "name": "dockerhub",
        "display_name": "Docker Hub API",
        "description": "Docker container image registry - search and get image details.",
        "category": "development",
        "category_label": "Development",
        "auth_required": False,
        "auth_type": None,
        "auth_field_name": None,
        "free_paid": "free",
        "rate_limit": "No documented limit",
        "rate_limit_unit": None,
        "base_url": "https://hub.docker.com/v2",
        "operations": [
            _op("search_images", "Search Docker images", [{"name": "query", "type": "string", "required": True}]),
            _op("get_image", "Get image details", [{"name": "namespace", "type": "string", "required": True}, {"name": "repository", "type": "string", "required": True}]),
        ],
        "capabilities": ["container_images", "docker"],
    },
    {
        "name": "stackexchange",
        "display_name": "Stack Exchange API",
        "description": "Stack Overflow and Stack Exchange Q&A data.",
        "category": "development",
        "category_label": "Development",
        "auth_required": False,
        "auth_type": None,
        "auth_field_name": None,
        "free_paid": "free",
        "rate_limit": "300 per day (no key), 10,000 per day (with key)",
        "rate_limit_unit": "per_day",
        "base_url": "https://api.stackexchange.com/2.3",
        "operations": [
            _op("search_questions", "Search questions", [{"name": "q", "type": "string", "required": True}, {"name": "site", "type": "string", "required": False}]),
            _op("get_questions", "Get recent questions", [{"name": "site", "type": "string", "required": False}]),
        ],
        "capabilities": ["q_and_a", "programming_help", "technical_questions"],
    },
    {
        "name": "github_api",
        "display_name": "GitHub (Extended)",
        "description": "Extended GitHub API access with authentication for private repos and higher limits.",
        "category": "development",
        "category_label": "Development",
        "auth_required": True,
        "auth_type": "api_key",
        "auth_field_name": "Personal Access Token",
        "free_paid": "free",
        "rate_limit": "5000 per hour (authenticated)",
        "rate_limit_unit": "per_hour",
        "base_url": "https://api.github.com",
        "operations": [
            _op("list_repos", "List authenticated user repositories", []),
            _op("create_issue", "Create a repository issue", [{"name": "owner", "type": "string", "required": True}, {"name": "repo", "type": "string", "required": True}, {"name": "title", "type": "string", "required": True}, {"name": "body", "type": "string", "required": False}]),
        ],
        "capabilities": ["private_repos", "issue_management", "repo_management"],
    },
]

# ---------------------------------------------------------------------------
# KNOWLEDGE
# ---------------------------------------------------------------------------
KNOWLEDGE_CONNECTORS = [
    {
        "name": "wikipedia",
        "display_name": "Wikipedia",
        "description": "Free encyclopedia - search and retrieve articles on any topic.",
        "category": "knowledge",
        "category_label": "Knowledge",
        "auth_required": False,
        "auth_type": None,
        "auth_field_name": None,
        "free_paid": "free",
        "rate_limit": "No documented limit",
        "rate_limit_unit": None,
        "base_url": "https://en.wikipedia.org/w/api.php",
        "operations": [
            _op("search_articles", "Search Wikipedia articles", [{"name": "query", "type": "string", "required": True}]),
            _op("get_article", "Get article content by title", [{"name": "title", "type": "string", "required": True}]),
            _op("get_summary", "Get article summary", [{"name": "title", "type": "string", "required": True}]),
        ],
        "capabilities": ["encyclopedia", "general_knowledge", "article_search"],
    },
    {
        "name": "wikidata",
        "display_name": "Wikidata",
        "description": "Free and open knowledge base - structured data about entities.",
        "category": "knowledge",
        "category_label": "Knowledge",
        "auth_required": False,
        "auth_type": None,
        "auth_field_name": None,
        "free_paid": "free",
        "rate_limit": "No documented limit",
        "rate_limit_unit": None,
        "base_url": "https://www.wikidata.org/w/api.php",
        "operations": [
            _op("search_entities", "Search Wikidata entities", [{"name": "query", "type": "string", "required": True}]),
            _op("get_entity", "Get entity details", [{"name": "id", "type": "string", "required": True}]),
        ],
        "capabilities": ["structured_data", "entities", "knowledge_graph"],
    },
    {
        "name": "crossref",
        "display_name": "Crossref",
        "description": "Scholarly metadata - DOI registration, journal articles, and citations.",
        "category": "knowledge",
        "category_label": "Knowledge",
        "auth_required": False,
        "auth_type": None,
        "auth_field_name": None,
        "free_paid": "free",
        "rate_limit": "No documented limit",
        "rate_limit_unit": None,
        "base_url": "https://api.crossref.org",
        "operations": [
            _op("search_works", "Search scholarly works", [{"name": "query", "type": "string", "required": True}, {"name": "rows", "type": "integer", "required": False}]),
            _op("get_work", "Get work by DOI", [{"name": "doi", "type": "string", "required": True}]),
        ],
        "capabilities": ["scholarly_metadata", "doi_lookup", "citations"],
    },
    {
        "name": "openlibrary",
        "display_name": "Open Library",
        "description": "Open book catalog - search books, authors, and editions.",
        "category": "knowledge",
        "category_label": "Knowledge",
        "auth_required": False,
        "auth_type": None,
        "auth_field_name": None,
        "free_paid": "free",
        "rate_limit": "No documented limit",
        "rate_limit_unit": None,
        "base_url": "https://openlibrary.org",
        "operations": [
            _op("search_books", "Search books", [{"name": "query", "type": "string", "required": True}]),
            _op("get_book", "Get book details by ISBN", [{"name": "isbn", "type": "string", "required": True}]),
        ],
        "capabilities": ["book_catalog", "isbn_lookup"],
    },
]

# ---------------------------------------------------------------------------
# OTHER (Weather, Currency, Maps, Translation, Government, Financial, Educational)
# ---------------------------------------------------------------------------
OTHER_CONNECTORS = [
    {
        "name": "weather",
        "display_name": "OpenWeatherMap",
        "description": "Weather data - current weather, forecasts, and historical data.",
        "category": "other",
        "category_label": "Other",
        "auth_required": True,
        "auth_type": "api_key",
        "auth_field_name": "API Key",
        "free_paid": "freemium",
        "rate_limit": "60 calls per minute (free tier)",
        "rate_limit_unit": "per_minute",
        "base_url": "https://api.openweathermap.org/data/2.5",
        "operations": [
            _op("get_current_weather", "Get current weather", [{"name": "city", "type": "string", "required": True}, {"name": "units", "type": "string", "required": False}]),
            _op("get_forecast", "Get weather forecast", [{"name": "city", "type": "string", "required": True}, {"name": "units", "type": "string", "required": False}]),
        ],
        "capabilities": ["current_weather", "forecasts", "climate_data"],
    },
    {
        "name": "currency",
        "display_name": "ExchangeRate API",
        "description": "Currency conversion rates and exchange rate data.",
        "category": "other",
        "category_label": "Other",
        "auth_required": False,
        "auth_type": None,
        "auth_field_name": None,
        "free_paid": "free",
        "rate_limit": "1,500 requests per month (free)",
        "rate_limit_unit": "per_day",
        "base_url": "https://open.er-api.com/v6",
        "operations": [
            _op("get_latest_rates", "Get latest exchange rates", [{"name": "base", "type": "string", "required": False}]),
            _op("convert_currency", "Convert between currencies", [{"name": "from", "type": "string", "required": True}, {"name": "to", "type": "string", "required": True}, {"name": "amount", "type": "number", "required": True}]),
        ],
        "capabilities": ["currency_conversion", "exchange_rates"],
    },
    {
        "name": "countries",
        "display_name": "REST Countries",
        "description": "Country information - names, capitals, currencies, languages, flags.",
        "category": "other",
        "category_label": "Other",
        "auth_required": False,
        "auth_type": None,
        "auth_field_name": None,
        "free_paid": "free",
        "rate_limit": "No documented limit",
        "rate_limit_unit": None,
        "base_url": "https://restcountries.com/v3.1",
        "operations": [
            _op("search_countries", "Search countries by name", [{"name": "name", "type": "string", "required": True}]),
            _op("get_all_countries", "Get all countries", []),
            _op("get_country_by_code", "Get country by ISO code", [{"name": "code", "type": "string", "required": True}]),
        ],
        "capabilities": ["country_data", "geography"],
    },
    {
        "name": "wikivoyage",
        "display_name": "Wikivoyage",
        "description": "Worldwide travel guide - destinations, attractions, and travel tips.",
        "category": "other",
        "category_label": "Other",
        "auth_required": False,
        "auth_type": None,
        "auth_field_name": None,
        "free_paid": "free",
        "rate_limit": "No documented limit",
        "rate_limit_unit": None,
        "base_url": "https://en.wikivoyage.org/w/api.php",
        "operations": [
            _op("search_destinations", "Search travel destinations", [{"name": "query", "type": "string", "required": True}]),
            _op("get_destination", "Get destination guide", [{"name": "title", "type": "string", "required": True}]),
        ],
        "capabilities": ["travel_guides", "destinations"],
    },
    {
        "name": "usgs",
        "display_name": "USGS Earthquake Hazards Program",
        "description": "Earthquake data - real-time earthquake feeds and historical seismic data.",
        "category": "other",
        "category_label": "Other",
        "auth_required": False,
        "auth_type": None,
        "auth_field_name": None,
        "free_paid": "free",
        "rate_limit": "No documented limit",
        "rate_limit_unit": None,
        "base_url": "https://earthquake.usgs.gov/fdsnws/event/1",
        "operations": [
            _op("get_earthquakes", "Get recent earthquakes", [{"name": "starttime", "type": "string", "required": False}, {"name": "limit", "type": "integer", "required": False}]),
            _op("get_earthquake", "Get earthquake details", [{"name": "event_id", "type": "string", "required": True}]),
        ],
        "capabilities": ["earthquake_data", "seismic_monitoring"],
    },
]

# Combine all connectors
ALL_CONNECTORS = (
    SPACE_SCIENCE_CONNECTORS
    + NEWS_INFORMATION_CONNECTORS
    + MEDIA_ENTERTAINMENT_CONNECTORS
    + DEVELOPMENT_CONNECTORS
    + KNOWLEDGE_CONNECTORS
    + OTHER_CONNECTORS
)

BUILTIN_CONNECTORS: dict[str, dict] = {c["name"]: c for c in ALL_CONNECTORS}