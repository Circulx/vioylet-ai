import type { BrandAutofillResponse } from "@/lib/api/contracts";
import type { BrandFormState } from "@/types/brand-space.types";

function pickText(current: string, next?: string | null) {
  const value = (next || "").trim();
  if (!value) return current;
  // Prefer filling empty fields; overwrite thin placeholders
  if (!current.trim() || current.trim().length < 3) return value;
  return current;
}

function pickList(current: string[], next?: string[] | null) {
  if (!next?.length) return current;
  if (!current.length) return [...next];
  return current;
}

/** Merge vector-DB autofill suggestions into the Brand Space form (empty-first). */
export function applyBrandAutofillToForm(
  form: BrandFormState,
  suggestion: BrandAutofillResponse,
): BrandFormState {
  const toneAttrs = pickList(form.voiceTone.coreToneAttributes, suggestion.core_tone_attributes);
  const weights = { ...form.voiceTone.coreToneAttributeWeights };
  for (const attr of toneAttrs) {
    if (weights[attr] == null) weights[attr] = 70;
  }

  return {
    ...form,
    core: {
      ...form.core,
      name: pickText(form.core.name, suggestion.brand_name),
      tagline: pickText(form.core.tagline, suggestion.brand_tagline),
      description: pickText(form.core.description, suggestion.brand_description),
      industryCategory: pickText(form.core.industryCategory, suggestion.industry_category),
      differentiators: pickText(form.core.differentiators, suggestion.differentiators),
    },
    voiceTone: {
      ...form.voiceTone,
      coreToneAttributes: toneAttrs,
      coreToneAttributeWeights: weights,
      primaryEmotion: pickText(form.voiceTone.primaryEmotion, suggestion.primary_emotion),
      secondaryEmotion: pickText(form.voiceTone.secondaryEmotion, suggestion.secondary_emotion),
      avoidedEmotion: pickText(form.voiceTone.avoidedEmotion, suggestion.avoided_emotion),
      contentComplexity: pickText(form.voiceTone.contentComplexity, suggestion.content_complexity),
      sentenceLength: pickText(form.voiceTone.sentenceLength, suggestion.sentence_length),
      perspective: pickText(form.voiceTone.perspective, suggestion.perspective),
    },
    targetAudience: {
      ...form.targetAudience,
      selectedAudiences: pickList(
        form.targetAudience.selectedAudiences,
        suggestion.selected_audiences,
      ),
      goals: pickText(form.targetAudience.goals, suggestion.audience_goals),
      motivations: pickText(form.targetAudience.motivations, suggestion.audience_motivations),
      fearsAndPainPoints: pickText(form.targetAudience.fearsAndPainPoints, suggestion.audience_fears),
      objections: pickText(form.targetAudience.objections, suggestion.audience_objections),
    },
    visualIdentity: {
      ...form.visualIdentity,
      logoPlacements: pickList(form.visualIdentity.logoPlacements, suggestion.logo_placements),
      primaryColor: pickText(form.visualIdentity.primaryColor, suggestion.primary_color),
      secondaryColor: pickText(form.visualIdentity.secondaryColor, suggestion.secondary_color),
      typography: pickText(form.visualIdentity.typography, suggestion.typography),
      brandMood: pickText(form.visualIdentity.brandMood, suggestion.brand_mood),
      visualStyle: pickText(form.visualIdentity.visualStyle, suggestion.visual_style),
    },
    brandRules: {
      ...form.brandRules,
      selectedRules: pickList(form.brandRules.selectedRules, suggestion.selected_rules),
      positiveWordBank: pickText(form.brandRules.positiveWordBank, suggestion.positive_word_bank),
      restrictedTopics: pickText(form.brandRules.restrictedTopics, suggestion.restricted_topics),
      restrictedClaims: pickText(form.brandRules.restrictedClaims, suggestion.restricted_claims),
      blockedWordsPhrases: pickText(
        form.brandRules.blockedWordsPhrases,
        suggestion.blocked_words_phrases,
      ),
    },
    additional: {
      ...form.additional,
      brandMission: pickText(form.additional.brandMission, suggestion.brand_mission),
      brandVision: pickText(form.additional.brandVision, suggestion.brand_vision),
      brandPromise: pickText(form.additional.brandPromise, suggestion.brand_promise),
      marketPositioning: pickText(form.additional.marketPositioning, suggestion.market_positioning),
    },
  };
}
