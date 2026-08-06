import { apiOrigin } from "@/lib/env";
import type { BrandAttachmentResponse, BrandOverviewResponse } from "@/lib/api/contracts";
import {
  AUDIENCE_OPTIONS,
  BRAND_ARCHETYPE_OPTIONS,
  BRAND_RULE_OPTIONS,
  BUYING_STAGE_OPTIONS,
  COMPLIANCE_LEVEL_OPTIONS,
  CONTENT_COMPLEXITY_OPTIONS,
  CORE_TONE_OPTIONS,
  DIGITAL_ACCESS_OPTIONS,
  EDUCATION_LEVEL_OPTIONS,
  EMPLOYMENT_STATUS_OPTIONS,
  HOUSEHOLD_SIZE_OPTIONS,
  INDUSTRY_OPTIONS,
  INCOME_LEVEL_OPTIONS,
  LANGUAGE_PREFERENCE_OPTIONS,
  LOGO_PLACEMENT_OPTIONS,
  LOCATION_OPTIONS,
  MARKET_MATURITY_OPTIONS,
  PERSPECTIVE_OPTIONS,
  PROFESSIONAL_BACKGROUND_OPTIONS,
  SENTENCE_LENGTH_OPTIONS,
  sanitizeOption,
  sanitizeOptionArray,
} from "@/lib/brand-space-options";
import {
  createPersistedBrandUploadItem,
  emptyBrandFormState,
  normalizeBrandLogoItems,
  type BrandFormState,
} from "@/types/brand-space.types";
import type { UploadedBrandAssets } from "@/lib/brand-space-persistence";

type AttachmentLike = Pick<
  BrandAttachmentResponse,
  | "id"
  | "name"
  | "channel"
  | "asset_url"
  | "storage_path"
  | "lifecycle_state"
  | "asset_category"
  | "metadata_json"
  | "structured_data_json"
  | "normalized_data_json"
> & {
  field_key?: string | null;
};

function splitList(value?: string) {
  return (value || "")
    .split(/[\n,]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function toTextarea(value: unknown) {
  if (Array.isArray(value)) {
    return value
      .map((item) => String(item).trim())
      .filter(Boolean)
      .join("\n");
  }
  return typeof value === "string" ? value : "";
}

function toRecord(value: unknown) {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function resolveAssetUrl(value: unknown) {
  if (typeof value === "string" && value) {
    return value;
  }
  return undefined;
}

function resolveStorageUrl(storagePath?: string) {
  return storagePath ? `${apiOrigin}/storage/${storagePath}` : undefined;
}

function createKnowledgeItemFromDescriptor(
  descriptor: Record<string, unknown> | undefined,
  fallbackName: string,
  fallbackChannel: string,
  fallbackTags?: string[],
) {
  if (!descriptor) {
    return null;
  }
  const uploadedAssetId = typeof descriptor.id === "string" ? descriptor.id : undefined;
  if (!uploadedAssetId) {
    return null;
  }
  const storagePath = typeof descriptor.storage_path === "string" ? descriptor.storage_path : undefined;
  const assetUrl = resolveAssetUrl(descriptor.url) || resolveStorageUrl(storagePath);
  return createPersistedBrandUploadItem({
    id: `existing-${uploadedAssetId}`,
    name: typeof descriptor.name === "string" && descriptor.name ? descriptor.name : fallbackName,
    uploadedAssetId,
    storagePath,
    assetUrl,
    lifecycleState:
      typeof descriptor.lifecycle_state === "string" && descriptor.lifecycle_state
        ? descriptor.lifecycle_state
        : "indexed",
    channel:
      typeof descriptor.channel === "string" && descriptor.channel
        ? descriptor.channel
        : fallbackChannel,
    mimeType: typeof descriptor.mime_type === "string" ? descriptor.mime_type : undefined,
    pageCount: typeof descriptor.page_count === "number" ? descriptor.page_count : undefined,
    processingError: typeof descriptor.processing_error === "string" ? descriptor.processing_error : undefined,
    structuredDataJson: toRecord(descriptor.structured_data_json),
    normalizedDataJson: toRecord(descriptor.normalized_data_json),
    tags: fallbackTags,
    kind: "knowledge",
  });
}

function createKnowledgeItems(
  descriptors: unknown,
  fallbackChannel: string,
  fallbackTags?: string[],
) {
  if (!Array.isArray(descriptors)) {
    return [];
  }
  return descriptors
    .map((descriptor, index) =>
      createKnowledgeItemFromDescriptor(
        toRecord(descriptor),
        `Uploaded file ${index + 1}`,
        fallbackChannel,
        fallbackTags,
      ),
    )
    .filter((item): item is NonNullable<typeof item> => Boolean(item));
}

function createTemplateItems(descriptors: unknown) {
  if (!Array.isArray(descriptors)) {
    return [];
  }
  return descriptors
    .map((descriptor, index) => {
      const record = toRecord(descriptor);
      const uploadedAssetId = typeof record.id === "string" ? record.id : undefined;
      if (!uploadedAssetId) {
        return null;
      }
      const storagePath = typeof record.storage_path === "string" ? record.storage_path : undefined;
      return createPersistedBrandUploadItem({
        id: `template-${uploadedAssetId}`,
        name: typeof record.name === "string" && record.name ? record.name : `Template ${index + 1}`,
        uploadedAssetId,
        storagePath,
        assetUrl: resolveAssetUrl(record.url) || resolveStorageUrl(storagePath),
        lifecycleState:
          typeof toRecord(record.analysis_json).status === "string"
            ? String(toRecord(record.analysis_json).status)
            : "indexed",
        tags: Array.isArray(record.tags) ? record.tags.map((item) => String(item)) : [],
        kind: "template",
        templateKind: typeof record.kind === "string" ? record.kind : "hybrid",
        analysisJson: toRecord(record.analysis_json),
      });
    })
    .filter((item): item is NonNullable<typeof item> => Boolean(item));
}

function createCompetitorBrand(record: Record<string, unknown>) {
  const socialProfiles = toRecord(record.social_profiles);
  return {
    name: String(record.name || record.competitor_brand_name || ""),
    websiteUrl: String(record.website_url || record.website || ""),
    linkedin: String(socialProfiles.linkedin || record.linkedin || ""),
    instagram: String(socialProfiles.instagram || record.instagram || ""),
    x: String(socialProfiles.x || record.x || ""),
  };
}

function createCompetitorBrands(value: unknown) {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => createCompetitorBrand(toRecord(item))).filter((item) =>
    Boolean(item.name || item.websiteUrl || item.linkedin || item.instagram || item.x),
  );
}

function normalizeCompetitorBrands(form: BrandFormState) {
  const competitors = form.additional.competitorBrands?.length
    ? form.additional.competitorBrands
    : [
        {
          name: form.additional.competitorBrandName,
          websiteUrl: form.additional.websiteUrl,
          linkedin: form.additional.linkedin,
          instagram: form.additional.instagram,
          x: form.additional.x,
        },
      ];

  return competitors
    .slice(0, 3)
    .filter((competitor) =>
      Boolean(
        competitor.name ||
          competitor.websiteUrl ||
          competitor.linkedin ||
          competitor.instagram ||
          competitor.x,
      ),
    );
}

function competitorDescriptors(form: BrandFormState) {
  return normalizeCompetitorBrands(form).map((competitor) => ({
    name: competitor.name,
    website_url: competitor.websiteUrl,
    social_profiles: {
      linkedin: competitor.linkedin,
      instagram: competitor.instagram,
      x: competitor.x,
    },
  }));
}

export function mapBrandOverviewToForm(overview: BrandOverviewResponse): BrandFormState {
  const form: BrandFormState = structuredClone(emptyBrandFormState);
  const sectionMap = Object.fromEntries(
    overview.sections.map((section) => [section.section_code, section.payload || {}]),
  ) as Record<string, Record<string, unknown>>;

  const identity = toRecord(sectionMap.identity);
  const foundations = toRecord(sectionMap.foundations);
  const voiceTone = toRecord(sectionMap.voice_tone);
  const personasSection = toRecord(sectionMap.personas);
  const guardrails = toRecord(sectionMap.guardrails);
  const objectives = toRecord(sectionMap.objectives);
  const visualIdentity = toRecord(sectionMap.visual_identity);
  const knowledge = toRecord(sectionMap.knowledge);
  const promptIntelligence = toRecord(sectionMap.prompt_intelligence);

  const primaryPersona =
    Array.isArray(personasSection.personas) && personasSection.personas.length
      ? toRecord(
          personasSection.personas.find((item) => toRecord(item).is_default) || personasSection.personas[0],
        )
      : toRecord(overview.personas.find((item) => Boolean(item.is_default)) || overview.personas[0]);
  const personaPsychographics = toRecord(primaryPersona.psychographics);
  const personaDemographics = toRecord(primaryPersona.demographics);
  const personaContentBehavior = toRecord(primaryPersona.content_behavior);
  const industryContext = toRecord(foundations.industry_context);
  const colorPalette = toRecord(visualIdentity.brand_color_palette);
  const typography = toRecord(visualIdentity.typography);
  const socialProfiles = toRecord(identity.social_profiles);
  const competitorBrands = createCompetitorBrands(
    industryContext.competitor_brands || knowledge.competitor_brands,
  );
  const primaryCompetitor =
    competitorBrands[0] ||
    createCompetitorBrand({
      name: industryContext.competitor_brand_name || knowledge.competitor_brand_name,
      website_url: identity.website_url || knowledge.website,
      social_profiles: {
        linkedin: socialProfiles.linkedin || toRecord(knowledge.social_profiles).linkedin,
        instagram: socialProfiles.instagram || toRecord(knowledge.social_profiles).instagram,
        x: socialProfiles.x || toRecord(knowledge.social_profiles).x,
      },
    });

  form.core = {
    logo: null,
    logos: [],
    name: String(identity.brand_name || overview.brand.name || ""),
    description: String(identity.brand_description || overview.brand.description || ""),
    industryCategory: String(identity.industry_category || ""),
    differentiators: toTextarea(identity.key_differentiators),
  };

  const primaryLogo =
    createKnowledgeItemFromDescriptor(
        {
          id: identity.logo_asset_id,
          name: `${overview.brand.name} Logo`,
          storage_path: identity.logo_asset_path,
          url: identity.logo_asset_url,
          lifecycle_state: "indexed",
          channel: "brand_asset",
        },
        `${overview.brand.name} Logo`,
        "brand_asset",
        ["Logo"],
      ) || null;
  const uploadedLogos = createKnowledgeItems(identity.logo_assets, "brand_asset", ["Logo"]);
  form.core.logos = normalizeBrandLogoItems(uploadedLogos.length ? uploadedLogos : primaryLogo ? [primaryLogo] : []);
  form.core.logo = form.core.logos[0] || primaryLogo;

  form.voiceTone = {
    coreToneAttributes: Array.isArray(voiceTone.tone_attributes)
      ? voiceTone.tone_attributes.map((item) => String(item))
      : [],
    coreToneAttributeWeights: Object.fromEntries(
      Object.entries(toRecord(voiceTone.tone_intensity)).map(([key, value]) => {
        const numericValue = Number(value);
        const percentage = Number.isFinite(numericValue)
          ? numericValue <= 10
            ? numericValue * 10
            : numericValue
          : 50;
        return [key, Math.max(0, Math.min(100, percentage))];
      }),
    ),
    primaryEmotion: String(voiceTone.primary_emotion || ""),
    secondaryEmotion: String(voiceTone.secondary_emotion || ""),
    avoidedEmotion: String(voiceTone.avoided_emotion || ""),
    contentComplexity: String(voiceTone.content_complexity || ""),
    sentenceLength: String(voiceTone.sentence_length || ""),
    perspective: String(voiceTone.perspective || ""),
  };

  form.targetAudience = {
    selectedAudiences: Array.isArray(personaContentBehavior.selected_audiences)
      ? personaContentBehavior.selected_audiences.map((item) => String(item))
      : Array.isArray(identity.audience_type)
        ? identity.audience_type.map((item) => String(item))
        : identity.audience_type
          ? [String(identity.audience_type)]
          : [],
    goals: toTextarea(primaryPersona.audience_goals || personaPsychographics.goals),
    motivations: toTextarea(primaryPersona.motivations || personaPsychographics.motivations),
    fearsAndPainPoints: toTextarea(primaryPersona.fears_and_pain_points || personaPsychographics.fears_and_pain_points),
    objections: toTextarea(primaryPersona.objections),
    contentConsumptionBehavior: toTextarea(
      personaPsychographics.content_consumption_behavior || personaContentBehavior.preferred_channels,
    ),
    audienceInsights: createKnowledgeItems(personaContentBehavior.audience_insights, "audience_insights"),
    audienceType: String(primaryPersona.audience_type || identity.audience_type || ""),
    ageRange: String(personaDemographics.age_range || ""),
    gender: String(personaDemographics.gender || ""),
    location: String(personaDemographics.region || toRecord(identity.target_geography).country || ""),
    educationLevel: String(personaDemographics.education_level || ""),
    employmentStatus: String(personaDemographics.employment_status || ""),
    professionalBackground: String(personaDemographics.professional_background || ""),
    householdSize: String(personaDemographics.household_size || ""),
    languagePreference: String(primaryPersona.language_preference || personaDemographics.language_preference || ""),
    incomeLevel: String(personaDemographics.income_level || ""),
    familyStatusOrLifeStage: String(personaDemographics.family_status_or_life_stage || ""),
    socioEconomicSegment: String(personaDemographics.socio_economic_segment || ""),
    digitalAccess: String(personaDemographics.digital_access || ""),
  };

  const colorPaletteUploads = createKnowledgeItems(visualIdentity.color_palette_uploads, "visual_identity", ["Color Palette"]);
  const activeColorPaletteAssetId = String(visualIdentity.active_color_palette_asset_id || "");
  const activeColorPaletteUploadId = colorPaletteUploads.find(
    (item) => item.uploadedAssetId === activeColorPaletteAssetId,
  )?.id || "";

  form.visualIdentity = {
    brandMood: String(visualIdentity.brand_mood || ""),
    visualStyle: String(visualIdentity.visual_style || ""),
    logoPlacements: Array.isArray(visualIdentity.logo_placements)
      ? visualIdentity.logo_placements.slice(0, 1).map((item) => String(item))
      : visualIdentity.logo_placement
        ? [String(visualIdentity.logo_placement)]
        : [],
    referenceCreatives: createKnowledgeItems(visualIdentity.reference_creatives, "reference_creative"),
    moodBoards: createKnowledgeItems(visualIdentity.mood_boards, "mood_board", ["Mood Board"]),
    primaryColor: String(colorPalette.primary || ""),
    secondaryColor: String(colorPalette.secondary || ""),
    additionalColors:
      Array.isArray(colorPalette.additional) && colorPalette.additional.length
        ? colorPalette.additional.map((item) => ({
            name: String(toRecord(item).name || ""),
            hex: String(toRecord(item).hex || ""),
          }))
        : [{ name: "", hex: "" }],
    colorPaletteUploads,
    activeColorPaletteUploadId,
    typography: String(typography.primary_style || ""),
    uploadedFonts: [],
    fontStyleGuide: createKnowledgeItems(visualIdentity.font_style_guides, "visual_identity", ["Font Guide"]),
  };

  form.brandRules = {
    selectedRules: Array.isArray(guardrails.custom_rules) ? guardrails.custom_rules.map((item) => String(item)) : [],
    positiveWordBank: toTextarea(guardrails.positive_word_bank),
    positiveWordBankUploads: createKnowledgeItems(toRecord(guardrails.word_bank_assets).positive, "guardrail_support", ["Positive Word Bank"]),
    replaceableWords: toTextarea(guardrails.replaceable_words),
    replaceableWordUploads: createKnowledgeItems(toRecord(guardrails.word_bank_assets).replaceable, "guardrail_support", ["Replaceable Words"]),
    negativeWordBank: toTextarea(guardrails.negative_word_bank),
    negativeWordBankUploads: createKnowledgeItems(toRecord(guardrails.word_bank_assets).negative, "guardrail_support", ["Negative Word Bank"]),
    whatToDo: toTextarea(guardrails.dos),
    whatNotToDo: toTextarea(guardrails.donts),
    restrictedTopics: toTextarea(guardrails.restricted_topics),
    restrictedClaims: toTextarea(guardrails.restricted_claims),
    blockedWordsPhrases: toTextarea(guardrails.blocked_words),
  };

  form.brandKnowledge = {
    templateFiles: createTemplateItems(knowledge.template_files || toRecord(promptIntelligence.platform_rules).recommended_templates),
    otherDocuments: createKnowledgeItems(knowledge.other_documents, "brand"),
  };

  // Prompt intelligence section
  const platformRulesRaw = toRecord(promptIntelligence.platform_rules);
  const promptStarters = Array.isArray(promptIntelligence.prompt_starters)
    ? (promptIntelligence.prompt_starters as Array<Record<string, unknown>>)
    : [];
  const supportedPlatforms = Array.isArray(platformRulesRaw.supported_platforms)
    ? (platformRulesRaw.supported_platforms as unknown[]).map((p) => String(p))
    : [];

  form.promptIntelligence = {
    preferredPlatforms: supportedPlatforms,
    contentFormats: [],
    instructionOverrides: String(promptIntelligence.instruction_overrides || ""),
    contentTone: String(promptIntelligence.content_tone_override || ""),
    contextualHints: String(promptIntelligence.contextual_hints || ""),
    platformRules: String(promptIntelligence.platform_specific_rules || ""),
    avoidedFormats: String(promptIntelligence.avoided_formats || ""),
  };

  const defaultObjective =
    Array.isArray(objectives.objectives) && objectives.objectives.length
      ? toRecord(
          objectives.objectives.find((item) => toRecord(item).is_default) || objectives.objectives[0],
        )
      : toRecord(overview.objectives.find((item) => Boolean(item.is_default)) || overview.objectives[0]);
  const objectiveConfig = toRecord(defaultObjective.configuration);

  form.additional = {
    brandMission: String(foundations.brand_mission || ""),
    brandVision: String(foundations.brand_vision || ""),
    brandPromise: String(foundations.brand_promise || ""),
    marketPositioning: String(foundations.market_positioning || ""),
    roleOfDigitalPlatforms: String(foundations.role_of_digital_platforms || ""),
    socialMediaChallenges: toTextarea(foundations.social_media_challenges),
    businessProblemOrOpportunity: String(foundations.business_problem_or_opportunity || objectiveConfig.business_problem_or_opportunity || ""),
    perceptionChallenge: String(foundations.perception_challenge || objectiveConfig.perception_challenge || ""),
    humanInsight: String(foundations.human_insight || objectiveConfig.human_insight || ""),
    brandAdvantage: String(foundations.brand_advantage || defaultObjective.name || ""),
    strategy: String(industryContext.strategy || defaultObjective.description || ""),
    marketMaturity: String(industryContext.market_maturity || objectiveConfig.market_maturity || ""),
    brandArchetype: String(industryContext.brand_archetype || objectiveConfig.brand_archetype || ""),
    buyingStage: String(industryContext.buying_stage || objectiveConfig.buying_stage || ""),
    complianceLevel: String(industryContext.compliance_level || objectiveConfig.compliance_level || ""),
    competitorBrandName: primaryCompetitor.name,
    websiteUrl: primaryCompetitor.websiteUrl,
    linkedin: primaryCompetitor.linkedin,
    instagram: primaryCompetitor.instagram,
    x: primaryCompetitor.x,
    competitorBrands: competitorBrands.length ? competitorBrands : [primaryCompetitor],
  };

  form.objectives = {
    primaryObjective: String(defaultObjective.content_type || objectiveConfig.primary_objective || ""),
    contentGoal: String(objectiveConfig.content_goal || ""),
    campaignTheme: String(defaultObjective.description || objectiveConfig.campaign_theme || ""),
    businessOutcome: String(objectiveConfig.business_problem_or_opportunity || form.additional.businessProblemOrOpportunity || ""),
    callToAction: String(objectiveConfig.call_to_action || ""),
    targetConversionAction: String(objectiveConfig.target_conversion_action || ""),
    contentFrequency: String(objectiveConfig.content_frequency || ""),
    successMetric: String(objectiveConfig.success_metric || ""),
  };

  return form;
}

function assetIds(items: Array<{ id: string }>) {
  return items.map((item) => item.id);
}

function assetDescriptors(items: AttachmentLike[]) {
  return items.map((item) => ({
    id: item.id,
    name: item.name,
    channel: item.channel,
    url: item.asset_url,
    storage_path: item.storage_path,
    lifecycle_state: item.lifecycle_state,
    asset_category: item.asset_category,
    field_key: item.field_key || undefined,
    structured_data_json: item.structured_data_json || {},
    normalized_data_json: item.normalized_data_json || {},
  }));
}

function templateDescriptors(items: AttachmentLike[]) {
  return items.map((item) => ({
    id: item.id,
    name: item.name,
    kind:
      typeof item.normalized_data_json?.template_kind === "string"
        ? String(item.normalized_data_json.template_kind)
        : item.asset_category === "template"
          ? "hybrid"
          : "hybrid",
    tags: Array.isArray(item.metadata_json?.tags) ? item.metadata_json.tags.map((tag) => String(tag)) : [],
    url: item.asset_url,
    storage_path: item.storage_path,
    lifecycle_state: item.lifecycle_state,
  }));
}

function toneIntensity(attributes: string[], weights: Record<string, number> = {}) {
  return Object.fromEntries(
    attributes.map((attribute) => {
      const value = Number(weights[attribute] ?? 50);
      return [attribute, Math.max(0, Math.min(100, Number.isFinite(value) ? value : 50))];
    }),
  );
}

function normalizeBrandSelections(form: BrandFormState) {
  return {
    industryCategory: sanitizeOption(INDUSTRY_OPTIONS, form.core.industryCategory),
    coreToneAttributes: sanitizeOptionArray(CORE_TONE_OPTIONS, form.voiceTone.coreToneAttributes),
    contentComplexity: sanitizeOption(CONTENT_COMPLEXITY_OPTIONS, form.voiceTone.contentComplexity),
    sentenceLength: sanitizeOption(SENTENCE_LENGTH_OPTIONS, form.voiceTone.sentenceLength),
    perspective: sanitizeOption(PERSPECTIVE_OPTIONS, form.voiceTone.perspective),
    selectedAudiences: sanitizeOptionArray(AUDIENCE_OPTIONS, form.targetAudience.selectedAudiences),
    logoPlacements: sanitizeOptionArray(
      LOGO_PLACEMENT_OPTIONS,
      form.visualIdentity.logoPlacements,
    ).slice(0, 1),
    location: sanitizeOption(LOCATION_OPTIONS, form.targetAudience.location),
    educationLevel: sanitizeOption(EDUCATION_LEVEL_OPTIONS, form.targetAudience.educationLevel),
    employmentStatus: sanitizeOption(EMPLOYMENT_STATUS_OPTIONS, form.targetAudience.employmentStatus),
    professionalBackground: sanitizeOption(
      PROFESSIONAL_BACKGROUND_OPTIONS,
      form.targetAudience.professionalBackground,
    ),
    householdSize: sanitizeOption(HOUSEHOLD_SIZE_OPTIONS, form.targetAudience.householdSize),
    languagePreference: sanitizeOption(
      LANGUAGE_PREFERENCE_OPTIONS,
      form.targetAudience.languagePreference,
    ),
    incomeLevel: sanitizeOption(INCOME_LEVEL_OPTIONS, form.targetAudience.incomeLevel),
    digitalAccess: sanitizeOption(DIGITAL_ACCESS_OPTIONS, form.targetAudience.digitalAccess),
    selectedRules: sanitizeOptionArray(BRAND_RULE_OPTIONS, form.brandRules.selectedRules),
    marketMaturity: sanitizeOption(MARKET_MATURITY_OPTIONS, form.additional.marketMaturity),
    brandArchetype: sanitizeOption(BRAND_ARCHETYPE_OPTIONS, form.additional.brandArchetype),
    buyingStage: sanitizeOption(BUYING_STAGE_OPTIONS, form.additional.buyingStage),
    complianceLevel: sanitizeOption(COMPLIANCE_LEVEL_OPTIONS, form.additional.complianceLevel),
  };
}

export function mapBrandFormToCreateRequest(form: BrandFormState, uploads?: UploadedBrandAssets) {
  const normalized = normalizeBrandSelections(form);
  const logoAssets = uploads?.logos?.length ? uploads.logos : uploads?.logo ? [uploads.logo] : [];
  const competitors = normalizeCompetitorBrands(form);
  const primaryCompetitor = competitors[0];

  return {
    identity: {
      brand_name: form.core.name || "",
      brand_description: form.core.description || "",
      industry_category: normalized.industryCategory || undefined,
      target_geography: {
        country: normalized.location || "",
      },
      audience_type: normalized.selectedAudiences[0] || undefined,
      key_differentiators: splitList(form.core.differentiators),
      logo_asset_id: logoAssets[0]?.id,
      logo_asset_ids: assetIds(logoAssets),
      website_url: primaryCompetitor?.websiteUrl || form.additional.websiteUrl || undefined,
      social_profiles: {
        linkedin: primaryCompetitor?.linkedin || form.additional.linkedin || undefined,
        instagram: primaryCompetitor?.instagram || form.additional.instagram || undefined,
        x: primaryCompetitor?.x || form.additional.x || undefined,
      },
    },
    foundations: {
      brand_mission: form.additional.brandMission || undefined,
      brand_vision: form.additional.brandVision || undefined,
      brand_promise: form.additional.brandPromise || undefined,
    },
    voice_tone: {
      tone_attributes: normalized.coreToneAttributes,
      tone_intensity: toneIntensity(normalized.coreToneAttributes, form.voiceTone.coreToneAttributeWeights),
      primary_emotion: form.voiceTone.primaryEmotion || "confident",
      secondary_emotion: form.voiceTone.secondaryEmotion || undefined,
      avoided_emotion: form.voiceTone.avoidedEmotion || undefined,
      content_complexity: normalized.contentComplexity || undefined,
      sentence_length: normalized.sentenceLength || undefined,
      perspective: normalized.perspective || undefined,
    },
  };
}

export function mapBrandSections(form: BrandFormState, uploads?: UploadedBrandAssets) {
  const uploaded = uploads;
  const normalized = normalizeBrandSelections(form);
  const logoAssets = uploaded?.logos?.length ? uploaded.logos : uploaded?.logo ? [uploaded.logo] : [];
  const competitors = normalizeCompetitorBrands(form);
  const primaryCompetitor = competitors[0];
  const competitorPayloads = competitorDescriptors(form);
  const logoPlacements = [...(normalized.logoPlacements || [])];
  const defaultLogoPlacement = logoPlacements[0] || "top_right";

  return [
    {
      section_code: "identity",
      payload: {
        brand_name: form.core.name || "",
        brand_description: form.core.description || "",
        industry_category: normalized.industryCategory || "",
        key_differentiators: splitList(form.core.differentiators),
        logo_asset_id: logoAssets[0]?.id || null,
        logo_asset_ids: assetIds(logoAssets),
        logo_asset_path: logoAssets[0]?.storage_path || null,
        logo_asset_url: logoAssets[0]?.asset_url || null,
        logo_assets: assetDescriptors(logoAssets),
        website_url: primaryCompetitor?.websiteUrl || form.additional.websiteUrl || "",
        social_profiles: {
          linkedin: primaryCompetitor?.linkedin || form.additional.linkedin || "",
          instagram: primaryCompetitor?.instagram || form.additional.instagram || "",
          x: primaryCompetitor?.x || form.additional.x || "",
        },
        audience_type: normalized.selectedAudiences[0] || "",
        target_geography: {
          country: normalized.location || "",
        },
      },
      completion_percent: 100,
    },
    {
      section_code: "foundations",
      payload: {
        brand_mission: form.additional.brandMission || "",
        brand_vision: form.additional.brandVision || "",
        brand_promise: form.additional.brandPromise || "",
        market_positioning: form.additional.marketPositioning || "",
        role_of_digital_platforms: form.additional.roleOfDigitalPlatforms || "",
        social_media_challenges: splitList(form.additional.socialMediaChallenges),
        business_problem_or_opportunity: form.additional.businessProblemOrOpportunity || "",
        perception_challenge: form.additional.perceptionChallenge || "",
        human_insight: form.additional.humanInsight || "",
        brand_advantage: form.additional.brandAdvantage || "",
        industry_context: {
          strategy: form.additional.strategy || "",
          market_maturity: normalized.marketMaturity || "",
          brand_archetype: normalized.brandArchetype || "",
          buying_stage: normalized.buyingStage || "",
          compliance_level: normalized.complianceLevel || "",
          competitor_brand_name: primaryCompetitor?.name || form.additional.competitorBrandName || "",
          competitor_brands: competitorPayloads,
        },
      },
      completion_percent: 100,
    },
    {
      section_code: "voice_tone",
      payload: {
        tone_attributes: normalized.coreToneAttributes,
        tone_intensity: toneIntensity(normalized.coreToneAttributes, form.voiceTone.coreToneAttributeWeights),
        primary_emotion: form.voiceTone.primaryEmotion || "",
        secondary_emotion: form.voiceTone.secondaryEmotion || "",
        avoided_emotion: form.voiceTone.avoidedEmotion || "",
        content_complexity: normalized.contentComplexity || "",
        sentence_length: normalized.sentenceLength || "",
        perspective: normalized.perspective || "",
      },
      completion_percent: 100,
    },
    {
      section_code: "personas",
      payload: {
        personas: [
          {
            name: normalized.selectedAudiences[0] || "Primary Audience",
            role: "Primary buyer persona",
            psychographics: {
              goals: splitList(form.targetAudience.goals),
              motivations: splitList(form.targetAudience.motivations),
              fears_and_pain_points: splitList(form.targetAudience.fearsAndPainPoints),
              objections: splitList(form.targetAudience.objections),
              content_consumption_behavior: splitList(form.targetAudience.contentConsumptionBehavior),
            },
            demographics: {
              age_range: form.targetAudience.ageRange || "",
              gender: form.targetAudience.gender || "",
              region: normalized.location || "",
              education_level: normalized.educationLevel || "",
              employment_status: normalized.employmentStatus || "",
              professional_background: normalized.professionalBackground || "",
              household_size: normalized.householdSize || "",
              language_preference: normalized.languagePreference || "",
              income_level: normalized.incomeLevel || "",
              family_status_or_life_stage: form.targetAudience.familyStatusOrLifeStage || "",
              socio_economic_segment: form.targetAudience.socioEconomicSegment || "",
              digital_access: normalized.digitalAccess || "",
            },
            audience_goals: splitList(form.targetAudience.goals),
            motivations: splitList(form.targetAudience.motivations),
            fears_and_pain_points: splitList(form.targetAudience.fearsAndPainPoints),
            objections: splitList(form.targetAudience.objections),
            content_behavior: {
              preferred_channels: splitList(form.targetAudience.contentConsumptionBehavior),
              selected_audiences: normalized.selectedAudiences,
              audience_insight_asset_ids: assetIds(uploaded?.audienceInsights || []),
              audience_insights: assetDescriptors(uploaded?.audienceInsights || []),
            },
            language_preference: normalized.languagePreference || "",
            is_default: true,
          },
        ],
      },
      completion_percent: 100,
    },
    {
      section_code: "guardrails",
      payload: {
        dos: splitList(form.brandRules.whatToDo),
        donts: splitList(form.brandRules.whatNotToDo),
        restricted_claims: splitList(form.brandRules.restrictedClaims),
        restricted_topics: splitList(form.brandRules.restrictedTopics),
        blocked_words: splitList(form.brandRules.blockedWordsPhrases),
        positive_word_bank: splitList(form.brandRules.positiveWordBank),
        replaceable_words: splitList(form.brandRules.replaceableWords),
        negative_word_bank: splitList(form.brandRules.negativeWordBank),
        custom_rules: normalized.selectedRules,
        positive_word_bank_asset_ids: assetIds(uploaded?.positiveWordBankUploads || []),
        replaceable_word_asset_ids: assetIds(uploaded?.replaceableWordUploads || []),
        negative_word_bank_asset_ids: assetIds(uploaded?.negativeWordBankUploads || []),
        word_bank_assets: {
          positive: assetDescriptors(uploaded?.positiveWordBankUploads || []),
          replaceable: assetDescriptors(uploaded?.replaceableWordUploads || []),
          negative: assetDescriptors(uploaded?.negativeWordBankUploads || []),
        },
      },
      completion_percent: 100,
    },
    {
      section_code: "objectives",
      payload: {
        objectives: [
          {
            name: form.objectives.campaignTheme || form.additional.brandAdvantage || form.additional.brandMission || "Brand Growth",
            description: form.objectives.businessOutcome || form.additional.strategy || form.additional.marketPositioning || "",
            content_type: form.objectives.primaryObjective || "social_post",
            platform_scope: "multiplatform",
            is_default: true,
            configuration: {
              primary_objective: form.objectives.primaryObjective || "",
              content_goal: form.objectives.contentGoal || "",
              campaign_theme: form.objectives.campaignTheme || "",
              call_to_action: form.objectives.callToAction || "",
              target_conversion_action: form.objectives.targetConversionAction || "",
              content_frequency: form.objectives.contentFrequency || "",
              success_metric: form.objectives.successMetric || "",
              business_problem_or_opportunity: form.objectives.businessOutcome || form.additional.businessProblemOrOpportunity || "",
              perception_challenge: form.additional.perceptionChallenge || "",
              human_insight: form.additional.humanInsight || "",
              market_positioning: form.additional.marketPositioning || "",
              role_of_digital_platforms: form.additional.roleOfDigitalPlatforms || "",
              social_media_challenges: splitList(form.additional.socialMediaChallenges),
              market_maturity: normalized.marketMaturity || "",
              brand_archetype: normalized.brandArchetype || "",
              buying_stage: normalized.buyingStage || "",
              compliance_level: normalized.complianceLevel || "",
            },
          },
        ],
      },
      completion_percent: 100,
    },
    {
      section_code: "visual_identity",
      payload: {
        brand_mood: form.visualIdentity.brandMood || "",
        visual_style: form.visualIdentity.visualStyle || "",
        logo_placements: logoPlacements,
        logo_placement: {
          allowed_positions: logoPlacements.length ? logoPlacements : [defaultLogoPlacement],
          default_position: defaultLogoPlacement,
        },
        brand_color_palette: {
          primary: form.visualIdentity.primaryColor || "",
          secondary: form.visualIdentity.secondaryColor || "",
          additional: form.visualIdentity.additionalColors
            .filter((color) => color.name || color.hex)
            .map((color) => ({ name: color.name, hex: color.hex })),
        },
        typography: {
          primary_style: form.visualIdentity.typography || "",
        },
        reference_creative_asset_ids: assetIds(uploaded?.referenceCreatives || []),
        mood_board_asset_ids: assetIds(uploaded?.moodBoards || []),
        reference_creatives: assetDescriptors(uploaded?.referenceCreatives || []),
        mood_boards: assetDescriptors(uploaded?.moodBoards || []),
        color_palette_asset_ids: assetIds(uploaded?.colorPaletteUploads || []),
        color_palette_uploads: assetDescriptors(uploaded?.colorPaletteUploads || []),
        active_color_palette_asset_id:
          form.visualIdentity.colorPaletteUploads.find(
            (item) => item.id === form.visualIdentity.activeColorPaletteUploadId,
          )?.uploadedAssetId || "",
        font_style_guide_asset_ids: assetIds(uploaded?.fontStyleGuide || []),
        font_style_guides: assetDescriptors(uploaded?.fontStyleGuide || []),
      },
      completion_percent: 100,
    },
    {
      section_code: "prompt_intelligence",
      payload: {
        prompt_starters: [
          { label: "Audience", value: normalized.selectedAudiences.join(", ") },
          { label: "Strategy", value: form.additional.strategy || "" },
          { label: "Brand mood", value: form.visualIdentity.brandMood || "" },
          { label: "Brand voice", value: normalized.coreToneAttributes.join(", ") },
        ].filter((item) => item.value),
        platform_rules: {
          supported_platforms: form.promptIntelligence.preferredPlatforms.length
            ? form.promptIntelligence.preferredPlatforms
            : ["linkedin", "instagram", "x", "youtube_thumbnail"],
          recommended_templates: templateDescriptors(uploaded?.templateFiles || []),
        },
        instruction_overrides: form.promptIntelligence.instructionOverrides || "",
        content_tone_override: form.promptIntelligence.contentTone || "",
        contextual_hints: form.promptIntelligence.contextualHints || "",
        platform_specific_rules: form.promptIntelligence.platformRules || "",
        avoided_formats: form.promptIntelligence.avoidedFormats || "",
        preferred_content_formats: form.promptIntelligence.contentFormats,
      },
      completion_percent: 100,
    },
    {
      section_code: "knowledge",
      payload: {
        template_ids: (uploaded?.templateFiles || []).map((item) => item.id),
        template_files: templateDescriptors(uploaded?.templateFiles || []),
        other_document_asset_ids: assetIds(uploaded?.otherDocuments || []),
        other_documents: assetDescriptors(uploaded?.otherDocuments || []),
        audience_insight_asset_ids: assetIds(uploaded?.audienceInsights || []),
        website: primaryCompetitor?.websiteUrl || form.additional.websiteUrl || "",
        competitor_brand_name: primaryCompetitor?.name || form.additional.competitorBrandName || "",
        competitor_brands: competitorPayloads,
        social_profiles: {
          linkedin: primaryCompetitor?.linkedin || form.additional.linkedin || "",
          instagram: primaryCompetitor?.instagram || form.additional.instagram || "",
          x: primaryCompetitor?.x || form.additional.x || "",
        },
      },
      completion_percent: 100,
    },
  ];
}
