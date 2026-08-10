import type { Role } from "@/types/rbac.types";

export type UUID = string;

export type PlatformPreset = "instagram" | "linkedin" | "x" | "youtube_thumbnail";
export type StudioFormat = "static" | "carousel" | "pdf" | "infographic";
export type ExportFileType = "doc" | "pdf" | "png" | "jpg";

export interface TokenPairResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}

export interface TwoFactorChallengeResponse {
  requires_two_factor: true;
  two_factor_ticket: string;
  delivery: "authenticator";
  email: string;
}

export type LoginResponse = TokenPairResponse | TwoFactorChallengeResponse;

export interface CurrentUserResponse {
  user_id: UUID;
  tenant_id?: UUID;
  email: string;
  full_name: string;
  role_codes: string[];
  assigned_brand_space_ids: UUID[];
  extra: Record<string, unknown>;
}

export interface InAppNotificationResponse {
  id: UUID;
  title: string;
  message: string;
  created_at: string;
  unread: boolean;
}

export interface InAppNotificationUnreadCountResponse {
  unread_count: number;
}

export interface BrandSpaceHistoryResponse {
  id: UUID;
  tenant_id: UUID;
  brand_space_id: UUID;
  activity_type: string;
  message: string;
  performed_by?: UUID | null;
  created_at: string;
}
export interface UiUser {
  id: UUID;
  tenantId?: UUID;
  email: string;
  name: string;
  role: Role;
  roleCodes: string[];
  brandSpaceIds: UUID[];
  phone?: string;
  notificationsEnabled?: boolean;
  twoFactorEnabled?: boolean;
}

export interface TwoFactorSetupResponse {
  enabled: boolean;
  pending_setup: boolean;
  secret?: string | null;
  otpauth_url?: string | null;
  qr_code_url?: string | null;
}

export interface TenantUsageLimits {
  max_users: number;
  max_brand_spaces: number;
  max_content_generations: number;
  max_image_generations: number;
  max_ocr_pages: number;
}

export interface TenantSummaryResponse {
  id: UUID;
  name: string;
  slug: string;
  contact_email: string;
  contact_number?: string;
  address?: string;
  logo_asset_path?: string;
  is_active: boolean;
  total_users: number;
  brand_space_count: number;
  usage_limits?: TenantUsageLimits;
  usage_consumption: Record<string, number>;
  token_usage: Record<string, number>;
  monthly_token_usage: Array<{
    month: string;
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  }>;
  metadata_json: Record<string, unknown>;
  created_at: string;
  tenant_admin_name?: string;
  tenant_admin_email?: string;
  tenant_admin_phone_number?: string;
  tenant_admin_user_id?: UUID | null;
  tenant_admin_is_active?: boolean | null;
  tenant_admin_is_activated?: boolean | null;
  tenant_admin_activation_link_sent_count?: number;
  tenant_admin_activation_link_attempts_left?: number;
  last_active_at?: string | null;
}

export interface TenantCreateResponse {
  id: UUID;
  name: string;
  slug: string;
  contact_email: string;
  contact_number?: string;
  address?: string;
  logo_asset_path?: string;
  is_active: boolean;
  metadata_json: Record<string, unknown>;
  created_at: string;
  activation_email: ActivationEmailStatus;
}

export interface ActivationEmailStatus {
  attempted: boolean;
  delivered: boolean;
  recipient_email: string;
  reason?: string | null;
}

export interface TenantCreateRequest {
  name: string;
  slug: string;
  contact_email: string;
  contact_number?: string;
  address?: string;
  admin_full_name: string;
  admin_email: string;
  admin_phone_number?: string;
  usage_limits: TenantUsageLimits;
  metadata_json?: Record<string, unknown>;
}

export type TenantUpdateRequest = Partial<TenantCreateRequest> & {
  metadata_json?: Record<string, unknown>;
  is_active?: boolean;
};

export interface TenantLogoUploadRequest {
  filename: string;
  mime_type: string;
  content_base64: string;
}

export interface TenantUserResponse {
  id: UUID;
  user_id?: UUID;
  tenant_id?: UUID;
  email: string;
  full_name: string;
  phone_number?: string;
  is_active: boolean;
  is_activated: boolean;
  role_codes: string[];
  brand_space_ids: UUID[];
  created_at: string;
  last_login_at?: string | null;
  activation_link_sent_count?: number;
  activation_link_attempts_left?: number;
  activation_email?: ActivationEmailStatus;
  notifications_enabled?: boolean;
}

export interface TenantBrandSpaceSummaryResponse {
  id: UUID;
  tenant_id: UUID;
  name: string;
  slug: string;
  lifecycle_state: string;
  created_at: string;
  last_active_at?: string | null;
  last_login_at?: string | null;
  content_generations: number;
  visual_generations: number;
  ocr_pages: number;
}

export interface TenantUserCreateRequest {
  full_name: string;
  email: string;
  phone_number?: string;
  role_code: string;
  brand_space_ids: UUID[];
}

export interface TenantUserUpdateRequest {
  full_name?: string;
  email?: string;
  phone_number?: string;
  role_code?: string;
  brand_space_ids?: UUID[];
  is_active?: boolean;
}

export interface TenantUsageSummary {
  tenant_id: UUID;
  limits: TenantUsageLimits;
  consumption: Record<string, number>;
  monthly_usage?: Array<{
    month: string;
    content_generations: number;
    image_generations: number;
    ocr_pages: number;
  }>;
  brand_usage?: Array<{
    id: UUID;
    name: string;
    allocation_percent: number;
    content_generations: number;
    image_generations: number;
    ocr_pages: number;
    monthly_usage?: Array<{
      month: string;
      content_generations: number;
      image_generations: number;
      ocr_pages: number;
    }>;
  }>;
}

export interface BrandUsageMetricResponse {
  code: string;
  used: number;
  allocated_limit: number;
  percent: number;
}

export interface BrandUsageResponse {
  brand_space_id: UUID;
  tenant_id: UUID;
  capacity_percent: number;
  usage_percent: number;
  metrics: BrandUsageMetricResponse[];
}

export interface BrandResponse {
  id: UUID;
  tenant_id: UUID;
  name: string;
  slug: string;
  tagline?: string | null;
  description: string;
  lifecycle_state: string;
  is_finalized: boolean;
  resolved_brand_context: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AssetProcessingStatusResponse {
  field_key: string;
  lifecycle_state: string;
  processor_name?: string | null;
  progress_current: number;
  progress_total: number;
  status_message?: string | null;
  raw_status_json: Record<string, unknown>;
}

export interface AssetValidationResultResponse {
  field_key: string;
  validation_state: string;
  trust_level?: string | null;
  warnings: string[];
  exclusion_reason?: string | null;
  resolved_payload: Record<string, unknown>;
  confidence?: number | null;
}

export interface AssetCategoryRoutingResponse {
  requested_field_key: string;
  requested_category?: string | null;
  routed_category: string;
  classifier?: string | null;
  confidence?: number | null;
  routing_reason?: string | null;
  decision_json: Record<string, unknown>;
}

export interface ReusableBrandAssetResponse {
  id: UUID;
  knowledge_asset_id: UUID;
  asset_kind: string;
  review_class?: string | null;
  review_status?: string | null;
  review_reason?: string | null;
  label?: string | null;
  mime_type: string;
  storage_path: string;
  asset_url?: string | null;
  width?: number | null;
  height?: number | null;
  confidence?: number | null;
  is_active: boolean;
  source_metadata_json: Record<string, unknown>;
  normalized_metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface BrandAttachmentResponse {
  id: UUID;
  tenant_id: UUID;
  brand_space_id?: UUID | null;
  name: string;
  original_filename: string;
  mime_type: string;
  storage_path: string;
  asset_url?: string | null;
  lifecycle_state: string;
  channel: string;
  field_key?: string | null;
  asset_category?: string | null;
  classification_confidence?: number | null;
  page_count: number;
  is_active: boolean;
  metadata_json: Record<string, unknown>;
  structured_data_json: Record<string, unknown>;
  normalized_data_json: Record<string, unknown>;
  processing_error?: string | null;
  validation_state: string;
  validation_summary_json: Record<string, unknown>;
  processing_status?: AssetProcessingStatusResponse | null;
  validation_result?: AssetValidationResultResponse | null;
  routing?: AssetCategoryRoutingResponse | null;
  reusable_assets: ReusableBrandAssetResponse[];
  created_at: string;
  updated_at: string;
}

export interface BrandAttachmentListResponse {
  field_key: string;
  assets: BrandAttachmentResponse[];
}

export interface DataConflictResponse {
  id: UUID;
  conflict_type: string;
  severity: string;
  field_keys: string[];
  knowledge_asset_ids: string[];
  details_json: Record<string, unknown>;
  resolution_status: string;
  resolved_payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ResolvedBrandContextResponse {
  brand_space_id: UUID;
  snapshot_id?: UUID | null;
  snapshot_kind: string;
  status: string;
  warnings: string[];
  excluded_asset_ids: string[];
  context_json: Record<string, unknown>;
}

export interface ValidationSummaryResponse {
  brand_space_id: UUID;
  warnings: string[];
  conflicts: DataConflictResponse[];
  excluded_assets: string[];
  validation_results: AssetValidationResultResponse[];
  latest_snapshot?: ResolvedBrandContextResponse | null;
}

export interface BrandOverviewResponse {
  brand: BrandResponse;
  sections: Array<{ section_code: string; payload: Record<string, unknown>; version?: number }>;
  personas: Array<Record<string, unknown>>;
  guardrails: Array<Record<string, unknown>>;
  objectives: Array<Record<string, unknown>>;
}

export interface BrandAutofillResponse {
  brand_name?: string;
  brand_tagline?: string;
  brand_description?: string;
  industry_category?: string;
  differentiators?: string;
  core_tone_attributes?: string[];
  primary_emotion?: string;
  secondary_emotion?: string;
  avoided_emotion?: string;
  content_complexity?: string;
  sentence_length?: string;
  perspective?: string;
  selected_audiences?: string[];
  audience_goals?: string;
  audience_motivations?: string;
  audience_fears?: string;
  audience_objections?: string;
  logo_placements?: string[];
  primary_color?: string;
  secondary_color?: string;
  typography?: string;
  brand_mood?: string;
  visual_style?: string;
  selected_rules?: string[];
  positive_word_bank?: string;
  restricted_topics?: string;
  restricted_claims?: string;
  blocked_words_phrases?: string;
  brand_mission?: string;
  brand_vision?: string;
  brand_promise?: string;
  market_positioning?: string;
  sources_used?: number;
  notes?: string[];
}

export interface KnowledgeAssetResponse {
  id: UUID;
  brand_space_id?: UUID;
  name: string;
  original_filename: string;
  mime_type: string;
  storage_path: string;
  asset_url?: string;
  lifecycle_state: string;
  channel: string;
  field_key?: string | null;
  asset_category?: string | null;
  page_count: number;
  metadata_json: Record<string, unknown>;
  structured_data_json: Record<string, unknown>;
  normalized_data_json: Record<string, unknown>;
  validation_state: string;
  validation_summary_json: Record<string, unknown>;
  is_active: boolean;
  processing_error?: string | null;
}

export interface TemplateResponse {
  id: UUID;
  name: string;
  description?: string | null;
  kind: string;
  storage_path: string;
  asset_url?: string | null;
  source_knowledge_asset_id?: UUID | null;
  origin_field_key?: string | null;
  tags: string[];
  analysis_json: Record<string, unknown>;
  matcher_features_json: Record<string, unknown>;
}

export interface TemplateRecommendationResponse {
  template_id: UUID;
  name: string;
  asset_url?: string | null;
  score: number;
  match_type: string;
  decision_confidence?: number | null;
  reasons: string[];
  score_breakdown: Record<string, unknown>;
  adaptation_plan: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export interface TemplateRecommendRequest {
  prompt: string;
  studio_panel: StudioPanelSelection;
  limit?: number;
}

export interface GenerationDecision {
  mode?: string;
  template_id?: UUID | null;
  template_name?: string | null;
  template_preview_asset_url?: string | null;
  template_decision_confidence?: number | null;
  template_recommendations?: TemplateRecommendationResponse[];
  rationale?: string[] | string;
  score_breakdown?: Record<string, unknown>;
  adaptation_plan?: Record<string, unknown>;
  brand_rule_hints?: string[];
  asset_strategy?: Record<string, unknown>;
  review_flags?: string[];
}

export interface StudioPanelSelection {
  format: StudioFormat;
  platform_preset: PlatformPreset;
  file_type: ExportFileType;
  size?: { width: number; height: number };
}

export interface StructuredTextPayload {
  headline: string;
  body: string;
  cta: string;
  hashtags: string[];
  metadata: Record<string, unknown>;
}

export interface AssetReference {
  asset_id: UUID;
  mime_type: string;
  storage_path: string;
  asset_url?: string | null;
  width?: number;
  height?: number;
  asset_role: string;
}

export interface ContentVersionResponse {
  id: UUID;
  session_id: UUID;
  parent_version_id?: UUID;
  lifecycle_state: string;
  content_type: string;
  title?: string;
  prompt: string;
  studio_panel: StudioPanelSelection;
  generated_payload: StructuredTextPayload;
  blueprint_payload: Record<string, unknown>;
  explainability_metadata: Record<string, unknown>;
  generation_decision: GenerationDecision;
  tone_score?: number;
  tone_feedback: Record<string, unknown>;
  assets: AssetReference[];
}

export interface ContentGenerateRequest {
  prompt: string;
  session_id?: UUID;
  persona_id?: UUID;
  objective_id?: UUID;
  template_id?: UUID;
  studio_panel: StudioPanelSelection;
  generate_image: boolean;
  reference_asset_ids: UUID[];
}

export interface ToneEvaluationResponse {
  score: number;
  matched_signals: string[];
  deviations: string[];
  rewrite_suggestions: string[];
}

export interface ChatSessionResponse {
  id: UUID;
  brand_space_id?: UUID;
  title?: string;
  session_kind: string;
  studio_panel: StudioPanelSelection;
  conversational_context: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChatMessageResponse {
  id: UUID;
  session_id: UUID;
  user_id?: UUID;
  content_version_id?: UUID;
  role: "user" | "assistant";
  message_text: string;
  structured_payload: ChatAssistantStructuredPayload | Record<string, unknown>;
  citations: Array<Record<string, unknown>>;
  created_at: string;
}

export interface ChatAssistantStructuredPayload {
  content_version_id?: UUID;
  generated_payload?: StructuredTextPayload;
  blueprint_payload?: Record<string, unknown>;
  tone_feedback?: Record<string, unknown>;
  generation_decision?: GenerationDecision;
  assets?: AssetReference[];
  preview_asset?: AssetReference;
  export_assets?: AssetReference[];
  renderer_metadata?: Record<string, unknown>;
  image_generation_requested?: boolean;
  image_generation_status?: string;
  image_asset_count?: number;
}

export interface ChatSendResponse {
  user_message: ChatMessageResponse;
  assistant_message: ChatMessageResponse;
}

export interface ChatEnhancePromptRequest {
  prompt: string;
  studio_panel?: StudioPanelSelection;
}

export interface ChatEnhancePromptResponse {
  enhanced_prompt: string;
}
export interface ChatSessionCreateRequest {
  title?: string;
  studio_panel: StudioPanelSelection;
}

export interface ChatSessionUpdateRequest {
  title?: string;
  studio_panel?: StudioPanelSelection;
  is_active?: boolean;
}

export interface ChatPipelineRecordRequest {
  prompt: string;
  image_urls: string[];
  assistant_text?: string;
  studio_panel?: StudioPanelSelection;
  title?: string;
}

export interface ChatMessageCreateRequest {
  message: string;
  studio_panel: StudioPanelSelection;
  persona_id?: UUID;
  objective_id?: UUID;
  template_id?: UUID;
  reference_asset_ids?: UUID[];
  generate_image: boolean;
}

export interface ReviewLinkResponse {
  id: UUID;
  token: string;
  status: string;
  allow_external_comments: boolean;
  created_by_name?: string | null;
}

export interface ReviewDetailResponse {
  link: ReviewLinkResponse;
  content?: {
    id: UUID;
    title?: string;
    brand_name?: string | null;
    generated_payload: StructuredTextPayload;
    blueprint_payload: Record<string, unknown>;
    generation_decision?: GenerationDecision;
    assets: AssetReference[];
    display_assets?: AssetReference[];
  };
  comments: Array<{
    id: UUID;
    body: string;
    parent_comment_id?: UUID | null;
    external_author_name?: string;
    author_user_id?: UUID;
    created_at: string;
  }>;
}

export interface ReviewUserSummary {
  id: UUID;
  full_name: string;
  email: string;
  role_codes: string[];
}

export interface ReviewParticipantResponse extends ReviewUserSummary {
  access_role: string;
  is_owner: boolean;
}

export interface ReviewShareAccessResponse {
  owner?: ReviewParticipantResponse | null;
  participants: ReviewParticipantResponse[];
  mentionable_users: ReviewUserSummary[];
}

export interface ReviewShareAccessUpdateRequest {
  user_ids: UUID[];
  user_emails?: string[];
  remove_user_ids?: UUID[];
}

export interface RenderResponse {
  content_version_id: UUID;
  preview_asset?: AssetReference;
  export_assets: AssetReference[];
  renderer_metadata: Record<string, unknown>;
}


export interface ImageEditVariant {
  id: string;
  label: string;
  target: string;
  instructions: string;
  asset: AssetReference;
  preview_style: Record<string, string>;
  created_at: string;
  is_original: boolean;
}

export interface ImageEditStateResponse {
  content_version_id: UUID;
  source_asset_id: UUID;
  variants: ImageEditVariant[];
}

export interface ImageEditStateRequest {
  content_version_id: UUID;
  source_asset: AssetReference;
}

export interface ImageEditApplyRequest extends ImageEditStateRequest {
  target?: string;
  instructions: string;
}
export interface AnalyticsResponse {
  scope: string;
  tenant_id?: UUID;
  brand_space_id?: UUID;
  metrics: Record<string, unknown>;
}

export interface RetrievedChunkResponse {
  chunk_id?: string;
  source: string;
  section: string;
  content_summary?: string;
  relevance_score: number;
  influence_area: string;
  used?: boolean;
  used_in_output?: boolean;
}

export interface BrandContextOutputResponse {
  brand_id: string;
  retrieved_sections: string[];
  high_relevance_context: RetrievedChunkResponse[];
  medium_relevance_context: RetrievedChunkResponse[];
  low_relevance_context: RetrievedChunkResponse[];
  missing_context: string[];
  brand_isolation_status: "pass" | "warning" | "fail";
  retrieval_confidence: number;
  retrieval_query: string;
  total_chunks_retrieved: number;
}

export interface BrandCoreResponse {
  brand_name: string;
  value_proposition: string;
  market_tension: string;
  stands_for: string[];
  stands_against: string[];
  competitive_position: string;
}

export interface CommunicationBehaviorResponse {
  tone_spectrum: string;
  emotional_territory: string;
  boldness_level: "low" | "medium" | "high";
  authority_level: "low" | "medium" | "high";
  simplicity_level: "low" | "medium" | "high";
  preferred_language_behavior: string;
  prohibited_phrases: string[];
}

export interface VisualBehaviorResponse {
  visual_mood: string;
  design_sophistication: "minimal" | "moderate" | "elaborate";
  color_behavior: string;
  image_behavior: string;
  logo_zone_instruction: string;
  typography_behavior: string;
}

export interface AudienceModelResponse {
  primary_persona: string;
  secondary_persona?: string | null;
  core_motivations: string[];
  core_objections: string[];
  emotional_needs: string[];
}

export interface BrandIntelligenceOutputResponse {
  brand_core: BrandCoreResponse;
  communication_behavior: CommunicationBehaviorResponse;
  visual_behavior: VisualBehaviorResponse;
  creative_territory: Record<string, unknown>;
  audience_model: AudienceModelResponse;
  guardrails: string[];
  weak_signals: string[];
  confidence: number;
}

export interface CampaignBriefOutputResponse {
  campaign_objective: string;
  funnel_stage: "awareness" | "consideration" | "conversion" | "retention" | "education";
  audience_intent: string;
  content_role: "educate" | "persuade" | "announce" | "compare" | "inspire" | "convert";
  platform_behavior_constraints: string;
  information_density: "low" | "medium" | "high";
  creative_risk_level: "low" | "medium" | "high";
  persuasion_model: string;
  missing_critical_inputs: string[];
}

export interface RejectedApproachResponse {
  approach_name: string;
  rejection_reason: string;
}

export interface StrategicReasoningOutputResponse {
  strategic_problem: string;
  brand_truth: string;
  recommended_approach: string;
  rejected_approaches: RejectedApproachResponse[];
  attention_strategy: string;
  emotional_strategy: string;
  visual_strategy: string;
  content_pacing_strategy: string;
}

export interface ConceptResponse {
  concept_id: string;
  concept_name: string;
  core_idea: string;
  hook: string;
  narrative_angle: string;
  visual_angle: string;
  brand_fit_reason: string;
  risk_level: "low" | "medium" | "high";
}

export interface RejectedConceptResponse {
  concept_id: string;
  rejection_reason: string;
}

export interface CreativeConceptsOutputResponse {
  all_concepts: ConceptResponse[];
  recommended_concept: ConceptResponse;
  selection_reason: string;
  rejected_concepts: RejectedConceptResponse[];
  diversity_score: number;
}

export interface SlidePlanResponse {
  slide_number: number;
  role: string;
  focus: string;
  copy_intent: string;
  visual_intent: string;
}

export interface FormatPlanOutputResponse {
  format_strategy: string;
  content_structure: string;
  copy_density: "low" | "medium" | "high";
  visual_density: "low" | "medium" | "high";
  layout_archetype: string;
  slide_plan: SlidePlanResponse[];
  notes?: string | null;
}

export interface CopySlideResponse {
  slide_number: number;
  headline: string;
  supporting_line?: string | null;
  body: string;
  cta?: string | null;
}

export interface CopyOutputResponse {
  headline: string;
  supporting_line?: string | null;
  body: string;
  cta: string;
  hashtags: string[];
  slide_copy: CopySlideResponse[];
  claim_safety_notes: string[];
}

export interface BlueprintSlideResponse {
  slide_number: number;
  role: string;
  headline: string;
  body?: string;
  label?: string | null;
  supporting_line?: string | null;
  cta?: string | null;
}

export interface BlueprintInfographicSectionResponse {
  section_label: string;
  stat?: string | null;
  includes?: string[];
  body?: string;
  icon_hint?: string | null;
}

export interface OverlayZoneResponse {
  zone_id: string;
  role: string;
  text: string;
  priority?: number;
  x_rel?: number | null;
  y_rel?: number | null;
  w_rel?: number | null;
  h_rel?: number | null;
  slide_number?: number | null;
}

export interface CreativeBlueprintResponse {
  purpose?: string;
  intent?: string;
  audience?: string;
  platform?: string;
  format?: "static" | "carousel" | "infographic";
  tone?: string;
  hook?: string;
  story_flow?: string[];
  messaging_pillars?: string[];
  cta?: string;
  headline?: string;
  supporting_line?: string | null;
  body?: string;
  labels?: string[];
  hashtags?: string[];
  slides?: BlueprintSlideResponse[];
  title?: string | null;
  sections?: BlueprintInfographicSectionResponse[];
  problem_statement?: string | null;
  solution_statement?: string | null;
  proof_points?: string[];
  stat_highlights?: string[];
  process_steps?: string[];
  customer_quote?: string | null;
  customer_name?: string | null;
  visual_hierarchy?: string[];
  text_density?: string;
  layout_archetype?: string;
  layout_type?: string;
  overlay_zones?: OverlayZoneResponse[];
  brand_alignment_notes?: string[];
  validation_checklist?: string[];
  missing_critical?: string[];
  claim_safety_notes?: string[];
  sources?: { title?: string; url?: string }[];
  source_footer?: string;
}

export interface PipelineApproveRequest {
  run_id: string;
  creative_blueprint?: CreativeBlueprintResponse | null;
}

export interface PipelineRejectRequest {
  run_id: string;
}

export interface PipelineEditImageTextRequest {
  image_url: string;
  headline?: string;
  supporting_line?: string;
  body?: string;
  cta?: string;
}

export interface PipelineEditImageTextResponse {
  image_url: string;
  headline?: string;
  supporting_line?: string;
  body?: string;
  cta?: string;
}

export interface VisualReasoningOutputResponse {
  dominant_visual_system: "generated_image" | "type_led" | "illustration" | "infographic" | "data_visual" | "product_visual";
  visual_style: string;
  composition_logic: string;
  focal_point: string;
  negative_space_plan: string;
  color_behavior: string;
  logo_zone_instruction: string;
  typography_behavior?: string | null;
  image_prompt_direction: string;
  generated_image_url: string;
  generated_image_urls?: string[];
}

export interface SceneElementResponse {
  element_id: string;
  element_type: "background" | "visual" | "copy" | "logo" | "cta" | "decorative";
  content: string;
  position: { x: number; y: number; width: number; height: number };
  style: Record<string, unknown>;
  asset_url?: string | null;
}

export interface SceneGraphOutputResponse {
  platform: string;
  platform_ratio: string;
  canvas_width: number;
  canvas_height: number;
  layers: string[];
  elements: SceneElementResponse[];
  styles: Record<string, unknown>;
  assets: string[];
}

export interface PipelineRunRequest {
  brand_id: string;
  user_prompt: string;
  platform?: "linkedin" | "instagram" | "x" | "twitter";
  format?: "static" | "carousel" | "infographic";
}

export interface FinalOutputResponse {
  platform: string;
  format: string;
  canvas_ratio: string;
  asset_url: string;
  asset_urls: string[];
  slide_count: number;
  render_status: string;
  message: string;
}

export interface PipelineRunResponse {
  run_id?: string;
  status: string;
  brand_id: string;
  user_prompt: string;
  platform: string;
  format: string;
  brand_context?: BrandContextOutputResponse;
  brand_intelligence?: BrandIntelligenceOutputResponse;
  campaign_brief?: CampaignBriefOutputResponse;
  strategic_reasoning?: StrategicReasoningOutputResponse;
  creative_concepts?: CreativeConceptsOutputResponse;
  format_plan?: FormatPlanOutputResponse;
  copy?: CopyOutputResponse;
  creative_blueprint?: CreativeBlueprintResponse;
  visual_reasoning?: VisualReasoningOutputResponse;
  scene_graph?: SceneGraphOutputResponse;
  final_output?: FinalOutputResponse;
  layer_latencies?: Record<string, number>;
  token_usage?: Record<string, { input_tokens: number; output_tokens: number }>;
  error?: string | null;
}

export interface RankedChunkResponse {
  chunk_id?: string;
  source: string;
  section: string;
  content?: string;
  text?: string;
  content_summary?: string;
  influence_area: string;
  pinecone_score?: number;
  campaign_score?: number;
  audience_score?: number;
  compliance_score?: number;
  visual_score?: number;
  signal_scores?: {
    campaign: number;
    audience: number;
    compliance: number;
    visual: number;
  };
  composite_score: number;
  tier: "high" | "medium" | "low";
  used?: boolean;
  used_in_output?: boolean;
}

export interface RetrievalLogResponse {
  brand_id: string;
  namespace: string;
  query: string;
  total_chunks: number;
  chunks: {
    source: string;
    section: string;
    relevance_score: number;
    influence_area: string;
    used: boolean;
  }[];
}

export interface RetrievalPreviewResponse {
  brand_context: BrandContextOutputResponse;
  retrieval_log: RetrievalLogResponse;
  ranked_chunks: RankedChunkResponse[];
}
