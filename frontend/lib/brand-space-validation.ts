import type { BrandFormState } from "@/types/brand-space.types";

export type MissingBrandField = {
  label: string;
  tab: string;
};

export type BrandTabCompletion = {
  completed: number;
  percent: number;
  required: number;
};

function hasText(value: string | null | undefined) {
  return Boolean(value?.trim());
}

function hasUpload(items: Array<unknown> | null | undefined) {
  return Boolean(items?.length);
}

export function getMissingRequiredBrandFields(form: BrandFormState): MissingBrandField[] {
  return getRequiredBrandFieldChecks(form)
    .filter((field) => !field.complete)
    .map(({ tab, label }) => ({ tab, label }));
}

function getRequiredBrandFieldChecks(form: BrandFormState) {
  const checks: Array<MissingBrandField & { complete: boolean }> = [];

  const requireText = (tab: string, label: string, value: string | null | undefined) => {
    checks.push({ tab, label, complete: hasText(value) });
  };

  const requireList = (tab: string, label: string, values: Array<unknown> | null | undefined) => {
    checks.push({ tab, label, complete: Boolean(values?.length) });
  };

  checks.push({
    tab: "core_brand_signals",
    label: "Upload Brand Logo",
    complete: hasUpload(form.core.logos.length ? form.core.logos : form.core.logo ? [form.core.logo] : []),
  });
  requireText("core_brand_signals", "Brand Name", form.core.name);
  requireText("core_brand_signals", "Brand Description", form.core.description);
  requireText("core_brand_signals", "Industry Category", form.core.industryCategory);

  requireList("voice_tone", "Core Tone Attributes", form.voiceTone.coreToneAttributes);

  requireList("target_audience", "Select Target Audience", form.targetAudience.selectedAudiences);

  requireList("visual_identity", "Logo Placement", form.visualIdentity.logoPlacements);
  checks.push({
    tab: "visual_identity",
    label: "Brand Color Palette (HEX)",
    complete: hasText(form.visualIdentity.primaryColor) && hasText(form.visualIdentity.secondaryColor),
  });
  requireText("visual_identity", "Typography", form.visualIdentity.typography);
  checks.push({
    tab: "visual_identity",
    label: "Upload Font Style Guide",
    complete:
      hasUpload(form.visualIdentity.fontStyleGuide) || hasText(form.visualIdentity.typography),
  });

  requireList("brand_rules", "Set The Rules. Violyt Will Follow Them.", form.brandRules.selectedRules);
  requireText("brand_rules", "Positive Word Bank", form.brandRules.positiveWordBank);
  requireText("brand_rules", "Restricted Topics", form.brandRules.restrictedTopics);
  requireText("brand_rules", "Restricted Claims", form.brandRules.restrictedClaims);
  requireText("brand_rules", "Blocked Words / Phrases", form.brandRules.blockedWordsPhrases);

  return checks;
}

export function getBrandTabCompletion(form: BrandFormState, tabValues: string[]) {
  const tabCompletion = Object.fromEntries(
    tabValues.map((tab) => [tab, { completed: 0, percent: 100, required: 0 }]),
  ) as Record<string, BrandTabCompletion>;

  for (const field of getRequiredBrandFieldChecks(form)) {
    const current = tabCompletion[field.tab] ?? { completed: 0, percent: 100, required: 0 };
    current.required += 1;
    if (field.complete) {
      current.completed += 1;
    }
    current.percent = Math.round((current.completed / current.required) * 100);
    tabCompletion[field.tab] = current;
  }

  return tabCompletion;
}

export function formatMissingRequiredBrandFields(missing: MissingBrandField[]) {
  const visibleFields = missing.slice(0, 5).map((field) => field.label);
  const remainingCount = missing.length - visibleFields.length;
  return remainingCount > 0
    ? `${visibleFields.join(", ")} and ${remainingCount} more`
    : visibleFields.join(", ");
}
