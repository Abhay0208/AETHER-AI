from ..base import ConnectorBase, ConnectorResult
import httpx


class OpenAlexConnector(ConnectorBase):
    NAME = "openalex"
    DISPLAY_NAME = "OpenAlex"
    DESCRIPTION = "Open academic index - research papers, authors, institutions, and concepts."
    CATEGORY = "space_science"
    CATEGORY_LABEL = "Space and Science"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "100,000 per day (email for more)"
    RATE_LIMIT_UNIT = "per_day"
    BASE_URL = "https://api.openalex.org"
    OPERATIONS = [
        {"name": "search_works", "description": "Search research works", "parameters": [{"name": "search", "type": "string", "required": True}, {"name": "per_page", "type": "integer", "required": False}]},
        {"name": "get_authors", "description": "Search authors", "parameters": [{"name": "search", "type": "string", "required": True}]},
        {"name": "get_concepts", "description": "Search concepts", "parameters": [{"name": "search", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["research_papers", "academic_search", "author_lookup"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(
                self.BASE_URL,
                params={"search": "test", "per-page": 1},
                headers=self._headers(),
            )
            resp.raise_for_status()
            return ConnectorResult(success=True, data={"status": "ok"})
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "search_works":
                resp = self.client.get(
                    f"{self.BASE_URL}/works",
                    params={"search": params.get("search", ""), "per-page": params.get("per_page", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"id": w.get("id"), "title": w.get("display_name"), "publication_year": w.get("publication_year")} for w in data.get("results", [])]
                return ConnectorResult(success=True, data={"results": results, "count": data.get("meta", {}).get("count", 0)}, connector=self.NAME, operation=operation)
            elif operation == "get_authors":
                resp = self.client.get(
                    f"{self.BASE_URL}/authors",
                    params={"search": params.get("search", ""), "per-page": params.get("per_page", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"id": a.get("id"), "display_name": a.get("display_name")} for a in data.get("results", [])]
                return ConnectorResult(success=True, data={"results": results}, connector=self.NAME, operation=operation)
            elif operation == "get_concepts":
                resp = self.client.get(
                    f"{self.BASE_URL}/concepts",
                    params={"search": params.get("search", ""), "per-page": params.get("per_page", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"id": c.get("id"), "display_name": c.get("display_name")} for c in data.get("results", [])]
                return ConnectorResult(success=True, data={"results": results}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class ArXivConnector(ConnectorBase):
    NAME = "arxiv"
    DISPLAY_NAME = "arXiv"
    DESCRIPTION = "Open access archive for scholarly articles in physics, mathematics, computer science, and more."
    CATEGORY = "space_science"
    CATEGORY_LABEL = "Space and Science"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "3 requests per second"
    RATE_LIMIT_UNIT = "per_minute"
    BASE_URL = "https://export.arxiv.org"
    OPERATIONS = [
        {"name": "search_papers", "description": "Search arXiv papers", "parameters": [{"name": "search_query", "type": "string", "required": True}, {"name": "max_results", "type": "integer", "required": False}]},
        {"name": "get_paper", "description": "Get paper by ID", "parameters": [{"name": "id", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["academic_papers", "preprints", "research"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(
                f"{self.BASE_URL}/api/query",
                params={"search_query": "all:electron", "max_results": 1},
                headers=self._headers(),
            )
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "search_papers":
                resp = self.client.get(
                    f"{self.BASE_URL}/api/query",
                    params={"search_query": params.get("search_query", ""), "max_results": params.get("max_results", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.content)
                ns = {"a": "http://www.w3.org/2005/Atom"}
                entries = root.findall("a:entry", ns)
                results = []
                for entry in entries:
                    title = entry.find("a:title", ns)
                    summary = entry.find("a:summary", ns)
                    results.append({
                        "title": title.text.strip() if title is not None else "",
                        "summary": summary.text.strip() if summary is not None else "",
                    })
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "get_paper":
                resp = self.client.get(
                    f"{self.BASE_URL}/api/query",
                    params={"id_list": params.get("id", "")},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.content)
                ns = {"a": "http://www.w3.org/2005/Atom"}
                entry = root.find("a:entry", ns)
                if entry is None:
                    return ConnectorResult(success=False, error="Paper not found", connector=self.NAME)
                title = entry.find("a:title", ns)
                summary = entry.find("a:summary", ns)
                return ConnectorResult(success=True, data={"title": title.text.strip() if title is not None else "", "summary": summary.text.strip() if summary is not None else ""}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class NewsAPIConnector(ConnectorBase):
    NAME = "newsapi"
    DISPLAY_NAME = "NewsAPI"
    DESCRIPTION = "Access breaking news headlines and search articles from 30,000+ sources."
    CATEGORY = "news_information"
    CATEGORY_LABEL = "News and Information"
    AUTH_REQUIRED = True
    AUTH_TYPE = "api_key"
    AUTH_FIELD_NAME = "API Key"
    FREE_PAID = "freemium"
    RATE_LIMIT = "500 requests per day (free tier)"
    RATE_LIMIT_UNIT = "per_day"
    BASE_URL = "https://newsapi.org/v2"
    OPERATIONS = [
        {"name": "get_headlines", "description": "Get top headlines", "parameters": [{"name": "country", "type": "string", "required": False}, {"name": "category", "type": "string", "required": False}, {"name": "page_size", "type": "integer", "required": False}]},
        {"name": "search_everything", "description": "Search all articles", "parameters": [{"name": "q", "type": "string", "required": True}, {"name": "page_size", "type": "integer", "required": False}]},
    ]
    CAPABILITIES = ["news_headlines", "article_search", "breaking_news"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0)

    def test_connection(self):
        api_key = self.auth_config.get("api_key") if self.auth_config else None
        if not api_key:
            return ConnectorResult(success=False, error="No API key configured", connector=self.NAME)
        try:
            resp = self.client.get(f"{self.BASE_URL}/top-headlines", params={"apiKey": api_key, "country": "us", "pageSize": 1}, headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        api_key = self.auth_config.get("api_key") if self.auth_config else None
        if not api_key:
            return ConnectorResult(success=False, error="No API key configured", connector=self.NAME)
        try:
            if operation == "get_headlines":
                resp = self.client.get(
                    f"{self.BASE_URL}/top-headlines",
                    params={"apiKey": api_key, "country": params.get("country", "us"), "category": params.get("category"), "pageSize": params.get("page_size", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"title": a.get("title"), "description": a.get("description"), "url": a.get("url"), "published_at": a.get("publishedAt")} for a in data.get("articles", [])]
                return ConnectorResult(success=True, data={"results": results, "count": data.get("totalResults", 0)}, connector=self.NAME, operation=operation)
            elif operation == "search_everything":
                resp = self.client.get(
                    f"{self.BASE_URL}/everything",
                    params={"apiKey": api_key, "q": params.get("q", ""), "pageSize": params.get("page_size", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"title": a.get("title"), "description": a.get("description"), "url": a.get("url"), "published_at": a.get("publishedAt")} for a in data.get("articles", [])]
                return ConnectorResult(success=True, data={"results": results, "count": data.get("totalResults", 0)}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class GDELTConnector(ConnectorBase):
    NAME = "gdel"
    DISPLAY_NAME = "GDELT"
    DESCRIPTION = "Global Database of Events, Language, and Tone - monitors global media."
    CATEGORY = "news_information"
    CATEGORY_LABEL = "News and Information"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "No documented limit"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://api.gdeltproject.org/api/v2"
    OPERATIONS = [
        {"name": "doc_query", "description": "Query GDELT documents", "parameters": [{"name": "query", "type": "string", "required": True}, {"name": "mode", "type": "string", "required": False}]},
        {"name": "get_counts", "description": "Get mention counts", "parameters": [{"name": "query", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["global_media_monitoring", "event_tracking", "media_analysis"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0)

    def test_connection(self):
        try:
            resp = self.client.get(
                self.BASE_URL,
                params={"query": "test", "mode": "artlist", "maxrecords": 1, "format": "json"},
                headers=self._headers(),
            )
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "doc_query":
                resp = self.client.get(
                    self.BASE_URL,
                    params={"query": params.get("query", ""), "mode": params.get("mode", "artlist"), "maxrecords": params.get("maxrecords", 10), "format": "json"},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                articles = data.get("articles", [])
                results = [{"title": a.get("title"), "url": a.get("url"), "domain": a.get("domain"), "seendate": a.get("seendate")} for a in articles]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "get_counts":
                resp = self.client.get(
                    self.BASE_URL,
                    params={"query": params.get("query", ""), "mode": "timelinevol", "format": "json"},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"counts": data}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class MusicBrainzConnector(ConnectorBase):
    NAME = "musicbrainz"
    DISPLAY_NAME = "MusicBrainz"
    DESCRIPTION = "Open music encyclopedia - artists, recordings, releases, and labels."
    CATEGORY = "media_entertainment"
    CATEGORY_LABEL = "Media and Entertainment"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "1 request per second"
    RATE_LIMIT_UNIT = "per_minute"
    BASE_URL = "https://musicbrainz.org/ws/2"
    OPERATIONS = [
        {"name": "search_artist", "description": "Search artists", "parameters": [{"name": "query", "type": "string", "required": True}]},
        {"name": "search_recording", "description": "Search recordings/tracks", "parameters": [{"name": "query", "type": "string", "required": True}]},
        {"name": "search_release", "description": "Search releases/albums", "parameters": [{"name": "query", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["music_metadata", "artist_lookup", "track_info"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(
                f"{self.BASE_URL}/artist",
                params={"query": "test", "fmt": "json", "limit": 1},
                headers=self._headers(),
            )
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "search_artist":
                resp = self.client.get(
                    f"{self.BASE_URL}/artist",
                    params={"query": params.get("query", ""), "fmt": "json", "limit": params.get("limit", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"id": a.get("id"), "name": a.get("name"), "country": a.get("country")} for a in data.get("artists", [])]
                return ConnectorResult(success=True, data={"results": results, "count": data.get("count", 0)}, connector=self.NAME, operation=operation)
            elif operation == "search_recording":
                resp = self.client.get(
                    f"{self.BASE_URL}/recording",
                    params={"query": params.get("query", ""), "fmt": "json", "limit": params.get("limit", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"id": r.get("id"), "title": r.get("title"), "artist": r.get("artist-credit", [{}])[0].get("name") if r.get("artist-credit") else None} for r in data.get("recordings", [])]
                return ConnectorResult(success=True, data={"results": results, "count": data.get("count", 0)}, connector=self.NAME, operation=operation)
            elif operation == "search_release":
                resp = self.client.get(
                    f"{self.BASE_URL}/release",
                    params={"query": params.get("query", ""), "fmt": "json", "limit": params.get("limit", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"id": r.get("id"), "title": r.get("title"), "date": r.get("date")} for r in data.get("releases", [])]
                return ConnectorResult(success=True, data={"results": results, "count": data.get("count", 0)}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class OpenLibraryConnector(ConnectorBase):
    NAME = "openlibrary"
    DISPLAY_NAME = "Open Library"
    DESCRIPTION = "Open book catalog - search books, authors, and editions."
    CATEGORY = "knowledge"
    CATEGORY_LABEL = "Knowledge"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "No documented limit"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://openlibrary.org"
    OPERATIONS = [
        {"name": "search_books", "description": "Search books", "parameters": [{"name": "query", "type": "string", "required": True}]},
        {"name": "get_book", "description": "Get book details by ISBN", "parameters": [{"name": "isbn", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["book_catalog", "isbn_lookup"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(
                f"{self.BASE_URL}/search.json",
                params={"q": "test", "limit": 1},
                headers=self._headers(),
            )
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "search_books":
                resp = self.client.get(
                    f"{self.BASE_URL}/search.json",
                    params={"q": params.get("query", ""), "limit": params.get("limit", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"title": b.get("title"), "author_name": b.get("author_name", []), "first_publish_year": b.get("first_publish_year"), "key": b.get("key")} for b in data.get("docs", [])]
                return ConnectorResult(success=True, data={"results": results, "count": data.get("numFound", 0)}, connector=self.NAME, operation=operation)
            elif operation == "get_book":
                resp = self.client.get(f"{self.BASE_URL}/isbn/{params.get('isbn')}.json", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"title": data.get("title"), "authors": [a.get("name") for a in data.get("authors", [])], "publish_date": data.get("publish_date"), "isbn_10": data.get("isbn_10"), "isbn_13": data.get("isbn_13")}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class CrossrefConnector(ConnectorBase):
    NAME = "crossref"
    DISPLAY_NAME = "Crossref"
    DESCRIPTION = "Scholarly metadata - DOI registration, journal articles, and citations."
    CATEGORY = "knowledge"
    CATEGORY_LABEL = "Knowledge"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "No documented limit"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://api.crossref.org"
    OPERATIONS = [
        {"name": "search_works", "description": "Search scholarly works", "parameters": [{"name": "query", "type": "string", "required": True}, {"name": "rows", "type": "integer", "required": False}]},
        {"name": "get_work", "description": "Get work by DOI", "parameters": [{"name": "doi", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["scholarly_metadata", "doi_lookup", "citations"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(
                f"{self.BASE_URL}/works",
                params={"query": "test", "rows": 1},
                headers=self._headers(),
            )
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "search_works":
                resp = self.client.get(
                    f"{self.BASE_URL}/works",
                    params={"query": params.get("query", ""), "rows": params.get("rows", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"id": w.get("DOI"), "title": w.get("title", [""])[0] if w.get("title") else "", "published": w.get("published-print", {}).get("date-parts", [[None]])[0][0] if w.get("published-print") else None} for w in data.get("message", {}).get("items", [])]
                return ConnectorResult(success=True, data={"results": results, "count": data.get("message", {}).get("total-results", 0)}, connector=self.NAME, operation=operation)
            elif operation == "get_work":
                resp = self.client.get(f"{self.BASE_URL}/works/{params.get('doi', '')}", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                w = data.get("message", {})
                return ConnectorResult(success=True, data={"title": w.get("title", [""])[0] if w.get("title") else "", "doi": w.get("DOI"), "authors": [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in w.get("author", [])], "published": w.get("published-print", {}).get("date-parts", [[None]])[0][0] if w.get("published-print") else None}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class CountriesConnector(ConnectorBase):
    NAME = "countries"
    DISPLAY_NAME = "REST Countries"
    DESCRIPTION = "Country information - names, capitals, currencies, languages, flags."
    CATEGORY = "other"
    CATEGORY_LABEL = "Other"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "No documented limit"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://restcountries.com/v3.1"
    OPERATIONS = [
        {"name": "search_countries", "description": "Search countries by name", "parameters": [{"name": "name", "type": "string", "required": True}]},
        {"name": "get_all_countries", "description": "Get all countries", "parameters": []},
        {"name": "get_country_by_code", "description": "Get country by ISO code", "parameters": [{"name": "code", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["country_data", "geography"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(f"{self.BASE_URL}/all?fields=name,capital", headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "search_countries":
                resp = self.client.get(f"{self.BASE_URL}/name/{params.get('name', '')}", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                results = [{"name": c.get("name", {}).get("common"), "capital": c.get("capital", [None])[0], "region": c.get("region"), "population": c.get("population")} for c in data]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "get_all_countries":
                resp = self.client.get(f"{self.BASE_URL}/all?fields=name,capital,region,population", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                results = [{"name": c.get("name", {}).get("common"), "capital": c.get("capital", [None])[0], "region": c.get("region"), "population": c.get("population")} for c in data]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "get_country_by_code":
                resp = self.client.get(f"{self.BASE_URL}/alpha/{params.get('code', '')}", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()[0]
                return ConnectorResult(success=True, data={"name": data.get("name", {}).get("common"), "capital": data.get("capital", [None])[0], "region": data.get("region"), "population": data.get("population"), "currencies": list(data.get("currencies", {}).keys())}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class USGSConnector(ConnectorBase):
    NAME = "usgs"
    DISPLAY_NAME = "USGS Earthquake Hazards Program"
    DESCRIPTION = "Earthquake data - real-time earthquake feeds and historical seismic data."
    CATEGORY = "other"
    CATEGORY_LABEL = "Other"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "No documented limit"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1"
    OPERATIONS = [
        {"name": "get_earthquakes", "description": "Get recent earthquakes", "parameters": [{"name": "starttime", "type": "string", "required": False}, {"name": "limit", "type": "integer", "required": False}]},
        {"name": "get_earthquake", "description": "Get earthquake details", "parameters": [{"name": "event_id", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["earthquake_data", "seismic_monitoring"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(
                f"{self.BASE_URL}/query",
                params={"format": "geojson", "starttime": "2024-01-01", "limit": 1},
                headers=self._headers(),
            )
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "get_earthquakes":
                resp = self.client.get(
                    f"{self.BASE_URL}/query",
                    params={"format": "geojson", "starttime": params.get("starttime"), "limit": params.get("limit", 20)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                features = data.get("features", [])
                results = [{"id": f.get("id"), "mag": f.get("properties", {}).get("mag"), "place": f.get("properties", {}).get("place"), "time": f.get("properties", {}).get("time")} for f in features]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "get_earthquake":
                resp = self.client.get(f"{self.BASE_URL}/query", params={"format": "geojson", "eventid": params.get("event_id", "")}, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                features = data.get("features", [])
                if not features:
                    return ConnectorResult(success=False, error="Earthquake not found", connector=self.NAME)
                f = features[0]
                props = f.get("properties", {})
                return ConnectorResult(success=True, data={"id": f.get("id"), "mag": props.get("mag"), "place": props.get("place"), "time": props.get("time"), "url": props.get("url")}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class WikivoyageConnector(ConnectorBase):
    NAME = "wikivoyage"
    DISPLAY_NAME = "Wikivoyage"
    DESCRIPTION = "Worldwide travel guide - destinations, attractions, and travel tips."
    CATEGORY = "other"
    CATEGORY_LABEL = "Other"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "No documented limit"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://en.wikivoyage.org/w/api.php"
    OPERATIONS = [
        {"name": "search_destinations", "description": "Search travel destinations", "parameters": [{"name": "query", "type": "string", "required": True}]},
        {"name": "get_destination", "description": "Get destination guide", "parameters": [{"name": "title", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["travel_guides", "destinations"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(
                self.BASE_URL,
                params={"action": "query", "list": "search", "srsearch": "Paris", "format": "json"},
                headers=self._headers(),
            )
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "search_destinations":
                resp = self.client.get(
                    self.BASE_URL,
                    params={"action": "query", "list": "search", "srsearch": params.get("query", ""), "srlimit": params.get("limit", 10), "format": "json"},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"title": r.get("title"), "snippet": r.get("snippet", "")} for r in data.get("query", {}).get("search", [])]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "get_destination":
                resp = self.client.get(
                    self.BASE_URL,
                    params={"action": "query", "prop": "extracts", "explaintext": 1, "titles": params.get("title", ""), "format": "json"},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                pages = data.get("query", {}).get("pages", {})
                page = next(iter(pages.values())) if pages else {}
                return ConnectorResult(success=True, data={"title": page.get("title"), "content": page.get("extract", "")}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class GuardianConnector(ConnectorBase):
    NAME = "guardian"
    DISPLAY_NAME = "The Guardian"
    DESCRIPTION = "Access Guardian news articles, sections, and contributors."
    CATEGORY = "news_information"
    CATEGORY_LABEL = "News and Information"
    AUTH_REQUIRED = True
    AUTH_TYPE = "api_key"
    AUTH_FIELD_NAME = "API Key"
    FREE_PAID = "free"
    RATE_LIMIT = "50 requests per second"
    RATE_LIMIT_UNIT = "per_minute"
    BASE_URL = "https://content.guardianapis.com"
    OPERATIONS = [
        {"name": "search_articles", "description": "Search Guardian articles", "parameters": [{"name": "q", "type": "string", "required": True}, {"name": "page_size", "type": "integer", "required": False}]},
        {"name": "get_sections", "description": "Get available sections", "parameters": []},
    ]
    CAPABILITIES = ["news_articles", "uk_news"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0)

    def test_connection(self):
        api_key = self.auth_config.get("api_key") if self.auth_config else None
        if not api_key:
            return ConnectorResult(success=False, error="No API key configured", connector=self.NAME)
        try:
            resp = self.client.get(f"{self.BASE_URL}/search", params={"api-key": api_key, "q": "test", "page-size": 1}, headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        api_key = self.auth_config.get("api_key") if self.auth_config else None
        if not api_key:
            return ConnectorResult(success=False, error="No API key configured", connector=self.NAME)
        try:
            if operation == "search_articles":
                resp = self.client.get(
                    f"{self.BASE_URL}/search",
                    params={"api-key": api_key, "q": params.get("q", ""), "page-size": params.get("page_size", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"title": a.get("webTitle"), "url": a.get("webUrl"), "section": a.get("sectionName"), "published": a.get("webPublicationDate")} for a in data.get("response", {}).get("results", [])]
                return ConnectorResult(success=True, data={"results": results, "count": data.get("response", {}).get("total", 0)}, connector=self.NAME, operation=operation)
            elif operation == "get_sections":
                resp = self.client.get(f"{self.BASE_URL}/sections", params={"api-key": api_key}, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                results = [{"title": s.get("webTitle"), "url": s.get("webUrl")} for s in data.get("response", {}).get("results", [])]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class SpotifyConnector(ConnectorBase):
    NAME = "spotify"
    DISPLAY_NAME = "Spotify Web API"
    DESCRIPTION = "Access Spotify music catalog, playlists, and user data (requires authorization)."
    CATEGORY = "media_entertainment"
    CATEGORY_LABEL = "Media and Entertainment"
    AUTH_REQUIRED = True
    AUTH_TYPE = "bearer"
    AUTH_FIELD_NAME = "Access Token"
    FREE_PAID = "free"
    RATE_LIMIT = "Varies by endpoint"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://api.spotify.com/v1"
    OPERATIONS = [
        {"name": "search_track", "description": "Search tracks", "parameters": [{"name": "q", "type": "string", "required": True}]},
        {"name": "get_track", "description": "Get track details", "parameters": [{"name": "id", "type": "string", "required": True}]},
        {"name": "get_artist", "description": "Get artist details", "parameters": [{"name": "id", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["music_catalog", "playlists", "audio_features"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0)

    def test_connection(self):
        token = self.auth_config.get("access_token") if self.auth_config else None
        if not token:
            return ConnectorResult(success=False, error="No access token configured", connector=self.NAME)
        try:
            resp = self.client.get(f"{self.BASE_URL}/tracks/2takcWOa6BMIWgS3Agy29X", headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        token = self.auth_config.get("access_token") if self.auth_config else None
        if not token:
            return ConnectorResult(success=False, error="No access token configured", connector=self.NAME)
        try:
            if operation == "search_track":
                resp = self.client.get(
                    f"{self.BASE_URL}/search",
                    params={"q": params.get("q", ""), "type": "track", "limit": params.get("limit", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"id": t.get("id"), "name": t.get("name"), "artists": [a.get("name") for a in t.get("artists", [])], "album": t.get("album", {}).get("name")} for t in data.get("tracks", {}).get("items", [])]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "get_track":
                resp = self.client.get(f"{self.BASE_URL}/tracks/{params.get('id', '')}", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"id": data.get("id"), "name": data.get("name"), "artists": [a.get("name") for a in data.get("artists", [])], "album": data.get("album", {}).get("name"), "duration_ms": data.get("duration_ms")}, connector=self.NAME, operation=operation)
            elif operation == "get_artist":
                resp = self.client.get(f"{self.BASE_URL}/artists/{params.get('id', '')}", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"id": data.get("id"), "name": data.get("name"), "followers": data.get("followers", {}).get("total"), "genres": data.get("genres", [])}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class RSSConnector(ConnectorBase):
    NAME = "rss"
    DISPLAY_NAME = "RSS Feeds"
    DESCRIPTION = "Read and parse RSS/Atom feeds from any source."
    CATEGORY = "news_information"
    CATEGORY_LABEL = "News and Information"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "Depends on source"
    RATE_LIMIT_UNIT = None
    BASE_URL = None
    OPERATIONS = [
        {"name": "fetch_feed", "description": "Fetch and parse an RSS feed", "parameters": [{"name": "url", "type": "string", "required": True}]},
        {"name": "search_feed", "description": "Search items in a feed", "parameters": [{"name": "url", "type": "string", "required": True}, {"name": "query", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["rss_parsing", "feed_aggregation"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        return ConnectorResult(success=True, data={"status": "ok"})

    def execute_operation(self, operation, params=None):
        params = params or {}
        import xml.etree.ElementTree as ET
        try:
            if operation == "fetch_feed":
                url = params.get("url", "")
                if not url:
                    return ConnectorResult(success=False, error="url parameter required", connector=self.NAME)
                resp = self.client.get(url, headers=self._headers())
                resp.raise_for_status()
                root = ET.fromstring(resp.content)
                items = root.findall(".//item")
                results = []
                for item in items:
                    results.append({
                        "title": item.findtext("title", ""),
                        "link": item.findtext("link", ""),
                        "description": item.findtext("description", ""),
                        "pubDate": item.findtext("pubDate", ""),
                    })
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "search_feed":
                url = params.get("url", "")
                query = params.get("query", "")
                if not url or not query:
                    return ConnectorResult(success=False, error="url and query parameters required", connector=self.NAME)
                resp = self.client.get(url, headers=self._headers())
                resp.raise_for_status()
                root = ET.fromstring(resp.content)
                items = root.findall(".//item")
                results = []
                for item in items:
                    title = item.findtext("title", "")
                    desc = item.findtext("description", "")
                    if query.lower() in title.lower() or query.lower() in desc.lower():
                        results.append({"title": title, "link": item.findtext("link", ""), "description": desc, "pubDate": item.findtext("pubDate", "")})
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)
        except ET.ParseError as exc:
            return ConnectorResult(success=False, error=f"Invalid RSS feed: {str(exc)}", connector=self.NAME)


class NPMConnector(ConnectorBase):
    NAME = "npm"
    DISPLAY_NAME = "npm Registry"
    DESCRIPTION = "JavaScript package registry - search and get package details."
    CATEGORY = "development"
    CATEGORY_LABEL = "Development"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "No documented limit"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://registry.npmjs.org"
    OPERATIONS = [
        {"name": "search_packages", "description": "Search npm packages", "parameters": [{"name": "query", "type": "string", "required": True}]},
        {"name": "get_package", "description": "Get package details", "parameters": [{"name": "package_name", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["package_registry", "javascript", "npm"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(f"{self.BASE_URL}/express", headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "search_packages":
                # npm doesn't have a public search API endpoint; use the npm registry search
                resp = self.client.get(
                    f"{self.BASE_URL}/-/all",
                    params={"search": params.get("query", "")},
                    headers=self._headers(),
                )
                # Simplified: return a note that full search requires npm search API
                return ConnectorResult(success=True, data={"message": "Use https://api.npms.io/v2/search?q={query} for full search", "query": params.get("query", "")}, connector=self.NAME, operation=operation)
            elif operation == "get_package":
                resp = self.client.get(f"{self.BASE_URL}/{params.get('package_name', '')}", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"name": data.get("name"), "version": data.get("version"), "description": data.get("description"), "license": data.get("license"), "homepage": data.get("homepage")}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class PyPIConnector(ConnectorBase):
    NAME = "pypi"
    DISPLAY_NAME = "PyPI (Python Package Index)"
    DESCRIPTION = "Python package repository - search and get package details."
    CATEGORY = "development"
    CATEGORY_LABEL = "Development"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "No documented limit"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://pypi.org/pypi"
    OPERATIONS = [
        {"name": "search_packages", "description": "Search PyPI packages", "parameters": [{"name": "query", "type": "string", "required": True}]},
        {"name": "get_package", "description": "Get package details", "parameters": [{"name": "package_name", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["package_registry", "python"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(f"{self.BASE_URL}/requests/json", headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "search_packages":
                # PyPI JSON API doesn't have full-text search; use the simple search
                resp = self.client.get(
                    f"{self.BASE_URL}/",
                    params={"q": params.get("query", "")},
                    headers=self._headers(),
                )
                return ConnectorResult(success=True, data={"message": "Use https://pypi.org/search/?q={query} for full search", "query": params.get("query", "")}, connector=self.NAME, operation=operation)
            elif operation == "get_package":
                resp = self.client.get(f"{self.BASE_URL}/{params.get('package_name', '')}/json", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                info = data.get("info", {})
                return ConnectorResult(success=True, data={"name": info.get("name"), "version": info.get("version"), "summary": info.get("summary"), "author": info.get("author"), "homepage": info.get("home_page")}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class DockerHubConnector(ConnectorBase):
    NAME = "dockerhub"
    DISPLAY_NAME = "Docker Hub"
    DESCRIPTION = "Docker container image registry - search and get image details."
    CATEGORY = "development"
    CATEGORY_LABEL = "Development"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "No documented limit"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://hub.docker.com/v2"
    OPERATIONS = [
        {"name": "search_images", "description": "Search Docker images", "parameters": [{"name": "query", "type": "string", "required": True}]},
        {"name": "get_image", "description": "Get image details", "parameters": [{"name": "namespace", "type": "string", "required": True}, {"name": "repository", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["container_images", "docker"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(f"{self.BASE_URL}/search/repositories/?query=alpine&page_size=1", headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "search_images":
                resp = self.client.get(
                    f"{self.BASE_URL}/search/repositories/",
                    params={"query": params.get("query", ""), "page_size": params.get("page_size", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"name": r.get("name"), "description": r.get("short_description"), "stars": r.get("star_count"), "is_official": r.get("is_official")} for r in data.get("results", [])]
                return ConnectorResult(success=True, data={"results": results, "count": data.get("count", 0)}, connector=self.NAME, operation=operation)
            elif operation == "get_image":
                resp = self.client.get(f"{self.BASE_URL}/repositories/{params.get('namespace', '')}/{params.get('repository', '')}", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"name": data.get("name"), "description": data.get("description"), "stars": data.get("star_count"), "is_official": data.get("is_official"), "user": data.get("user")}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class StackExchangeConnector(ConnectorBase):
    NAME = "stackexchange"
    DISPLAY_NAME = "Stack Exchange"
    DESCRIPTION = "Stack Overflow and Stack Exchange Q&A data."
    CATEGORY = "development"
    CATEGORY_LABEL = "Development"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "300 per day (no key), 10,000 per day (with key)"
    RATE_LIMIT_UNIT = "per_day"
    BASE_URL = "https://api.stackexchange.com/2.3"
    OPERATIONS = [
        {"name": "search_questions", "description": "Search questions", "parameters": [{"name": "q", "type": "string", "required": True}, {"name": "site", "type": "string", "required": False}]},
        {"name": "get_questions", "description": "Get recent questions", "parameters": [{"name": "site", "type": "string", "required": False}]},
    ]
    CAPABILITIES = ["q_and_a", "programming_help", "technical_questions"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(
                f"{self.BASE_URL}/questions",
                params={"order": "desc", "sort": "activity", "site": "stackoverflow", "pagesize": 1},
                headers=self._headers(),
            )
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        site = params.get("site", "stackoverflow")
        try:
            if operation == "search_questions":
                resp = self.client.get(
                    f"{self.BASE_URL}/search/advanced",
                    params={"q": params.get("q", ""), "site": site, "pagesize": params.get("pagesize", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"title": q.get("title"), "link": q.get("link"), "score": q.get("score"), "answered": q.get("is_answered")} for q in data.get("items", [])]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "get_questions":
                resp = self.client.get(
                    f"{self.BASE_URL}/questions",
                    params={"order": "desc", "sort": "activity", "site": site, "pagesize": params.get("pagesize", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"title": q.get("title"), "link": q.get("link"), "score": q.get("score"), "answered": q.get("is_answered")} for q in data.get("items", [])]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class TVMazeConnector(ConnectorBase):
    NAME = "tvmaze"
    DISPLAY_NAME = "TVMaze"
    DESCRIPTION = "TV show schedules, cast, and episode information."
    CATEGORY = "media_entertainment"
    CATEGORY_LABEL = "Media and Entertainment"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "No documented limit"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://api.tvmaze.com"
    OPERATIONS = [
        {"name": "search_shows", "description": "Search TV shows", "parameters": [{"name": "q", "type": "string", "required": True}]},
        {"name": "get_show", "description": "Get show details", "parameters": [{"name": "id", "type": "integer", "required": True}]},
        {"name": "get_episodes", "description": "Get show episodes", "parameters": [{"name": "id", "type": "integer", "required": True}]},
    ]
    CAPABILITIES = ["tv_shows", "episodes", "cast"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(f"{self.BASE_URL}/singlesearch/shows?q=test", headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "search_shows":
                resp = self.client.get(f"{self.BASE_URL}/singlesearch/shows", params={"q": params.get("q", "")}, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"id": data.get("id"), "name": data.get("name"), "genres": data.get("genres", []), "summary": data.get("summary"), "url": data.get("url")}, connector=self.NAME, operation=operation)
            elif operation == "get_show":
                resp = self.client.get(f"{self.BASE_URL}/shows/{params.get('id', '')}", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"id": data.get("id"), "name": data.get("name"), "genres": data.get("genres", []), "summary": data.get("summary"), "url": data.get("url"), "network": data.get("network", {}).get("name")}, connector=self.NAME, operation=operation)
            elif operation == "get_episodes":
                resp = self.client.get(f"{self.BASE_URL}/shows/{params.get('id', '')}/episodes", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                results = [{"id": e.get("id"), "name": e.get("name"), "season": e.get("season"), "number": e.get("number"), "airdate": e.get("airdate")} for e in data]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class GitHubAPIConnector(ConnectorBase):
    NAME = "github_api"
    DISPLAY_NAME = "GitHub (Extended)"
    DESCRIPTION = "Extended GitHub API access with authentication for private repos and higher limits."
    CATEGORY = "development"
    CATEGORY_LABEL = "Development"
    AUTH_REQUIRED = True
    AUTH_TYPE = "api_key"
    AUTH_FIELD_NAME = "Personal Access Token"
    FREE_PAID = "free"
    RATE_LIMIT = "5000 per hour (authenticated)"
    RATE_LIMIT_UNIT = "per_hour"
    BASE_URL = "https://api.github.com"
    OPERATIONS = [
        {"name": "list_repos", "description": "List authenticated user repositories", "parameters": []},
        {"name": "create_issue", "description": "Create a repository issue", "parameters": [{"name": "owner", "type": "string", "required": True}, {"name": "repo", "type": "string", "required": True}, {"name": "title", "type": "string", "required": True}, {"name": "body", "type": "string", "required": False}]},
    ]
    CAPABILITIES = ["private_repos", "issue_management", "repo_management"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"Accept": "application/vnd.github+json", "User-Agent": "AETHER/1.0"})

    def test_connection(self):
        token = self.auth_config.get("api_key") if self.auth_config else None
        if not token:
            return ConnectorResult(success=False, error="No API key configured", connector=self.NAME)
        try:
            resp = self.client.get(f"{self.BASE_URL}/user", headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        token = self.auth_config.get("api_key") if self.auth_config else None
        if not token:
            return ConnectorResult(success=False, error="No API key configured", connector=self.NAME)
        try:
            if operation == "list_repos":
                resp = self.client.get(f"{self.BASE_URL}/user/repos", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                results = [{"name": r.get("full_name"), "description": r.get("description"), "stars": r.get("stargazers_count"), "private": r.get("private")} for r in data]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "create_issue":
                resp = self.client.post(
                    f"{self.BASE_URL}/repos/{params.get('owner', '')}/{params.get('repo', '')}/issues",
                    json={"title": params.get("title", ""), "body": params.get("body", "")},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"number": data.get("number"), "title": data.get("title"), "url": data.get("html_url")}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class SpaceflightConnector(ConnectorBase):
    NAME = "spaceflight"
    DISPLAY_NAME = "Spaceflight News"
    DESCRIPTION = "Spaceflight news articles, launches, and events."
    CATEGORY = "space_science"
    CATEGORY_LABEL = "Space and Science"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "No documented limit"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://api.spaceflightnewsapi.net/v3"
    OPERATIONS = [
        {"name": "get_articles", "description": "Get spaceflight news articles", "parameters": [{"name": "limit", "type": "integer", "required": False}, {"name": "search", "type": "string", "required": False}]},
        {"name": "get_launches", "description": "Get upcoming and past launches", "parameters": [{"name": "limit", "type": "integer", "required": False}]},
        {"name": "get_events", "description": "Get space events", "parameters": [{"name": "limit", "type": "integer", "required": False}]},
    ]
    CAPABILITIES = ["space_news", "launch_data", "events"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(f"{self.BASE_URL}/articles", params={"_limit": 1}, headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "get_articles":
                resp = self.client.get(
                    f"{self.BASE_URL}/articles",
                    params={"_limit": params.get("limit", 10), "_search": params.get("search", "")},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"id": a.get("id"), "title": a.get("title"), "summary": a.get("summary"), "url": a.get("url")} for a in data]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "get_launches":
                resp = self.client.get(f"{self.BASE_URL}/launches", params={"_limit": params.get("limit", 10)}, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                results = [{"id": l.get("id"), "name": l.get("name"), "net": l.get("net"), "provider": l.get("provider")} for l in data]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "get_events":
                resp = self.client.get(f"{self.BASE_URL}/events", params={"_limit": params.get("limit", 10)}, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                results = [{"id": e.get("id"), "name": e.get("name"), "description": e.get("description"), "date": e.get("date")} for e in data]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class WikidataConnector(ConnectorBase):
    NAME = "wikidata"
    DISPLAY_NAME = "Wikidata"
    DESCRIPTION = "Free and open knowledge base - structured data about entities."
    CATEGORY = "knowledge"
    CATEGORY_LABEL = "Knowledge"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "No documented limit"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://www.wikidata.org/w/api.php"
    OPERATIONS = [
        {"name": "search_entities", "description": "Search Wikidata entities", "parameters": [{"name": "query", "type": "string", "required": True}]},
        {"name": "get_entity", "description": "Get entity details", "parameters": [{"name": "id", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["structured_data", "entities", "knowledge_graph"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(
                self.BASE_URL,
                params={"action": "wbsearchentities", "search": "test", "language": "en", "format": "json"},
                headers=self._headers(),
            )
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "search_entities":
                resp = self.client.get(
                    self.BASE_URL,
                    params={"action": "wbsearchentities", "search": params.get("query", ""), "language": "en", "format": "json", "limit": params.get("limit", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"id": e.get("id"), "label": e.get("label"), "description": e.get("description")} for e in data.get("search", [])]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "get_entity":
                resp = self.client.get(
                    self.BASE_URL,
                    params={"action": "wbgetentities", "ids": params.get("id", ""), "format": "json", "languages": "en"},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                entities = data.get("entities", {})
                entity = entities.get(params.get("id", ""), {})
                labels = entity.get("labels", {})
                label = labels.get("en", {}).get("value", "") if labels else ""
                descriptions = entity.get("descriptions", {})
                description = descriptions.get("en", {}).get("value", "") if descriptions else ""
                return ConnectorResult(success=True, data={"id": entity.get("id"), "label": label, "description": description}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class WikipediaConnector(ConnectorBase):
    NAME = "wikipedia"
    DISPLAY_NAME = "Wikipedia"
    DESCRIPTION = "Free encyclopedia - search and retrieve articles on any topic."
    CATEGORY = "knowledge"
    CATEGORY_LABEL = "Knowledge"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "No documented limit"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://en.wikipedia.org/w/api.php"
    OPERATIONS = [
        {"name": "search_articles", "description": "Search Wikipedia articles", "parameters": [{"name": "query", "type": "string", "required": True}, {"name": "limit", "type": "integer", "required": False}]},
        {"name": "get_article", "description": "Get article content by title", "parameters": [{"name": "title", "type": "string", "required": True}]},
        {"name": "get_summary", "description": "Get article summary", "parameters": [{"name": "title", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["encyclopedia", "general_knowledge", "article_search"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(
                self.BASE_URL,
                params={"action": "query", "list": "search", "srsearch": "test", "format": "json"},
                headers=self._headers(),
            )
            resp.raise_for_status()
            return ConnectorResult(success=True, data={"status": "ok"})
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "search_articles":
                resp = self.client.get(
                    self.BASE_URL,
                    params={"action": "query", "list": "search", "srsearch": params.get("query", ""), "srlimit": params.get("limit", 10), "format": "json"},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"title": r.get("title"), "snippet": r.get("snippet", "")} for r in data.get("query", {}).get("search", [])]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "get_article":
                resp = self.client.get(
                    self.BASE_URL,
                    params={"action": "query", "prop": "extracts", "explaintext": 1, "titles": params.get("title", ""), "format": "json"},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                pages = data.get("query", {}).get("pages", {})
                page = next(iter(pages.values())) if pages else {}
                return ConnectorResult(success=True, data={"title": page.get("title"), "content": page.get("extract", "")}, connector=self.NAME, operation=operation)
            elif operation == "get_summary":
                resp = self.client.get(
                    self.BASE_URL,
                    params={"action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1, "titles": params.get("title", ""), "format": "json"},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                pages = data.get("query", {}).get("pages", {})
                page = next(iter(pages.values())) if pages else {}
                return ConnectorResult(success=True, data={"title": page.get("title"), "summary": page.get("extract", "")}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class GitHubConnector(ConnectorBase):
    NAME = "github"
    DISPLAY_NAME = "GitHub"
    DESCRIPTION = "GitHub repositories, users, issues, pull requests, and more."
    CATEGORY = "development"
    CATEGORY_LABEL = "Development"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "60 per hour (unauthenticated), 5000 per hour (authenticated)"
    RATE_LIMIT_UNIT = "per_hour"
    BASE_URL = "https://api.github.com"
    OPERATIONS = [
        {"name": "search_repos", "description": "Search repositories", "parameters": [{"name": "q", "type": "string", "required": True}, {"name": "per_page", "type": "integer", "required": False}]},
        {"name": "get_repo", "description": "Get repository details", "parameters": [{"name": "owner", "type": "string", "required": True}, {"name": "repo", "type": "string", "required": True}]},
        {"name": "get_user", "description": "Get user details", "parameters": [{"name": "username", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["code_hosting", "repository_search", "issues", "pull_requests"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"Accept": "application/vnd.github+json", "User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(f"{self.BASE_URL}/zen", headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "search_repos":
                resp = self.client.get(
                    f"{self.BASE_URL}/search/repositories",
                    params={"q": params.get("q", ""), "per_page": params.get("per_page", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"name": r["full_name"], "description": r.get("description"), "stars": r.get("stargazers_count"), "url": r.get("html_url")} for r in data.get("items", [])]
                return ConnectorResult(success=True, data={"results": results, "count": data.get("total_count", 0)}, connector=self.NAME, operation=operation)
            elif operation == "get_repo":
                resp = self.client.get(f"{self.BASE_URL}/repos/{params.get('owner')}/{params.get('repo')}", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"name": data.get("full_name"), "description": data.get("description"), "stars": data.get("stargazers_count"), "forks": data.get("forks_count"), "url": data.get("html_url"), "language": data.get("language")}, connector=self.NAME, operation=operation)
            elif operation == "get_user":
                resp = self.client.get(f"{self.BASE_URL}/users/{params.get('username')}", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"login": data.get("login"), "name": data.get("name"), "bio": data.get("bio"), "public_repos": data.get("public_repos"), "url": data.get("html_url")}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class NASASpaceConnector(ConnectorBase):
    NAME = "nasa"
    DISPLAY_NAME = "NASA"
    DESCRIPTION = "Access NASA APIs including Mars rover photos, APOD, asteroid data, and more."
    CATEGORY = "space_science"
    CATEGORY_LABEL = "Space and Science"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "1000 per hour"
    RATE_LIMIT_UNIT = "per_hour"
    BASE_URL = "https://api.nasa.gov"
    OPERATIONS = [
        {"name": "get_apod", "description": "Get Astronomy Picture of the Day", "parameters": [{"name": "date", "type": "string", "required": False}]},
        {"name": "get_mars_rover_photos", "description": "Get Mars rover photos", "parameters": [{"name": "rover", "type": "string", "required": True}, {"name": "sol", "type": "integer", "required": False}]},
    ]
    CAPABILITIES = ["astronomy", "space_imagery", "asteroid_data"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0)

    def test_connection(self):
        try:
            resp = self.client.get(f"{self.BASE_URL}/planetary/apod", params={"api_key": "DEMO_KEY"}, headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "get_apod":
                resp = self.client.get(f"{self.BASE_URL}/planetary/apod", params={"api_key": "DEMO_KEY", "date": params.get("date")}, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"title": data.get("title"), "url": data.get("url"), "explanation": data.get("explanation"), "date": data.get("date")}, connector=self.NAME, operation=operation)
            elif operation == "get_mars_rover_photos":
                resp = self.client.get(f"{self.BASE_URL}/mars-photos/api/v1/rovers/{params.get('rover')}/photos", params={"api_key": "DEMO_KEY", "sol": params.get("sol", 1000)}, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                photos = [{"img_src": p.get("img_src"), "earth_date": p.get("earth_date"), "camera": p.get("camera", {}).get("full_name")} for p in data.get("photos", [])]
                return ConnectorResult(success=True, data={"photos": photos, "count": len(photos)}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class TMDBConnector(ConnectorBase):
    NAME = "tmdb"
    DISPLAY_NAME = "TMDB"
    DESCRIPTION = "Movie and TV show metadata, images, and cast information."
    CATEGORY = "media_entertainment"
    CATEGORY_LABEL = "Media and Entertainment"
    AUTH_REQUIRED = True
    AUTH_TYPE = "api_key"
    AUTH_FIELD_NAME = "API Key"
    FREE_PAID = "free"
    RATE_LIMIT = "40 requests per 10 seconds"
    RATE_LIMIT_UNIT = "per_minute"
    BASE_URL = "https://api.themoviedb.org/3"
    OPERATIONS = [
        {"name": "search_movie", "description": "Search for movies", "parameters": [{"name": "query", "type": "string", "required": True}]},
        {"name": "get_movie_details", "description": "Get movie details", "parameters": [{"name": "movie_id", "type": "integer", "required": True}]},
    ]
    CAPABILITIES = ["movie_metadata", "tv_metadata", "cast_info", "posters"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0)

    def test_connection(self):
        api_key = self.auth_config.get("api_key") if self.auth_config else None
        if not api_key:
            return ConnectorResult(success=False, error="No API key configured", connector=self.NAME)
        try:
            resp = self.client.get(f"{self.BASE_URL}/movie/550", params={"api_key": api_key}, headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        api_key = self.auth_config.get("api_key") if self.auth_config else None
        if not api_key:
            return ConnectorResult(success=False, error="No API key configured", connector=self.NAME)
        try:
            if operation == "search_movie":
                resp = self.client.get(f"{self.BASE_URL}/search/movie", params={"api_key": api_key, "query": params.get("query", "")}, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                results = [{"title": r.get("title"), "release_date": r.get("release_date"), "overview": r.get("overview"), "poster_path": r.get("poster_path")} for r in data.get("results", [])]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "get_movie_details":
                resp = self.client.get(f"{self.BASE_URL}/movie/{params.get('movie_id')}", params={"api_key": api_key}, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"title": data.get("title"), "overview": data.get("overview"), "release_date": data.get("release_date"), "rating": data.get("vote_average"), "poster_path": data.get("poster_path")}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class WeatherConnector(ConnectorBase):
    NAME = "weather"
    DISPLAY_NAME = "OpenWeatherMap"
    DESCRIPTION = "Weather data - current weather, forecasts, and historical data."
    CATEGORY = "other"
    CATEGORY_LABEL = "Other"
    AUTH_REQUIRED = True
    AUTH_TYPE = "api_key"
    AUTH_FIELD_NAME = "API Key"
    FREE_PAID = "freemium"
    RATE_LIMIT = "60 calls per minute (free tier)"
    RATE_LIMIT_UNIT = "per_minute"
    BASE_URL = "https://api.openweathermap.org/data/2.5"
    OPERATIONS = [
        {"name": "get_current_weather", "description": "Get current weather", "parameters": [{"name": "city", "type": "string", "required": True}, {"name": "units", "type": "string", "required": False}]},
        {"name": "get_forecast", "description": "Get weather forecast", "parameters": [{"name": "city", "type": "string", "required": True}, {"name": "units", "type": "string", "required": False}]},
    ]
    CAPABILITIES = ["current_weather", "forecasts", "climate_data"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0)

    def test_connection(self):
        api_key = self.auth_config.get("api_key") if self.auth_config else None
        if not api_key:
            return ConnectorResult(success=False, error="No API key configured", connector=self.NAME)
        try:
            resp = self.client.get(f"{self.BASE_URL}/weather", params={"q": "London", "appid": api_key, "units": "metric"}, headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        api_key = self.auth_config.get("api_key") if self.auth_config else None
        if not api_key:
            return ConnectorResult(success=False, error="No API key configured", connector=self.NAME)
        try:
            if operation == "get_current_weather":
                resp = self.client.get(f"{self.BASE_URL}/weather", params={"q": params.get("city", ""), "appid": api_key, "units": params.get("units", "metric")}, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"city": data.get("name"), "temperature": data.get("main", {}).get("temp"), "description": data.get("weather", [{}])[0].get("description"), "humidity": data.get("main", {}).get("humidity")}, connector=self.NAME, operation=operation)
            elif operation == "get_forecast":
                resp = self.client.get(f"{self.BASE_URL}/forecast", params={"q": params.get("city", ""), "appid": api_key, "units": params.get("units", "metric")}, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                forecasts = [{"dt": f.get("dt"), "temp": f.get("main", {}).get("temp"), "description": f.get("weather", [{}])[0].get("description")} for f in data.get("list", [])[:5]]
                return ConnectorResult(success=True, data={"city": data.get("city", {}).get("name"), "forecasts": forecasts}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class CurrencyConnector(ConnectorBase):
    NAME = "currency"
    DISPLAY_NAME = "ExchangeRate API"
    DESCRIPTION = "Currency conversion rates and exchange rate data."
    CATEGORY = "other"
    CATEGORY_LABEL = "Other"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "1,500 requests per month (free)"
    RATE_LIMIT_UNIT = "per_day"
    BASE_URL = "https://open.er-api.com/v6"
    OPERATIONS = [
        {"name": "get_latest_rates", "description": "Get latest exchange rates", "parameters": [{"name": "base", "type": "string", "required": False}]},
        {"name": "convert_currency", "description": "Convert between currencies", "parameters": [{"name": "from", "type": "string", "required": True}, {"name": "to", "type": "string", "required": True}, {"name": "amount", "type": "number", "required": True}]},
    ]
    CAPABILITIES = ["currency_conversion", "exchange_rates"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0)

    def test_connection(self):
        try:
            resp = self.client.get(f"{self.BASE_URL}/latest/USD", headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "get_latest_rates":
                base = params.get("base", "USD")
                resp = self.client.get(f"{self.BASE_URL}/latest/{base}", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"base": data.get("base_code"), "rates": data.get("rates", {}), "time": data.get("time_last_update_utc")}, connector=self.NAME, operation=operation)
            elif operation == "convert_currency":
                from_cur = params.get("from", "USD")
                to_cur = params.get("to", "EUR")
                amount = params.get("amount", 1)
                resp = self.client.get(f"{self.BASE_URL}/latest/{from_cur}", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                rate = data.get("rates", {}).get(to_cur, 1)
                converted = amount * rate
                return ConnectorResult(success=True, data={"from": from_cur, "to": to_cur, "amount": amount, "converted": converted, "rate": rate}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class NewsAPIConnector(ConnectorBase):
    NAME = "newsapi"
    DISPLAY_NAME = "NewsAPI"
    DESCRIPTION = "Access breaking news headlines and search articles from 30,000+ sources."
    CATEGORY = "news_information"
    CATEGORY_LABEL = "News and Information"
    AUTH_REQUIRED = True
    AUTH_TYPE = "api_key"
    AUTH_FIELD_NAME = "API Key"
    FREE_PAID = "freemium"
    RATE_LIMIT = "500 requests per day (free tier)"
    RATE_LIMIT_UNIT = "per_day"
    BASE_URL = "https://newsapi.org/v2"
    OPERATIONS = [
        {"name": "get_headlines", "description": "Get top headlines", "parameters": [{"name": "country", "type": "string", "required": False}, {"name": "category", "type": "string", "required": False}, {"name": "page_size", "type": "integer", "required": False}]},
        {"name": "search_everything", "description": "Search all articles", "parameters": [{"name": "q", "type": "string", "required": True}, {"name": "page_size", "type": "integer", "required": False}]},
    ]
    CAPABILITIES = ["news_headlines", "article_search", "breaking_news"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0)

    def test_connection(self):
        api_key = self.auth_config.get("api_key") if self.auth_config else None
        if not api_key:
            return ConnectorResult(success=False, error="No API key configured", connector=self.NAME)
        try:
            resp = self.client.get(f"{self.BASE_URL}/top-headlines", params={"apiKey": api_key, "country": "us", "pageSize": 1}, headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        api_key = self.auth_config.get("api_key") if self.auth_config else None
        if not api_key:
            return ConnectorResult(success=False, error="No API key configured", connector=self.NAME)
        try:
            if operation == "get_headlines":
                resp = self.client.get(
                    f"{self.BASE_URL}/top-headlines",
                    params={"apiKey": api_key, "country": params.get("country", "us"), "category": params.get("category"), "pageSize": params.get("page_size", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"title": a.get("title"), "description": a.get("description"), "url": a.get("url"), "published_at": a.get("publishedAt")} for a in data.get("articles", [])]
                return ConnectorResult(success=True, data={"results": results, "count": data.get("totalResults", 0)}, connector=self.NAME, operation=operation)
            elif operation == "search_everything":
                resp = self.client.get(
                    f"{self.BASE_URL}/everything",
                    params={"apiKey": api_key, "q": params.get("q", ""), "pageSize": params.get("page_size", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"title": a.get("title"), "description": a.get("description"), "url": a.get("url"), "published_at": a.get("publishedAt")} for a in data.get("articles", [])]
                return ConnectorResult(success=True, data={"results": results, "count": data.get("totalResults", 0)}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class GDELTConnector(ConnectorBase):
    NAME = "gdel"
    DISPLAY_NAME = "GDELT"
    DESCRIPTION = "Global Database of Events, Language, and Tone - monitors global media."
    CATEGORY = "news_information"
    CATEGORY_LABEL = "News and Information"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "No documented limit"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://api.gdeltproject.org/api/v2"
    OPERATIONS = [
        {"name": "doc_query", "description": "Query GDELT documents", "parameters": [{"name": "query", "type": "string", "required": True}, {"name": "mode", "type": "string", "required": False}]},
        {"name": "get_counts", "description": "Get mention counts", "parameters": [{"name": "query", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["global_media_monitoring", "event_tracking", "media_analysis"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0)

    def test_connection(self):
        try:
            resp = self.client.get(
                self.BASE_URL,
                params={"query": "test", "mode": "artlist", "maxrecords": 1, "format": "json"},
                headers=self._headers(),
            )
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "doc_query":
                resp = self.client.get(
                    self.BASE_URL,
                    params={"query": params.get("query", ""), "mode": params.get("mode", "artlist"), "maxrecords": params.get("maxrecords", 10), "format": "json"},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                articles = data.get("articles", [])
                results = [{"title": a.get("title"), "url": a.get("url"), "domain": a.get("domain"), "seendate": a.get("seendate")} for a in articles]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "get_counts":
                resp = self.client.get(
                    self.BASE_URL,
                    params={"query": params.get("query", ""), "mode": "timelinevol", "format": "json"},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"counts": data}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class MusicBrainzConnector(ConnectorBase):
    NAME = "musicbrainz"
    DISPLAY_NAME = "MusicBrainz"
    DESCRIPTION = "Open music encyclopedia - artists, recordings, releases, and labels."
    CATEGORY = "media_entertainment"
    CATEGORY_LABEL = "Media and Entertainment"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "1 request per second"
    RATE_LIMIT_UNIT = "per_minute"
    BASE_URL = "https://musicbrainz.org/ws/2"
    OPERATIONS = [
        {"name": "search_artist", "description": "Search artists", "parameters": [{"name": "query", "type": "string", "required": True}]},
        {"name": "search_recording", "description": "Search recordings/tracks", "parameters": [{"name": "query", "type": "string", "required": True}]},
        {"name": "search_release", "description": "Search releases/albums", "parameters": [{"name": "query", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["music_metadata", "artist_lookup", "track_info"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(
                f"{self.BASE_URL}/artist",
                params={"query": "test", "fmt": "json", "limit": 1},
                headers=self._headers(),
            )
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "search_artist":
                resp = self.client.get(
                    f"{self.BASE_URL}/artist",
                    params={"query": params.get("query", ""), "fmt": "json", "limit": params.get("limit", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"id": a.get("id"), "name": a.get("name"), "country": a.get("country")} for a in data.get("artists", [])]
                return ConnectorResult(success=True, data={"results": results, "count": data.get("count", 0)}, connector=self.NAME, operation=operation)
            elif operation == "search_recording":
                resp = self.client.get(
                    f"{self.BASE_URL}/recording",
                    params={"query": params.get("query", ""), "fmt": "json", "limit": params.get("limit", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"id": r.get("id"), "title": r.get("title"), "artist": r.get("artist-credit", [{}])[0].get("name") if r.get("artist-credit") else None} for r in data.get("recordings", [])]
                return ConnectorResult(success=True, data={"results": results, "count": data.get("count", 0)}, connector=self.NAME, operation=operation)
            elif operation == "search_release":
                resp = self.client.get(
                    f"{self.BASE_URL}/release",
                    params={"query": params.get("query", ""), "fmt": "json", "limit": params.get("limit", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"id": r.get("id"), "title": r.get("title"), "date": r.get("date")} for r in data.get("releases", [])]
                return ConnectorResult(success=True, data={"results": results, "count": data.get("count", 0)}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class NPMConnector(ConnectorBase):
    NAME = "npm"
    DISPLAY_NAME = "npm Registry"
    DESCRIPTION = "JavaScript package registry - search and get package details."
    CATEGORY = "development"
    CATEGORY_LABEL = "Development"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "No documented limit"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://registry.npmjs.org"
    OPERATIONS = [
        {"name": "search_packages", "description": "Search npm packages", "parameters": [{"name": "query", "type": "string", "required": True}]},
        {"name": "get_package", "description": "Get package details", "parameters": [{"name": "package_name", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["package_registry", "javascript", "npm"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(f"{self.BASE_URL}/express", headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "search_packages":
                return ConnectorResult(success=True, data={"message": "Use https://api.npms.io/v2/search?q={query} for full search", "query": params.get("query", "")}, connector=self.NAME, operation=operation)
            elif operation == "get_package":
                resp = self.client.get(f"{self.BASE_URL}/{params.get('package_name', '')}", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"name": data.get("name"), "version": data.get("version"), "description": data.get("description"), "license": data.get("license"), "homepage": data.get("homepage")}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class PyPIConnector(ConnectorBase):
    NAME = "pypi"
    DISPLAY_NAME = "PyPI (Python Package Index)"
    DESCRIPTION = "Python package repository - search and get package details."
    CATEGORY = "development"
    CATEGORY_LABEL = "Development"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "No documented limit"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://pypi.org/pypi"
    OPERATIONS = [
        {"name": "search_packages", "description": "Search PyPI packages", "parameters": [{"name": "query", "type": "string", "required": True}]},
        {"name": "get_package", "description": "Get package details", "parameters": [{"name": "package_name", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["package_registry", "python"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(f"{self.BASE_URL}/requests/json", headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "search_packages":
                return ConnectorResult(success=True, data={"message": "Use https://pypi.org/search/?q={query} for full search", "query": params.get("query", "")}, connector=self.NAME, operation=operation)
            elif operation == "get_package":
                resp = self.client.get(f"{self.BASE_URL}/{params.get('package_name', '')}/json", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                info = data.get("info", {})
                return ConnectorResult(success=True, data={"name": info.get("name"), "version": info.get("version"), "summary": info.get("summary"), "author": info.get("author"), "homepage": info.get("home_page")}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class DockerHubConnector(ConnectorBase):
    NAME = "dockerhub"
    DISPLAY_NAME = "Docker Hub"
    DESCRIPTION = "Docker container image registry - search and get image details."
    CATEGORY = "development"
    CATEGORY_LABEL = "Development"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "No documented limit"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://hub.docker.com/v2"
    OPERATIONS = [
        {"name": "search_images", "description": "Search Docker images", "parameters": [{"name": "query", "type": "string", "required": True}]},
        {"name": "get_image", "description": "Get image details", "parameters": [{"name": "namespace", "type": "string", "required": True}, {"name": "repository", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["container_images", "docker"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(f"{self.BASE_URL}/search/repositories/?query=alpine&page_size=1", headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "search_images":
                resp = self.client.get(
                    f"{self.BASE_URL}/search/repositories/",
                    params={"query": params.get("query", ""), "page_size": params.get("page_size", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"name": r.get("name"), "description": r.get("short_description"), "stars": r.get("star_count"), "is_official": r.get("is_official")} for r in data.get("results", [])]
                return ConnectorResult(success=True, data={"results": results, "count": data.get("count", 0)}, connector=self.NAME, operation=operation)
            elif operation == "get_image":
                resp = self.client.get(f"{self.BASE_URL}/repositories/{params.get('namespace', '')}/{params.get('repository', '')}", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"name": data.get("name"), "description": data.get("description"), "stars": data.get("star_count"), "is_official": data.get("is_official"), "user": data.get("user")}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class StackExchangeConnector(ConnectorBase):
    NAME = "stackexchange"
    DISPLAY_NAME = "Stack Exchange"
    DESCRIPTION = "Stack Overflow and Stack Exchange Q&A data."
    CATEGORY = "development"
    CATEGORY_LABEL = "Development"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "300 per day (no key), 10,000 per day (with key)"
    RATE_LIMIT_UNIT = "per_day"
    BASE_URL = "https://api.stackexchange.com/2.3"
    OPERATIONS = [
        {"name": "search_questions", "description": "Search questions", "parameters": [{"name": "q", "type": "string", "required": True}, {"name": "site", "type": "string", "required": False}]},
        {"name": "get_questions", "description": "Get recent questions", "parameters": [{"name": "site", "type": "string", "required": False}]},
    ]
    CAPABILITIES = ["q_and_a", "programming_help", "technical_questions"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(
                f"{self.BASE_URL}/questions",
                params={"order": "desc", "sort": "activity", "site": "stackoverflow", "pagesize": 1},
                headers=self._headers(),
            )
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        site = params.get("site", "stackoverflow")
        try:
            if operation == "search_questions":
                resp = self.client.get(
                    f"{self.BASE_URL}/search/advanced",
                    params={"q": params.get("q", ""), "site": site, "pagesize": params.get("pagesize", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"title": q.get("title"), "link": q.get("link"), "score": q.get("score"), "answered": q.get("is_answered")} for q in data.get("items", [])]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "get_questions":
                resp = self.client.get(
                    f"{self.BASE_URL}/questions",
                    params={"order": "desc", "sort": "activity", "site": site, "pagesize": params.get("pagesize", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"title": q.get("title"), "link": q.get("link"), "score": q.get("score"), "answered": q.get("is_answered")} for q in data.get("items", [])]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class TVMazeConnector(ConnectorBase):
    NAME = "tvmaze"
    DISPLAY_NAME = "TVMaze"
    DESCRIPTION = "TV show schedules, cast, and episode information."
    CATEGORY = "media_entertainment"
    CATEGORY_LABEL = "Media and Entertainment"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "No documented limit"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://api.tvmaze.com"
    OPERATIONS = [
        {"name": "search_shows", "description": "Search TV shows", "parameters": [{"name": "q", "type": "string", "required": True}]},
        {"name": "get_show", "description": "Get show details", "parameters": [{"name": "id", "type": "integer", "required": True}]},
        {"name": "get_episodes", "description": "Get show episodes", "parameters": [{"name": "id", "type": "integer", "required": True}]},
    ]
    CAPABILITIES = ["tv_shows", "episodes", "cast"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(f"{self.BASE_URL}/singlesearch/shows?q=test", headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "search_shows":
                resp = self.client.get(f"{self.BASE_URL}/singlesearch/shows", params={"q": params.get("q", "")}, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"id": data.get("id"), "name": data.get("name"), "genres": data.get("genres", []), "summary": data.get("summary"), "url": data.get("url")}, connector=self.NAME, operation=operation)
            elif operation == "get_show":
                resp = self.client.get(f"{self.BASE_URL}/shows/{params.get('id', '')}", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"id": data.get("id"), "name": data.get("name"), "genres": data.get("genres", []), "summary": data.get("summary"), "url": data.get("url"), "network": data.get("network", {}).get("name")}, connector=self.NAME, operation=operation)
            elif operation == "get_episodes":
                resp = self.client.get(f"{self.BASE_URL}/shows/{params.get('id', '')}/episodes", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                results = [{"id": e.get("id"), "name": e.get("name"), "season": e.get("season"), "number": e.get("number"), "airdate": e.get("airdate")} for e in data]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class GitHubAPIConnector(ConnectorBase):
    NAME = "github_api"
    DISPLAY_NAME = "GitHub (Extended)"
    DESCRIPTION = "Extended GitHub API access with authentication for private repos and higher limits."
    CATEGORY = "development"
    CATEGORY_LABEL = "Development"
    AUTH_REQUIRED = True
    AUTH_TYPE = "api_key"
    AUTH_FIELD_NAME = "Personal Access Token"
    FREE_PAID = "free"
    RATE_LIMIT = "5000 per hour (authenticated)"
    RATE_LIMIT_UNIT = "per_hour"
    BASE_URL = "https://api.github.com"
    OPERATIONS = [
        {"name": "list_repos", "description": "List authenticated user repositories", "parameters": []},
        {"name": "create_issue", "description": "Create a repository issue", "parameters": [{"name": "owner", "type": "string", "required": True}, {"name": "repo", "type": "string", "required": True}, {"name": "title", "type": "string", "required": True}, {"name": "body", "type": "string", "required": False}]},
    ]
    CAPABILITIES = ["private_repos", "issue_management", "repo_management"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"Accept": "application/vnd.github+json", "User-Agent": "AETHER/1.0"})

    def test_connection(self):
        token = self.auth_config.get("api_key") if self.auth_config else None
        if not token:
            return ConnectorResult(success=False, error="No API key configured", connector=self.NAME)
        try:
            resp = self.client.get(f"{self.BASE_URL}/user", headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        token = self.auth_config.get("api_key") if self.auth_config else None
        if not token:
            return ConnectorResult(success=False, error="No API key configured", connector=self.NAME)
        try:
            if operation == "list_repos":
                resp = self.client.get(f"{self.BASE_URL}/user/repos", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                results = [{"name": r.get("full_name"), "description": r.get("description"), "stars": r.get("stargazers_count"), "private": r.get("private")} for r in data]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "create_issue":
                resp = self.client.post(
                    f"{self.BASE_URL}/repos/{params.get('owner', '')}/{params.get('repo', '')}/issues",
                    json={"title": params.get("title", ""), "body": params.get("body", "")},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"number": data.get("number"), "title": data.get("title"), "url": data.get("html_url")}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class CountriesConnector(ConnectorBase):
    NAME = "countries"
    DISPLAY_NAME = "REST Countries"
    DESCRIPTION = "Country information - names, capitals, currencies, languages, flags."
    CATEGORY = "other"
    CATEGORY_LABEL = "Other"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "No documented limit"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://restcountries.com/v3.1"
    OPERATIONS = [
        {"name": "search_countries", "description": "Search countries by name", "parameters": [{"name": "name", "type": "string", "required": True}]},
        {"name": "get_all_countries", "description": "Get all countries", "parameters": []},
        {"name": "get_country_by_code", "description": "Get country by ISO code", "parameters": [{"name": "code", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["country_data", "geography"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(f"{self.BASE_URL}/all?fields=name,capital", headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "search_countries":
                resp = self.client.get(f"{self.BASE_URL}/name/{params.get('name', '')}", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                results = [{"name": c.get("name", {}).get("common"), "capital": c.get("capital", [None])[0], "region": c.get("region"), "population": c.get("population")} for c in data]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "get_all_countries":
                resp = self.client.get(f"{self.BASE_URL}/all?fields=name,capital,region,population", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                results = [{"name": c.get("name", {}).get("common"), "capital": c.get("capital", [None])[0], "region": c.get("region"), "population": c.get("population")} for c in data]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "get_country_by_code":
                resp = self.client.get(f"{self.BASE_URL}/alpha/{params.get('code', '')}", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()[0]
                return ConnectorResult(success=True, data={"name": data.get("name", {}).get("common"), "capital": data.get("capital", [None])[0], "region": data.get("region"), "population": data.get("population"), "currencies": list(data.get("currencies", {}).keys())}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class USGSConnector(ConnectorBase):
    NAME = "usgs"
    DISPLAY_NAME = "USGS Earthquake Hazards Program"
    DESCRIPTION = "Earthquake data - real-time earthquake feeds and historical seismic data."
    CATEGORY = "other"
    CATEGORY_LABEL = "Other"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "No documented limit"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1"
    OPERATIONS = [
        {"name": "get_earthquakes", "description": "Get recent earthquakes", "parameters": [{"name": "starttime", "type": "string", "required": False}, {"name": "limit", "type": "integer", "required": False}]},
        {"name": "get_earthquake", "description": "Get earthquake details", "parameters": [{"name": "event_id", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["earthquake_data", "seismic_monitoring"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(
                f"{self.BASE_URL}/query",
                params={"format": "geojson", "starttime": "2024-01-01", "limit": 1},
                headers=self._headers(),
            )
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "get_earthquakes":
                resp = self.client.get(
                    f"{self.BASE_URL}/query",
                    params={"format": "geojson", "starttime": params.get("starttime"), "limit": params.get("limit", 20)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                features = data.get("features", [])
                results = [{"id": f.get("id"), "mag": f.get("properties", {}).get("mag"), "place": f.get("properties", {}).get("place"), "time": f.get("properties", {}).get("time")} for f in features]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "get_earthquake":
                resp = self.client.get(f"{self.BASE_URL}/query", params={"format": "geojson", "eventid": params.get("event_id", "")}, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                features = data.get("features", [])
                if not features:
                    return ConnectorResult(success=False, error="Earthquake not found", connector=self.NAME)
                f = features[0]
                props = f.get("properties", {})
                return ConnectorResult(success=True, data={"id": f.get("id"), "mag": props.get("mag"), "place": props.get("place"), "time": props.get("time"), "url": props.get("url")}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class WikivoyageConnector(ConnectorBase):
    NAME = "wikivoyage"
    DISPLAY_NAME = "Wikivoyage"
    DESCRIPTION = "Worldwide travel guide - destinations, attractions, and travel tips."
    CATEGORY = "other"
    CATEGORY_LABEL = "Other"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "No documented limit"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://en.wikivoyage.org/w/api.php"
    OPERATIONS = [
        {"name": "search_destinations", "description": "Search travel destinations", "parameters": [{"name": "query", "type": "string", "required": True}]},
        {"name": "get_destination", "description": "Get destination guide", "parameters": [{"name": "title", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["travel_guides", "destinations"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        try:
            resp = self.client.get(
                self.BASE_URL,
                params={"action": "query", "list": "search", "srsearch": "Paris", "format": "json"},
                headers=self._headers(),
            )
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        try:
            if operation == "search_destinations":
                resp = self.client.get(
                    self.BASE_URL,
                    params={"action": "query", "list": "search", "srsearch": params.get("query", ""), "srlimit": params.get("limit", 10), "format": "json"},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"title": r.get("title"), "snippet": r.get("snippet", "")} for r in data.get("query", {}).get("search", [])]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "get_destination":
                resp = self.client.get(
                    self.BASE_URL,
                    params={"action": "query", "prop": "extracts", "explaintext": 1, "titles": params.get("title", ""), "format": "json"},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                pages = data.get("query", {}).get("pages", {})
                page = next(iter(pages.values())) if pages else {}
                return ConnectorResult(success=True, data={"title": page.get("title"), "content": page.get("extract", "")}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class GuardianConnector(ConnectorBase):
    NAME = "guardian"
    DISPLAY_NAME = "The Guardian"
    DESCRIPTION = "Access Guardian news articles, sections, and contributors."
    CATEGORY = "news_information"
    CATEGORY_LABEL = "News and Information"
    AUTH_REQUIRED = True
    AUTH_TYPE = "api_key"
    AUTH_FIELD_NAME = "API Key"
    FREE_PAID = "free"
    RATE_LIMIT = "50 requests per second"
    RATE_LIMIT_UNIT = "per_minute"
    BASE_URL = "https://content.guardianapis.com"
    OPERATIONS = [
        {"name": "search_articles", "description": "Search Guardian articles", "parameters": [{"name": "q", "type": "string", "required": True}, {"name": "page_size", "type": "integer", "required": False}]},
        {"name": "get_sections", "description": "Get available sections", "parameters": []},
    ]
    CAPABILITIES = ["news_articles", "uk_news"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0)

    def test_connection(self):
        api_key = self.auth_config.get("api_key") if self.auth_config else None
        if not api_key:
            return ConnectorResult(success=False, error="No API key configured", connector=self.NAME)
        try:
            resp = self.client.get(f"{self.BASE_URL}/search", params={"api-key": api_key, "q": "test", "page-size": 1}, headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        api_key = self.auth_config.get("api_key") if self.auth_config else None
        if not api_key:
            return ConnectorResult(success=False, error="No API key configured", connector=self.NAME)
        try:
            if operation == "search_articles":
                resp = self.client.get(
                    f"{self.BASE_URL}/search",
                    params={"api-key": api_key, "q": params.get("q", ""), "page-size": params.get("page_size", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"title": a.get("webTitle"), "url": a.get("webUrl"), "section": a.get("sectionName"), "published": a.get("webPublicationDate")} for a in data.get("response", {}).get("results", [])]
                return ConnectorResult(success=True, data={"results": results, "count": data.get("response", {}).get("total", 0)}, connector=self.NAME, operation=operation)
            elif operation == "get_sections":
                resp = self.client.get(f"{self.BASE_URL}/sections", params={"api-key": api_key}, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                results = [{"title": s.get("webTitle"), "url": s.get("webUrl")} for s in data.get("response", {}).get("results", [])]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class SpotifyConnector(ConnectorBase):
    NAME = "spotify"
    DISPLAY_NAME = "Spotify Web API"
    DESCRIPTION = "Access Spotify music catalog, playlists, and user data (requires authorization)."
    CATEGORY = "media_entertainment"
    CATEGORY_LABEL = "Media and Entertainment"
    AUTH_REQUIRED = True
    AUTH_TYPE = "bearer"
    AUTH_FIELD_NAME = "Access Token"
    FREE_PAID = "free"
    RATE_LIMIT = "Varies by endpoint"
    RATE_LIMIT_UNIT = None
    BASE_URL = "https://api.spotify.com/v1"
    OPERATIONS = [
        {"name": "search_track", "description": "Search tracks", "parameters": [{"name": "q", "type": "string", "required": True}]},
        {"name": "get_track", "description": "Get track details", "parameters": [{"name": "id", "type": "string", "required": True}]},
        {"name": "get_artist", "description": "Get artist details", "parameters": [{"name": "id", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["music_catalog", "playlists", "audio_features"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0)

    def test_connection(self):
        token = self.auth_config.get("access_token") if self.auth_config else None
        if not token:
            return ConnectorResult(success=False, error="No access token configured", connector=self.NAME)
        try:
            resp = self.client.get(f"{self.BASE_URL}/tracks/2takcWOa6BMIWgS3Agy29X", headers=self._headers())
            if resp.status_code == 200:
                return ConnectorResult(success=True, data={"status": "ok"})
            return ConnectorResult(success=False, error=f"HTTP {resp.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)

    def execute_operation(self, operation, params=None):
        params = params or {}
        token = self.auth_config.get("access_token") if self.auth_config else None
        if not token:
            return ConnectorResult(success=False, error="No access token configured", connector=self.NAME)
        try:
            if operation == "search_track":
                resp = self.client.get(
                    f"{self.BASE_URL}/search",
                    params={"q": params.get("q", ""), "type": "track", "limit": params.get("limit", 10)},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                results = [{"id": t.get("id"), "name": t.get("name"), "artists": [a.get("name") for a in t.get("artists", [])], "album": t.get("album", {}).get("name")} for t in data.get("tracks", {}).get("items", [])]
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "get_track":
                resp = self.client.get(f"{self.BASE_URL}/tracks/{params.get('id', '')}", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"id": data.get("id"), "name": data.get("name"), "artists": [a.get("name") for a in data.get("artists", [])], "album": data.get("album", {}).get("name"), "duration_ms": data.get("duration_ms")}, connector=self.NAME, operation=operation)
            elif operation == "get_artist":
                resp = self.client.get(f"{self.BASE_URL}/artists/{params.get('id', '')}", headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                return ConnectorResult(success=True, data={"id": data.get("id"), "name": data.get("name"), "followers": data.get("followers", {}).get("total"), "genres": data.get("genres", [])}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)


class RSSConnector(ConnectorBase):
    NAME = "rss"
    DISPLAY_NAME = "RSS Feeds"
    DESCRIPTION = "Read and parse RSS/Atom feeds from any source."
    CATEGORY = "news_information"
    CATEGORY_LABEL = "News and Information"
    AUTH_REQUIRED = False
    AUTH_TYPE = None
    AUTH_FIELD_NAME = None
    FREE_PAID = "free"
    RATE_LIMIT = "Depends on source"
    RATE_LIMIT_UNIT = None
    BASE_URL = None
    OPERATIONS = [
        {"name": "fetch_feed", "description": "Fetch and parse an RSS feed", "parameters": [{"name": "url", "type": "string", "required": True}]},
        {"name": "search_feed", "description": "Search items in a feed", "parameters": [{"name": "url", "type": "string", "required": True}, {"name": "query", "type": "string", "required": True}]},
    ]
    CAPABILITIES = ["rss_parsing", "feed_aggregation"]

    def __init__(self, auth_config=None):
        super().__init__(auth_config)
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": "AETHER/1.0"})

    def test_connection(self):
        return ConnectorResult(success=True, data={"status": "ok"})

    def execute_operation(self, operation, params=None):
        params = params or {}
        import xml.etree.ElementTree as ET
        try:
            if operation == "fetch_feed":
                url = params.get("url", "")
                if not url:
                    return ConnectorResult(success=False, error="url parameter required", connector=self.NAME)
                resp = self.client.get(url, headers=self._headers())
                resp.raise_for_status()
                root = ET.fromstring(resp.content)
                items = root.findall(".//item")
                results = []
                for item in items:
                    results.append({
                        "title": item.findtext("title", ""),
                        "link": item.findtext("link", ""),
                        "description": item.findtext("description", ""),
                        "pubDate": item.findtext("pubDate", ""),
                    })
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            elif operation == "search_feed":
                url = params.get("url", "")
                query = params.get("query", "")
                if not url or not query:
                    return ConnectorResult(success=False, error="url and query parameters required", connector=self.NAME)
                resp = self.client.get(url, headers=self._headers())
                resp.raise_for_status()
                root = ET.fromstring(resp.content)
                items = root.findall(".//item")
                results = []
                for item in items:
                    title = item.findtext("title", "")
                    desc = item.findtext("description", "")
                    if query.lower() in title.lower() or query.lower() in desc.lower():
                        results.append({"title": title, "link": item.findtext("link", ""), "description": desc, "pubDate": item.findtext("pubDate", "")})
                return ConnectorResult(success=True, data={"results": results, "count": len(results)}, connector=self.NAME, operation=operation)
            else:
                return ConnectorResult(success=False, error=f"Unknown operation: {operation}", connector=self.NAME)
        except httpx.HTTPStatusError as exc:
            return ConnectorResult(success=False, error=f"HTTP {exc.response.status_code}", connector=self.NAME)
        except httpx.HTTPError as exc:
            return ConnectorResult(success=False, error=str(exc), connector=self.NAME)
        except ET.ParseError as exc:
            return ConnectorResult(success=False, error=f"Invalid RSS feed: {str(exc)}", connector=self.NAME)


IMPLEMENTATION_MAP: dict[str, type[ConnectorBase]] = {
    "wikipedia": WikipediaConnector,
    "github": GitHubConnector,
    "nasa": NASASpaceConnector,
    "openalex": OpenAlexConnector,
    "arxiv": ArXivConnector,
    "newsapi": NewsAPIConnector,
    "gdel": GDELTConnector,
    "tmdb": TMDBConnector,
    "musicbrainz": MusicBrainzConnector,
    "openlibrary": OpenLibraryConnector,
    "weather": WeatherConnector,
    "currency": CurrencyConnector,
    "crossref": CrossrefConnector,
    "spaceflight": SpaceflightConnector,
    "wikidata": WikidataConnector,
    "npm": NPMConnector,
    "pypi": PyPIConnector,
    "dockerhub": DockerHubConnector,
    "stackexchange": StackExchangeConnector,
    "tvmaze": TVMazeConnector,
    "github_api": GitHubAPIConnector,
    "countries": CountriesConnector,
    "usgs": USGSConnector,
    "wikivoyage": WikivoyageConnector,
    "guardian": GuardianConnector,
    "spotify": SpotifyConnector,
    "rss": RSSConnector,
}
