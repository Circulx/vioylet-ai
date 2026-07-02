# Core application plumbing lives here: settings, security helpers, dependency gates, and shared errors.
from enum import StrEnum


class RoleCode(StrEnum):
    # Core runtime shape for role code; dependency and security helpers share this instead of passing loose
    # dictionaries.
    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    TENANT_USER = "tenant_user"
    BRAND_USER = "brand_user"
    EXTERNAL_REVIEWER = "external_reviewer"


class BrandSpaceLifecycle(StrEnum):
    # Core runtime shape for brand space lifecycle; dependency and security helpers share this instead of
    # passing loose dictionaries.
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ContentLifecycle(StrEnum):
    # Core runtime shape for content lifecycle; dependency and security helpers share this instead of passing
    # loose dictionaries.
    GENERATED = "generated"
    EDITED = "edited"
    ORGANIZED = "organized"
    SHARED = "shared"
    ARCHIVED = "archived"


class AssetLifecycle(StrEnum):
    # Core runtime shape for asset lifecycle; dependency and security helpers share this instead of passing
    # loose dictionaries.
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    DELETED = "deleted"


class BrandAssetField(StrEnum):
    # Core runtime shape for brand asset field; dependency and security helpers share this instead of passing
    # loose dictionaries.
    LOGO = "logo"
    AUDIENCE_INSIGHTS = "audience_insights"
    REFERENCE_CREATIVES = "reference_creatives"
    MOOD_BOARD = "mood_board"
    COLOR_PALETTE = "color_palette"
    FONT_GUIDE = "font_guide"
    POSITIVE_WORD_BANK = "positive_word_bank"
    NEGATIVE_WORD_BANK = "negative_word_bank"
    REPLACEABLE_WORD_BANK = "replaceable_word_bank"
    BRAND_KNOWLEDGE_TEMPLATES = "brand_knowledge_templates"
    BRAND_KNOWLEDGE_OTHER = "brand_knowledge_other"


class BrandAssetCategory(StrEnum):
    # Core runtime shape for brand asset category; dependency and security helpers share this instead of passing
    # loose dictionaries.
    LOGO = "logo"
    AUDIENCE_INSIGHT = "audience_insight"
    REFERENCE_CREATIVE = "reference_creative"
    MOOD_BOARD = "mood_board"
    COLOR_PALETTE = "color_palette"
    TYPOGRAPHY_GUIDE = "typography_guide"
    POSITIVE_WORD_BANK = "positive_word_bank"
    NEGATIVE_WORD_BANK = "negative_word_bank"
    REPLACEABLE_WORD_BANK = "replaceable_word_bank"
    TEMPLATE = "template"
    USER_UPLOAD_FOR_GENERATION = "user_upload_for_generation"  # 🔥 PHASE 3
    KNOWLEDGE_OTHER = "knowledge_other"
    ICON = "icon"
    DECORATIVE_ASSET = "decorative_asset"
    UNKNOWN = "unknown"


class AssetValidationState(StrEnum):
    # Core runtime shape for asset validation state; dependency and security helpers share this instead of
    # passing loose dictionaries.
    PENDING = "pending"
    CLEAN = "clean"
    WARNING = "warning"
    EXCLUDED = "excluded"


class ConflictSeverity(StrEnum):
    # Core runtime shape for conflict severity; dependency and security helpers share this instead of passing
    # loose dictionaries.
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class BrandSectionCode(StrEnum):
    # Core runtime shape for brand section code; dependency and security helpers share this instead of passing
    # loose dictionaries.
    IDENTITY = "identity"
    FOUNDATIONS = "foundations"
    VOICE_TONE = "voice_tone"
    PERSONAS = "personas"
    GUARDRAILS = "guardrails"
    KNOWLEDGE = "knowledge"
    PROMPT_INTELLIGENCE = "prompt_intelligence"
    OBJECTIVES = "objectives"
    VISUAL_IDENTITY = "visual_identity"
    REVIEW = "review"


class KnowledgeChannel(StrEnum):
    # Core runtime shape for knowledge channel; dependency and security helpers share this instead of passing
    # loose dictionaries.
    BRAND = "brand"
    STRATEGY = "strategy"
    METADATA = "metadata"
    TEMPLATE = "template"
    CAMPAIGN_HISTORY = "campaign_history"


class TemplateKind(StrEnum):
    # Core runtime shape for template kind; dependency and security helpers share this instead of passing loose
    # dictionaries.
    PROMPT_FRAMEWORK = "prompt_framework"
    LAYOUT = "layout"
    HYBRID = "hybrid"


class StudioFormat(StrEnum):
    # Core runtime shape for studio format; dependency and security helpers share this instead of passing loose
    # dictionaries.
    STATIC = "static"
    CAROUSEL = "carousel"
    PDF = "pdf"
    INFOGRAPHIC = "infographic"


class PlatformPreset(StrEnum):
    # Core runtime shape for platform preset; dependency and security helpers share this instead of passing
    # loose dictionaries.
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    X = "x"
    YOUTUBE_THUMBNAIL = "youtube_thumbnail"


class ExportFileType(StrEnum):
    # Core runtime shape for export file type; dependency and security helpers share this instead of passing
    # loose dictionaries.
    DOC = "doc"
    PDF = "pdf"
    PNG = "png"
    JPG = "jpg"


class AssetRole(StrEnum):
    # Core runtime shape for asset role; dependency and security helpers share this instead of passing loose
    # dictionaries.
    LOGO = "logo"
    AI_IMAGE = "ai_image"
    TEMPLATE_PREVIEW = "template_preview"
    RENDER_PREVIEW = "render_preview"
    RENDER_EXPORT = "render_export"
    KNOWLEDGE_UPLOAD = "knowledge_upload"
    REFERENCE_CREATIVE = "reference_creative"
    GENERATED_DOCUMENT = "generated_document"


class ReviewStatus(StrEnum):
    # Core runtime shape for review status; dependency and security helpers share this instead of passing loose
    # dictionaries.
    PENDING = "pending"
    APPROVED = "approved"
    NEEDS_CHANGES = "needs_changes"


class JobStatus(StrEnum):
    # Core runtime shape for job status; dependency and security helpers share this instead of passing loose
    # dictionaries.
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(StrEnum):
    # Core runtime shape for job type; dependency and security helpers share this instead of passing loose
    # dictionaries.
    KNOWLEDGE_PROCESS = "knowledge_process"
    TEMPLATE_ANALYSIS = "template_analysis"
    BRAND_CONTEXT_REFRESH = "brand_context_refresh"
    RAGAS_EVALUATION = "ragas_evaluation"
    RENDER_PREVIEW = "render_preview"
    RENDER_EXPORT = "render_export"
    SOCIAL_PUBLISH = "social_publish"


class SocialPlatform(StrEnum):
    # Core runtime shape for social platform; dependency and security helpers share this instead of passing
    # loose dictionaries.
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    X = "x"


class UsageMetricCode(StrEnum):
    # Core runtime shape for usage metric code; dependency and security helpers share this instead of passing
    # loose dictionaries.
    USERS = "users"
    BRAND_SPACES = "brand_spaces"
    CONTENT_GENERATIONS = "content_generations"
    IMAGE_GENERATIONS = "image_generations"
    OCR_PAGES = "ocr_pages"
