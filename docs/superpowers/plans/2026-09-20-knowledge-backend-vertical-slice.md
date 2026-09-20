# Changhe Knowledge Backend Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first independently testable backend slice that stores sourced historical claims and returns the published claims active in a requested year, grouped for the Android parallel-timeline UI.

**Architecture:** Use one Django 5.2 LTS application with Django REST Framework and PostgreSQL. Separate model modules define temporal, geographic, source, and historical-content boundaries; a publication service is the only path from approved to published content; a selector service powers a read-only `/api/v1/timeline/year-slice/` endpoint. Django Admin is the initial editorial interface.

**Tech Stack:** Python 3.13, Django 5.2.6, Django REST Framework 3.16, PostgreSQL 17, psycopg 3.2, pytest 8, pytest-django 4.11, Ruff 0.13, Docker Compose.

## Global Constraints

- Keep the backend as one Django application; do not introduce microservices, Elasticsearch, Celery, Redis, or a separate CMS in this slice.
- Store signed integer years and use inclusive ranges. The first content range is 1450–1700; future BCE support must not require a schema rewrite.
- Every published `Claim` must have at least one `Citation` with a locator or stable URL.
- AI-created records remain drafts and cannot call the publication service without a staff reviewer.
- Preserve time precision and uncertainty; never infer a day or month from a year-only source.
- Store only public-domain, openly licensed, or explicitly authorized full text. Other sources retain metadata, locator, short quotation, and external URL only.
- Public timeline reads require no account.
- Use `Asia/Shanghai` as the application time zone and UTC-aware timestamps in storage.
- API contracts live under `/api/v1/`.
- Prefer database constraints for row-local invariants and service-level validation for many-to-many invariants.
- All implementation steps follow red-green-refactor TDD and end with a focused commit.

## Subsystem Boundaries

This plan covers only the knowledge-backend vertical slice. Follow-up plans should separately cover:

1. Android parallel-timeline and Room offline store.
2. Source ingestion, OCR, AI candidate extraction, and editorial conflict handling.
3. Knowledge releases, full/delta packages, client-safe atomic synchronization, and rollback.
4. Mainland-China cloud deployment, backups, monitoring, ICP preparation, and privacy operations.

## Planned File Map

```text
Changhe/
├── .editorconfig
├── .gitignore
├── README.md
├── compose.yaml
└── backend/
    ├── pyproject.toml
    ├── manage.py
    ├── changhe_server/
    │   ├── __init__.py
    │   ├── asgi.py
    │   ├── settings.py
    │   ├── urls.py
    │   └── wsgi.py
    ├── knowledge/
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── apps.py
    │   ├── api/
    │   │   ├── __init__.py
    │   │   ├── serializers.py
    │   │   ├── urls.py
    │   │   └── views.py
    │   ├── management/
    │   │   ├── __init__.py
    │   │   └── commands/
    │   │       ├── __init__.py
    │   │       └── load_reference_data.py
    │   ├── migrations/
    │   │   └── __init__.py
    │   ├── models/
    │   │   ├── __init__.py
    │   │   ├── content.py
    │   │   ├── enums.py
    │   │   ├── geography.py
    │   │   ├── source.py
    │   │   └── temporal.py
    │   └── services/
    │       ├── __init__.py
    │       ├── publication.py
    │       └── year_slice.py
    └── tests/
        ├── __init__.py
        ├── factories.py
        ├── test_admin.py
        ├── test_health.py
        ├── test_models.py
        ├── test_publication.py
        ├── test_reference_data.py
        ├── test_year_slice_api.py
        └── test_year_slice_service.py
```

---

### Task 1: Repository and Django Runtime Bootstrap

**Files:**
- Create: `.gitignore`
- Create: `.editorconfig`
- Create: `README.md`
- Create: `compose.yaml`
- Create: `backend/pyproject.toml`
- Create through Django scaffold: `backend/manage.py`
- Create through Django scaffold: `backend/changhe_server/*`
- Create through Django scaffold: `backend/knowledge/apps.py`
- Create: `backend/tests/test_health.py`
- Modify: `backend/changhe_server/settings.py`
- Modify: `backend/changhe_server/urls.py`

**Interfaces:**
- Produces: Django project configured by `DATABASE_URL`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, and `DJANGO_ALLOWED_HOSTS`.
- Produces: `GET /health/ -> {"status": "ok"}` with HTTP 200.
- Produces: PostgreSQL development service named `db` on host port `5432`.

- [ ] **Step 1: Initialize version control and write repository ignores**

Run:

```powershell
git init -b main
```

Create `.gitignore`:

```gitignore
.idea/
.vscode/
.cursor/
.superpowers/
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/
.env
.venv/
backend/db.sqlite3
```

Create `.editorconfig`:

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
indent_style = space
indent_size = 4

[*.{yml,yaml,json}]
indent_size = 2
```

- [ ] **Step 2: Declare Python dependencies and PostgreSQL service**

Create `backend/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "changhe-backend"
version = "0.1.0"
requires-python = ">=3.13,<3.14"
dependencies = [
  "Django>=5.2.6,<5.3",
  "djangorestframework>=3.16,<3.17",
  "dj-database-url>=3.0,<4",
  "psycopg[binary]>=3.2,<3.3",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.4,<9",
  "pytest-django>=4.11,<5",
  "ruff>=0.13,<0.14",
]

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "changhe_server.settings"
python_files = ["test_*.py"]
testpaths = ["tests"]

[tool.setuptools.packages.find]
include = ["changhe_server*", "knowledge*"]

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "DJ"]
```

Create `compose.yaml`:

```yaml
services:
  db:
    image: postgres:17
    environment:
      POSTGRES_DB: changhe
      POSTGRES_USER: changhe
      POSTGRES_PASSWORD: changhe-local
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U changhe -d changhe"]
      interval: 5s
      timeout: 3s
      retries: 10
    volumes:
      - changhe-postgres:/var/lib/postgresql/data

volumes:
  changhe-postgres:
```

- [ ] **Step 3: Create the virtual environment and Django scaffold**

Run from `backend/`:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\django-admin.exe startproject changhe_server .
.\.venv\Scripts\python.exe manage.py startapp knowledge
New-Item -ItemType Directory -Force tests
New-Item -ItemType File -Force tests\__init__.py
```

Expected: dependency installation succeeds and `manage.py`, `changhe_server/`, `knowledge/`, and `tests/` exist.

- [ ] **Step 4: Write the failing health endpoint test**

Create `backend/tests/test_health.py`:

```python
from django.test import TestCase


class HealthEndpointTests(TestCase):
    def test_health_returns_ok(self):
        response = self.client.get("/health/")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
```

- [ ] **Step 5: Run the test and confirm the endpoint is absent**

Run from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_health.py -q
```

Expected: FAIL because `/health/` returns 404.

- [ ] **Step 6: Configure Django and implement the health endpoint**

Replace the generated database, locale, and app settings in `backend/changhe_server/settings.py` with:

```python
import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-local-development-key")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "knowledge",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "changhe_server.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "changhe_server.wsgi.application"
ASGI_APPLICATION = "changhe_server.asgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=60,
    )
}

AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}
```

Replace `backend/changhe_server/urls.py` with:

```python
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health),
    path("api/v1/", include("knowledge.api.urls")),
]
```

Create `backend/knowledge/api/__init__.py` and `backend/knowledge/api/urls.py`:

```python
from django.urls import path

app_name = "knowledge_api"
urlpatterns = []
```

- [ ] **Step 7: Verify bootstrap quality**

Run from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe manage.py check
```

Expected: one passing test, no Ruff errors, and `System check identified no issues`.

- [ ] **Step 8: Commit the bootstrap**

```powershell
git add .gitignore .editorconfig README.md compose.yaml backend
git commit -m "chore: bootstrap Changhe Django backend"
```

---

### Task 2: Temporal, Geographic, and Source Models

**Files:**
- Create: `backend/knowledge/models/enums.py`
- Create: `backend/knowledge/models/temporal.py`
- Create: `backend/knowledge/models/geography.py`
- Create: `backend/knowledge/models/source.py`
- Create: `backend/knowledge/models/__init__.py`
- Delete: `backend/knowledge/models.py`
- Create: `backend/tests/test_models.py`
- Create through Django: `backend/knowledge/migrations/0001_initial.py`

**Interfaces:**
- Produces: `HistoricalTimeSpan(start_year, end_year, precision, display_text, calendar)`.
- Produces: `Region(name, slug, parent)` and `Polity(name, slug, active_span)`.
- Produces: `Source`, `Edition`, and `Citation`.
- Invariant: `start_year <= end_year`.
- Invariant: a citation must contain either `locator` or `stable_url`.

- [ ] **Step 1: Write failing temporal and citation validation tests**

Create `backend/tests/test_models.py`:

```python
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from knowledge.models import Citation, Edition, HistoricalTimeSpan, Source


@pytest.mark.django_db
def test_time_span_rejects_reversed_range():
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            HistoricalTimeSpan.objects.create(
                start_year=1600,
                end_year=1500,
                precision="range",
                display_text="1600–1500",
            )


@pytest.mark.django_db
def test_citation_requires_locator_or_url():
    source = Source.objects.create(
        title="Synthetic test source",
        kind="book",
        license_status="metadata_only",
    )
    edition = Edition.objects.create(source=source, label="Test edition")
    citation = Citation(edition=edition, locator="", stable_url="")

    with pytest.raises(ValidationError):
        citation.full_clean()
```

- [ ] **Step 2: Run the tests and confirm model imports fail**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_models.py -q
```

Expected: collection FAIL because the model classes do not exist.

- [ ] **Step 3: Implement shared enumerations**

Create `backend/knowledge/models/enums.py`:

```python
from django.db import models


class TimePrecision(models.TextChoices):
    DAY = "day", "日"
    MONTH = "month", "月"
    YEAR = "year", "年"
    DECADE = "decade", "年代"
    CENTURY = "century", "世纪"
    CIRCA = "circa", "约"
    RANGE = "range", "区间"


class CalendarSystem(models.TextChoices):
    GREGORIAN = "gregorian", "公历"
    JULIAN = "julian", "儒略历"
    REGNAL = "regnal", "年号纪年"
    LUNAR = "lunar", "传统历法"
    OTHER = "other", "其他"


class SourceKind(models.TextChoices):
    PRIMARY = "primary", "一手史料"
    BOOK = "book", "学术书籍"
    ARTICLE = "article", "学术论文"
    REFERENCE = "reference", "工具书"
    DATASET = "dataset", "开放知识库"
    WEB = "web", "网页"


class LicenseStatus(models.TextChoices):
    PUBLIC_DOMAIN = "public_domain", "公版"
    OPEN = "open", "开放许可"
    AUTHORIZED = "authorized", "已授权"
    METADATA_ONLY = "metadata_only", "仅元数据与必要引文"
```

- [ ] **Step 4: Implement temporal and geographic models**

Create `backend/knowledge/models/temporal.py`:

```python
from django.db import models
from django.db.models import F, Q

from .enums import CalendarSystem, TimePrecision


class HistoricalTimeSpan(models.Model):
    start_year = models.IntegerField(
        help_text="Signed proleptic year; 0 represents 1 BCE."
    )
    end_year = models.IntegerField(
        help_text="Inclusive signed proleptic year; 0 represents 1 BCE."
    )
    precision = models.CharField(
        max_length=16,
        choices=TimePrecision.choices,
        default=TimePrecision.YEAR,
    )
    calendar = models.CharField(
        max_length=16,
        choices=CalendarSystem.choices,
        default=CalendarSystem.GREGORIAN,
    )
    display_text = models.CharField(max_length=128)

    class Meta:
        ordering = ["start_year", "end_year", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(start_year__lte=F("end_year")),
                name="knowledge_timespan_start_lte_end",
            )
        ]

    def __str__(self):
        return self.display_text
```

Create `backend/knowledge/models/geography.py`:

```python
from django.db import models


class Region(models.Model):
    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=128, unique=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Polity(models.Model):
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=160, unique=True)
    alternate_names = models.JSONField(default=list, blank=True)
    active_span = models.ForeignKey(
        "HistoricalTimeSpan",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="polities",
    )
    regions = models.ManyToManyField(Region, related_name="polities", blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "polities"

    def __str__(self):
        return self.name
```

- [ ] **Step 5: Implement source, edition, and citation models**

Create `backend/knowledge/models/source.py`:

```python
from django.core.exceptions import ValidationError
from django.db import models

from .enums import LicenseStatus, SourceKind


class Source(models.Model):
    title = models.CharField(max_length=512)
    kind = models.CharField(max_length=24, choices=SourceKind.choices)
    creators = models.JSONField(default=list, blank=True)
    canonical_url = models.URLField(blank=True)
    license_status = models.CharField(
        max_length=24,
        choices=LicenseStatus.choices,
    )
    license_note = models.TextField(blank=True)
    accessed_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["title", "id"]

    def __str__(self):
        return self.title


class Edition(models.Model):
    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="editions")
    label = models.CharField(max_length=256)
    publisher = models.CharField(max_length=256, blank=True)
    publication_year = models.IntegerField(null=True, blank=True)
    isbn = models.CharField(max_length=32, blank=True)
    external_id = models.CharField(max_length=128, blank=True)

    class Meta:
        ordering = ["source__title", "publication_year", "id"]

    def __str__(self):
        return f"{self.source.title} — {self.label}"


class Citation(models.Model):
    edition = models.ForeignKey(Edition, on_delete=models.PROTECT, related_name="citations")
    locator = models.CharField(max_length=256, blank=True)
    quotation = models.TextField(blank=True)
    stable_url = models.URLField(blank=True)

    class Meta:
        ordering = ["edition_id", "locator", "id"]

    def clean(self):
        super().clean()
        if not self.locator.strip() and not self.stable_url.strip():
            raise ValidationError("Citation requires a locator or stable URL.")

    def __str__(self):
        return f"{self.edition}: {self.locator or self.stable_url}"
```

Create `backend/knowledge/models/__init__.py`:

```python
from .geography import Polity, Region
from .source import Citation, Edition, Source
from .temporal import HistoricalTimeSpan

__all__ = [
    "Citation",
    "Edition",
    "HistoricalTimeSpan",
    "Polity",
    "Region",
    "Source",
]
```

Delete the scaffolded `backend/knowledge/models.py` so Django imports the package.

- [ ] **Step 6: Generate migrations and make the model tests pass**

```powershell
.\.venv\Scripts\python.exe manage.py makemigrations knowledge
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe -m pytest tests\test_models.py -q
.\.venv\Scripts\python.exe -m ruff check .
```

Expected: two passing tests and no lint errors.

- [ ] **Step 7: Commit foundational models**

```powershell
git add backend/knowledge backend/tests/test_models.py
git commit -m "feat: add temporal geography and source models"
```

---

### Task 3: Historical Content and Publication Workflow

**Files:**
- Create: `backend/knowledge/models/content.py`
- Modify: `backend/knowledge/models/enums.py`
- Modify: `backend/knowledge/models/__init__.py`
- Create: `backend/knowledge/services/__init__.py`
- Create: `backend/knowledge/services/publication.py`
- Create: `backend/tests/factories.py`
- Create: `backend/tests/test_publication.py`
- Create through Django: next `backend/knowledge/migrations/*.py`

**Interfaces:**
- Produces: `Topic`, `Person`, `Event`, `Snapshot`, `Claim`, and `ClaimRevision`.
- Produces: `publish_claim(*, claim: Claim, reviewer: User, reason: str) -> Claim`.
- Invariant: only a staff reviewer can publish.
- Invariant: only an approved claim with at least one valid citation can publish.

- [ ] **Step 1: Write failing publication tests**

Create `backend/tests/factories.py`:

```python
from django.contrib.auth import get_user_model

from knowledge.models import (
    Citation,
    Claim,
    Edition,
    HistoricalTimeSpan,
    Region,
    Source,
)


def make_staff_user(username="editor"):
    return get_user_model().objects.create_user(
        username=username,
        password="test-password",
        is_staff=True,
    )


def make_claim(*, workflow_state="approved"):
    span = HistoricalTimeSpan.objects.create(
        start_year=1520,
        end_year=1520,
        precision="year",
        display_text="1520",
    )
    region, _ = Region.objects.get_or_create(
        slug="test-region",
        defaults={"name": "Test Region"},
    )
    claim = Claim.objects.create(
        text="Synthetic historical claim for automated tests.",
        timespan=span,
        certainty="verified",
        workflow_state=workflow_state,
    )
    claim.regions.add(region)
    return claim


def add_citation(claim):
    source = Source.objects.create(
        title="Synthetic source for automated tests",
        kind="book",
        license_status="metadata_only",
    )
    edition = Edition.objects.create(source=source, label="Test edition")
    citation = Citation.objects.create(
        edition=edition,
        locator="p. 1",
        stable_url="https://example.test/source",
    )
    claim.citations.add(citation)
    return citation
```

Create `backend/tests/test_publication.py`:

```python
import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from knowledge.models import ClaimRevision
from knowledge.services.publication import publish_claim
from tests.factories import add_citation, make_claim, make_staff_user


@pytest.mark.django_db
def test_publish_claim_requires_citation():
    claim = make_claim()
    reviewer = make_staff_user()

    with pytest.raises(ValidationError, match="citation"):
        publish_claim(claim=claim, reviewer=reviewer, reason="Reviewed against source")


@pytest.mark.django_db
def test_publish_claim_requires_staff_reviewer(django_user_model):
    claim = make_claim()
    add_citation(claim)
    reviewer = django_user_model.objects.create_user(username="reader")

    with pytest.raises(PermissionDenied):
        publish_claim(claim=claim, reviewer=reviewer, reason="Not authorized")


@pytest.mark.django_db
def test_publish_claim_records_revision():
    claim = make_claim()
    add_citation(claim)
    reviewer = make_staff_user()

    published = publish_claim(
        claim=claim,
        reviewer=reviewer,
        reason="Citation and wording verified",
    )

    assert published.workflow_state == "published"
    assert published.published_at is not None
    revision = ClaimRevision.objects.get(claim=published)
    assert revision.reviewer == reviewer
    assert revision.reason == "Citation and wording verified"
```

- [ ] **Step 2: Run the publication tests and confirm imports fail**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_publication.py -q
```

Expected: collection FAIL because content models and publication service do not exist.

- [ ] **Step 3: Add content workflow enumerations**

Append to `backend/knowledge/models/enums.py`:

```python
class ClaimCertainty(models.TextChoices):
    VERIFIED = "verified", "已证实"
    INFERRED = "inferred", "学界推断"
    DISPUTED = "disputed", "存在争议"
    UNVERIFIED = "unverified", "待核查"


class WorkflowState(models.TextChoices):
    DRAFT = "draft", "草稿"
    IN_REVIEW = "in_review", "审核中"
    APPROVED = "approved", "已批准"
    PUBLISHED = "published", "已发布"
    WITHDRAWN = "withdrawn", "已撤回"


class SnapshotDimension(models.TextChoices):
    POLITICS = "politics", "政治"
    ECONOMY = "economy", "经济"
    SOCIETY = "society", "社会"
    TECHNOLOGY = "technology", "科技"
    CULTURE = "culture", "文化"
```

- [ ] **Step 4: Implement historical content models**

Create `backend/knowledge/models/content.py`:

```python
from django.conf import settings
from django.db import models

from .enums import ClaimCertainty, SnapshotDimension, WorkflowState


class Topic(models.Model):
    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=128, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Person(models.Model):
    name = models.CharField(max_length=160)
    alternate_names = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class Event(models.Model):
    title = models.CharField(max_length=256)
    timespan = models.ForeignKey(
        "HistoricalTimeSpan",
        on_delete=models.PROTECT,
        related_name="events",
    )
    regions = models.ManyToManyField("Region", related_name="events")
    polities = models.ManyToManyField("Polity", related_name="events", blank=True)
    people = models.ManyToManyField(Person, related_name="events", blank=True)
    topics = models.ManyToManyField(Topic, related_name="events", blank=True)

    class Meta:
        ordering = ["timespan__start_year", "title", "id"]

    def __str__(self):
        return self.title


class Snapshot(models.Model):
    label = models.CharField(max_length=256)
    region = models.ForeignKey("Region", on_delete=models.PROTECT, related_name="snapshots")
    polity = models.ForeignKey(
        "Polity",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="snapshots",
    )
    timespan = models.ForeignKey(
        "HistoricalTimeSpan",
        on_delete=models.PROTECT,
        related_name="snapshots",
    )
    dimension = models.CharField(max_length=24, choices=SnapshotDimension.choices)

    class Meta:
        ordering = ["timespan__start_year", "region__sort_order", "dimension", "id"]

    def __str__(self):
        return self.label


class Claim(models.Model):
    text = models.TextField()
    timespan = models.ForeignKey(
        "HistoricalTimeSpan",
        on_delete=models.PROTECT,
        related_name="claims",
    )
    certainty = models.CharField(max_length=24, choices=ClaimCertainty.choices)
    workflow_state = models.CharField(
        max_length=24,
        choices=WorkflowState.choices,
        default=WorkflowState.DRAFT,
    )
    ai_generated = models.BooleanField(default=False)
    regions = models.ManyToManyField("Region", related_name="claims")
    polities = models.ManyToManyField("Polity", related_name="claims", blank=True)
    topics = models.ManyToManyField(Topic, related_name="claims", blank=True)
    event = models.ForeignKey(
        Event,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="claims",
    )
    snapshot = models.ForeignKey(
        Snapshot,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="claims",
    )
    citations = models.ManyToManyField("Citation", related_name="claims")
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["timespan__start_year", "id"]

    def __str__(self):
        return self.text[:80]


class ClaimRevision(models.Model):
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="revisions")
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="claim_revisions",
    )
    from_state = models.CharField(max_length=24, choices=WorkflowState.choices)
    to_state = models.CharField(max_length=24, choices=WorkflowState.choices)
    text_snapshot = models.TextField()
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
```

Update `backend/knowledge/models/__init__.py` to import and export all content classes:

```python
from .content import Claim, ClaimRevision, Event, Person, Snapshot, Topic
from .geography import Polity, Region
from .source import Citation, Edition, Source
from .temporal import HistoricalTimeSpan

__all__ = [
    "Citation",
    "Claim",
    "ClaimRevision",
    "Edition",
    "Event",
    "HistoricalTimeSpan",
    "Person",
    "Polity",
    "Region",
    "Snapshot",
    "Source",
    "Topic",
]
```

- [ ] **Step 5: Implement the guarded publication service**

Create `backend/knowledge/services/__init__.py` as an empty file.

Create `backend/knowledge/services/publication.py`:

```python
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from knowledge.models import Claim, ClaimRevision
from knowledge.models.enums import WorkflowState


@transaction.atomic
def publish_claim(*, claim: Claim, reviewer, reason: str) -> Claim:
    if not reviewer.is_staff:
        raise PermissionDenied("Only staff reviewers can publish claims.")
    if claim.workflow_state != WorkflowState.APPROVED:
        raise ValidationError("Claim must be approved before publication.")
    if not reason.strip():
        raise ValidationError("Publication requires a review reason.")
    if not claim.citations.exists():
        raise ValidationError("Published claim requires at least one citation.")
    for citation in claim.citations.all():
        citation.full_clean()

    previous_state = claim.workflow_state
    claim.workflow_state = WorkflowState.PUBLISHED
    claim.published_at = timezone.now()
    claim.save(update_fields=["workflow_state", "published_at", "updated_at"])
    ClaimRevision.objects.create(
        claim=claim,
        reviewer=reviewer,
        from_state=previous_state,
        to_state=WorkflowState.PUBLISHED,
        text_snapshot=claim.text,
        reason=reason.strip(),
    )
    return claim
```

- [ ] **Step 6: Generate migrations and verify publication behavior**

```powershell
.\.venv\Scripts\python.exe manage.py makemigrations knowledge
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe -m pytest tests\test_publication.py -q
.\.venv\Scripts\python.exe -m ruff check .
```

Expected: three passing publication tests and no lint errors.

- [ ] **Step 7: Commit content workflow**

```powershell
git add backend/knowledge backend/tests
git commit -m "feat: add historical claims and guarded publication"
```

---

### Task 4: Published Year-Slice Selector

**Files:**
- Create: `backend/knowledge/services/year_slice.py`
- Create: `backend/tests/test_year_slice_service.py`

**Interfaces:**
- Consumes: published `Claim` records and their `HistoricalTimeSpan`, regions, topics, citations, events, and snapshots.
- Produces: `select_year_slice(*, year: int, region_ids: Sequence[int] = (), topic_slugs: Sequence[str] = ()) -> QuerySet[Claim]`.
- Result includes a claim when `start_year <= year <= end_year`.
- Result excludes all non-published states.

- [ ] **Step 1: Write failing selector tests**

Create `backend/tests/test_year_slice_service.py`:

```python
import pytest

from knowledge.models import Topic
from knowledge.services.publication import publish_claim
from knowledge.services.year_slice import select_year_slice
from tests.factories import add_citation, make_claim, make_staff_user


@pytest.mark.django_db
def test_selector_returns_only_published_claims_active_in_year():
    reviewer = make_staff_user()
    published = make_claim()
    add_citation(published)
    publish_claim(claim=published, reviewer=reviewer, reason="Verified")
    make_claim(workflow_state="draft")

    result = list(select_year_slice(year=1520))

    assert result == [published]


@pytest.mark.django_db
def test_selector_filters_by_region_and_topic():
    reviewer = make_staff_user()
    claim = make_claim()
    topic = Topic.objects.create(name="政治", slug="politics")
    claim.topics.add(topic)
    add_citation(claim)
    publish_claim(claim=claim, reviewer=reviewer, reason="Verified")
    region_id = claim.regions.get().id

    assert list(
        select_year_slice(
            year=1520,
            region_ids=[region_id],
            topic_slugs=["politics"],
        )
    ) == [claim]
    assert list(select_year_slice(year=1519, region_ids=[region_id])) == []
```

- [ ] **Step 2: Run tests and confirm the selector is missing**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_year_slice_service.py -q
```

Expected: collection FAIL because `knowledge.services.year_slice` does not exist.

- [ ] **Step 3: Implement the optimized selector**

Create `backend/knowledge/services/year_slice.py`:

```python
from collections.abc import Sequence

from django.db.models import QuerySet

from knowledge.models import Claim
from knowledge.models.enums import WorkflowState


def select_year_slice(
    *,
    year: int,
    region_ids: Sequence[int] = (),
    topic_slugs: Sequence[str] = (),
) -> QuerySet[Claim]:
    claims = (
        Claim.objects.filter(
            workflow_state=WorkflowState.PUBLISHED,
            timespan__start_year__lte=year,
            timespan__end_year__gte=year,
        )
        .select_related("timespan", "event", "snapshot")
        .prefetch_related(
            "regions",
            "topics",
            "citations__edition__source",
        )
    )
    if region_ids:
        claims = claims.filter(regions__id__in=region_ids)
    if topic_slugs:
        claims = claims.filter(topics__slug__in=topic_slugs)
    return claims.distinct().order_by(
        "timespan__start_year",
        "timespan__end_year",
        "id",
    )
```

- [ ] **Step 4: Verify selector behavior and query quality**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_year_slice_service.py -q
.\.venv\Scripts\python.exe -m ruff check .
```

Expected: two passing selector tests and no lint errors.

- [ ] **Step 5: Commit selector**

```powershell
git add backend/knowledge/services/year_slice.py backend/tests/test_year_slice_service.py
git commit -m "feat: select published claims by year"
```

---

### Task 5: Read-Only Year-Slice API

**Files:**
- Create: `backend/knowledge/api/serializers.py`
- Create: `backend/knowledge/api/views.py`
- Modify: `backend/knowledge/api/urls.py`
- Create: `backend/tests/test_year_slice_api.py`

**Interfaces:**
- Consumes: `select_year_slice`.
- Produces: `GET /api/v1/timeline/year-slice/?year=1520`.
- Accepts repeated `region` integer parameters and repeated `topic` slug parameters.
- Returns HTTP 400 for missing or invalid year.
- Returns published claims grouped by region.

- [ ] **Step 1: Write failing API contract tests**

Create `backend/tests/test_year_slice_api.py`:

```python
import pytest
from django.urls import reverse

from knowledge.models import Topic
from knowledge.services.publication import publish_claim
from tests.factories import add_citation, make_claim, make_staff_user


@pytest.mark.django_db
def test_year_slice_api_groups_claims_by_region(client):
    claim = make_claim()
    topic = Topic.objects.create(name="政治", slug="politics")
    claim.topics.add(topic)
    add_citation(claim)
    publish_claim(
        claim=claim,
        reviewer=make_staff_user(),
        reason="Verified",
    )

    response = client.get(
        reverse("knowledge_api:year-slice"),
        {"year": "1520", "topic": "politics"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["year"] == 1520
    assert payload["regions"][0]["name"] == "Test Region"
    assert payload["regions"][0]["claims"][0]["text"] == claim.text
    assert payload["regions"][0]["claims"][0]["citations"][0]["locator"] == "p. 1"


@pytest.mark.django_db
@pytest.mark.parametrize("query", [{}, {"year": "not-a-year"}, {"year": "12000"}])
def test_year_slice_api_rejects_invalid_year(client, query):
    response = client.get(reverse("knowledge_api:year-slice"), query)

    assert response.status_code == 400
```

- [ ] **Step 2: Run API tests and confirm the route is absent**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_year_slice_api.py -q
```

Expected: FAIL because `knowledge_api:year-slice` is not registered.

- [ ] **Step 3: Implement explicit serializers**

Create `backend/knowledge/api/serializers.py`:

```python
from rest_framework import serializers

from knowledge.models import Citation, Claim, Topic


class YearSliceQuerySerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=-10000, max_value=3000)
    region = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        default=list,
    )
    topic = serializers.ListField(
        child=serializers.SlugField(),
        required=False,
        default=list,
    )


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ["slug", "name"]


class CitationSerializer(serializers.ModelSerializer):
    source_title = serializers.CharField(source="edition.source.title")
    edition_label = serializers.CharField(source="edition.label")

    class Meta:
        model = Citation
        fields = [
            "id",
            "source_title",
            "edition_label",
            "locator",
            "quotation",
            "stable_url",
        ]


class ClaimSerializer(serializers.ModelSerializer):
    time_label = serializers.CharField(source="timespan.display_text")
    topics = TopicSerializer(many=True)
    citations = CitationSerializer(many=True)

    class Meta:
        model = Claim
        fields = [
            "id",
            "text",
            "certainty",
            "time_label",
            "topics",
            "citations",
            "event_id",
            "snapshot_id",
        ]
```

- [ ] **Step 4: Implement grouping view and route**

Create `backend/knowledge/api/views.py`:

```python
from rest_framework.response import Response
from rest_framework.views import APIView

from knowledge.api.serializers import (
    ClaimSerializer,
    YearSliceQuerySerializer,
)
from knowledge.services.year_slice import select_year_slice


class YearSliceView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        query = YearSliceQuerySerializer(
            data={
                "year": request.query_params.get("year"),
                "region": request.query_params.getlist("region"),
                "topic": request.query_params.getlist("topic"),
            }
        )
        query.is_valid(raise_exception=True)
        values = query.validated_data
        claims = select_year_slice(
            year=values["year"],
            region_ids=values["region"],
            topic_slugs=values["topic"],
        )

        grouped = {}
        for claim in claims:
            serialized_claim = ClaimSerializer(claim).data
            for region in claim.regions.all():
                region_group = grouped.setdefault(
                    region.id,
                    {
                        "id": region.id,
                        "slug": region.slug,
                        "name": region.name,
                        "sort_order": region.sort_order,
                        "claims": [],
                    },
                )
                region_group["claims"].append(serialized_claim)

        regions = sorted(
            grouped.values(),
            key=lambda item: (item["sort_order"], item["name"]),
        )
        for region in regions:
            region.pop("sort_order")
        return Response({"year": values["year"], "regions": regions})
```

Replace `backend/knowledge/api/urls.py` with:

```python
from django.urls import path

from knowledge.api.views import YearSliceView

app_name = "knowledge_api"

urlpatterns = [
    path(
        "timeline/year-slice/",
        YearSliceView.as_view(),
        name="year-slice",
    ),
]
```

- [ ] **Step 5: Verify API behavior**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_year_slice_api.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
```

Expected: API tests and the full suite pass; Ruff reports no errors.

- [ ] **Step 6: Commit API**

```powershell
git add backend/knowledge/api backend/tests/test_year_slice_api.py
git commit -m "feat: expose published year slice API"
```

---

### Task 6: Editorial Admin and Reference Data

**Files:**
- Modify: `backend/knowledge/admin.py`
- Create: `backend/knowledge/management/__init__.py`
- Create: `backend/knowledge/management/commands/__init__.py`
- Create: `backend/knowledge/management/commands/load_reference_data.py`
- Create: `backend/tests/test_admin.py`
- Create: `backend/tests/test_reference_data.py`

**Interfaces:**
- Produces: searchable and filterable Django Admin pages for claims, citations, sources, editions, events, snapshots, regions, polities, topics, and people.
- Produces: admin actions that move draft claims to review and review claims to approved.
- Does not provide a bulk `published` state update; publication remains guarded by `publish_claim`.
- Produces: idempotent `manage.py load_reference_data`.

- [ ] **Step 1: Write failing admin and reference-data tests**

Create `backend/tests/test_admin.py`:

```python
from django.contrib import admin

from knowledge.admin import publish_approved
from knowledge.models import Citation, Claim, Event, Region, Snapshot, Source


def test_core_models_are_registered_in_admin():
    for model in [Claim, Citation, Source, Event, Snapshot, Region]:
        assert model in admin.site._registry

    claim_admin = admin.site._registry[Claim]
    assert "workflow_state" in claim_admin.readonly_fields
    assert publish_approved in claim_admin.actions
```

Create `backend/tests/test_reference_data.py`:

```python
import pytest
from django.core.management import call_command

from knowledge.models import Region, Topic


@pytest.mark.django_db
def test_reference_data_command_is_idempotent():
    call_command("load_reference_data")
    call_command("load_reference_data")

    assert Region.objects.filter(parent=None).count() == 4
    assert set(Topic.objects.values_list("slug", flat=True)) == {
        "politics",
        "economy",
        "society",
        "technology",
        "culture",
    }
```

- [ ] **Step 2: Run tests and confirm admin registrations and command are missing**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_admin.py tests\test_reference_data.py -q
```

Expected: FAIL because core models are unregistered and `load_reference_data` is unknown.

- [ ] **Step 3: Configure the editorial admin**

Replace `backend/knowledge/admin.py` with:

```python
from django.contrib import admin, messages

from knowledge.models import (
    Citation,
    Claim,
    ClaimRevision,
    Edition,
    Event,
    HistoricalTimeSpan,
    Person,
    Polity,
    Region,
    Snapshot,
    Source,
    Topic,
)
from knowledge.models.enums import WorkflowState
from knowledge.services.publication import publish_claim


@admin.action(description="Move selected claims to review")
def move_to_review(_modeladmin, _request, queryset):
    queryset.filter(workflow_state=WorkflowState.DRAFT).update(
        workflow_state=WorkflowState.IN_REVIEW
    )


@admin.action(description="Approve selected reviewed claims")
def approve_reviewed(_modeladmin, _request, queryset):
    queryset.filter(workflow_state=WorkflowState.IN_REVIEW).update(
        workflow_state=WorkflowState.APPROVED
    )


@admin.action(description="Publish selected approved claims")
def publish_approved(modeladmin, request, queryset):
    published_count = 0
    for claim in queryset.filter(workflow_state=WorkflowState.APPROVED):
        publish_claim(
            claim=claim,
            reviewer=request.user,
            reason="Published through reviewed admin action.",
        )
        published_count += 1
    modeladmin.message_user(
        request,
        f"Published {published_count} claims.",
        level=messages.SUCCESS,
    )


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ["id", "short_text", "certainty", "workflow_state", "published_at"]
    list_filter = ["certainty", "workflow_state", "ai_generated", "topics", "regions"]
    search_fields = ["text"]
    filter_horizontal = ["regions", "polities", "topics", "citations"]
    readonly_fields = ["workflow_state", "published_at", "created_at", "updated_at"]
    actions = [move_to_review, approve_reviewed, publish_approved]

    @admin.display(description="Claim")
    def short_text(self, obj):
        return obj.text[:80]


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ["title", "kind", "license_status", "accessed_on"]
    list_filter = ["kind", "license_status"]
    search_fields = ["title", "creators", "canonical_url"]


@admin.register(Citation)
class CitationAdmin(admin.ModelAdmin):
    list_display = ["edition", "locator", "stable_url"]
    search_fields = ["edition__source__title", "locator", "quotation", "stable_url"]


admin.site.register(
    [
        ClaimRevision,
        Edition,
        Event,
        HistoricalTimeSpan,
        Person,
        Polity,
        Region,
        Snapshot,
        Topic,
    ]
)
```

- [ ] **Step 4: Implement idempotent reference-data loading**

Create empty package files:

```text
backend/knowledge/management/__init__.py
backend/knowledge/management/commands/__init__.py
```

Create `backend/knowledge/management/commands/load_reference_data.py`:

```python
from django.core.management.base import BaseCommand, no_translations

from knowledge.models import Region, Topic


REGIONS = [
    ("east-asia", "东亚", 10),
    ("west-asia-north-africa", "西亚与北非", 20),
    ("europe", "欧洲", 30),
    ("americas", "美洲", 40),
]

TOPICS = [
    ("politics", "政治"),
    ("economy", "经济"),
    ("society", "社会"),
    ("technology", "科技"),
    ("culture", "文化"),
]


class Command(BaseCommand):
    help = "Load Changhe regions and timeline topics."

    @no_translations
    def handle(self, *args, **options):
        for slug, name, sort_order in REGIONS:
            Region.objects.update_or_create(
                slug=slug,
                defaults={"name": name, "sort_order": sort_order},
            )
        for slug, name in TOPICS:
            Topic.objects.update_or_create(slug=slug, defaults={"name": name})
        self.stdout.write(self.style.SUCCESS("Reference data loaded."))
```

- [ ] **Step 5: Verify editorial tooling**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_admin.py tests\test_reference_data.py -q
.\.venv\Scripts\python.exe manage.py load_reference_data
.\.venv\Scripts\python.exe -m ruff check .
```

Expected: two passing tests, `Reference data loaded.`, and no lint errors.

- [ ] **Step 6: Commit editorial tooling**

```powershell
git add backend/knowledge/admin.py backend/knowledge/management backend/tests
git commit -m "feat: add editorial admin and reference data"
```

---

### Task 7: PostgreSQL Verification and Operator Documentation

**Files:**
- Modify: `README.md`
- Modify: `backend/tests/test_year_slice_api.py`

**Interfaces:**
- Produces: a documented local path from fresh checkout to PostgreSQL-backed API.
- Verifies: migrations, system checks, full tests, lint, anonymous API access, and PostgreSQL execution.

- [ ] **Step 1: Add an anonymous-access regression test**

Append to `backend/tests/test_year_slice_api.py`:

```python
@pytest.mark.django_db
def test_year_slice_api_does_not_require_login(client):
    response = client.get(reverse("knowledge_api:year-slice"), {"year": "1520"})

    assert response.status_code == 200
    assert response.json() == {"year": 1520, "regions": []}
```

- [ ] **Step 2: Run the regression test**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_year_slice_api.py -q
```

Expected: all year-slice API tests pass.

- [ ] **Step 3: Document setup, validation, and API use**

Replace `README.md` with:

````markdown
# 长河

长河是一款以全球并行时间线和可追溯史料为核心的 Android 历史浏览应用。

## 当前实现

当前仓库包含知识后台纵向切片：

- 带时间精度的历史陈述模型
- 来源、版本和引用模型
- 人工审核后发布的工作流
- Django Admin 内容管理
- 匿名只读的年度切片 API

## 本地运行

要求：Python 3.13、Docker Desktop、PowerShell。

```powershell
docker compose up -d db
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
$env:DATABASE_URL = "postgresql://changhe:changhe-local@localhost:5432/changhe"
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py load_reference_data
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

打开：

- 健康检查：http://127.0.0.1:8000/health/
- 内容后台：http://127.0.0.1:8000/admin/
- 年度切片：http://127.0.0.1:8000/api/v1/timeline/year-slice/?year=1520

## 验证

```powershell
cd backend
$env:DATABASE_URL = "postgresql://changhe:changhe-local@localhost:5432/changhe"
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
```

## 内容规则

- AI 输出只能保存为候选草稿。
- 发布操作需要员工审核者、审核原因和至少一个有效引用。
- 未获授权的全文不得进入仓库或同步包。
- 历史日期必须保留来源提供的精度和不确定性。
````

- [ ] **Step 4: Run the full suite against PostgreSQL**

Run from repository root:

```powershell
docker compose up -d db
cd backend
$env:DATABASE_URL = "postgresql://changhe:changhe-local@localhost:5432/changhe"
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
```

Expected:

```text
System check identified no issues (0 silenced).
All tests pass.
All checks passed!
```

- [ ] **Step 5: Smoke-test the running API**

Start the server:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

In a second PowerShell terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/timeline/year-slice/?year=1520"
```

Expected JSON values:

```json
{"status":"ok"}
{"year":1520,"regions":[]}
```

- [ ] **Step 6: Commit verified vertical slice**

```powershell
git add README.md backend/tests/test_year_slice_api.py
git commit -m "docs: document backend setup and verification"
git status --short
```

Expected: the final `git status --short` output is empty.

## Final Acceptance Checklist

- [ ] `docker compose up -d db` reaches a healthy PostgreSQL 17 service.
- [ ] Fresh migrations apply to PostgreSQL without manual edits.
- [ ] `manage.py check` reports no issues.
- [ ] All pytest tests pass against PostgreSQL.
- [ ] Ruff reports no errors.
- [ ] `/health/` is available.
- [ ] `/api/v1/timeline/year-slice/?year=1520` works anonymously.
- [ ] Draft and approved claims never appear in the public endpoint.
- [ ] Published claims require a staff reviewer, reason, and valid citation.
- [ ] Reference-data loading is idempotent.
- [ ] Django Admin keeps `workflow_state` read-only and its publish action calls the guarded publication service.
