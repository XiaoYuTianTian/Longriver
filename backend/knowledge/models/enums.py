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
