import type { CreativeBlueprintResponse, StructuredTextPayload } from "@/lib/api/contracts";

export function buildPostCaption({
  platform,
  blueprint,
  generatedPayload,
}: {
  platform: string;
  blueprint?: CreativeBlueprintResponse | null;
  generatedPayload?: StructuredTextPayload | null;
}): string {
  const hook = blueprint?.hook?.trim() || "";
  const headline = generatedPayload?.headline?.trim() || blueprint?.headline?.trim() || "";
  const body = generatedPayload?.body?.trim() || blueprint?.body?.trim() || "";
  const cta = generatedPayload?.cta?.trim() || blueprint?.cta?.trim() || "";
  const hashtags = (generatedPayload?.hashtags?.length
    ? generatedPayload.hashtags
    : blueprint?.hashtags) || [];

  const normalized = platform === "x" ? "twitter" : platform;
  const tags = hashtags
    .map((tag) => String(tag || "").trim())
    .filter(Boolean)
    .map((tag) => (tag.startsWith("#") ? tag : `#${tag.replace(/^#+/, "")}`));

  const parts: string[] = [];
  const lead = hook || headline;

  if (normalized === "instagram") {
    if (lead) parts.push(lead);
    if (body) parts.push(body);
    if (cta) parts.push(cta);
    if (tags.length) parts.push(tags.join(" "));
  } else if (normalized === "linkedin") {
    if (lead) parts.push(lead);
    if (body) parts.push(body);
    if (cta) parts.push(cta);
    if (tags.length) parts.push(tags.slice(0, 5).join(" "));
  } else {
    if (lead) parts.push(lead);
    if (body) {
      parts.push(body.length > 220 ? `${body.slice(0, 217).trim()}…` : body);
    }
    if (cta) parts.push(cta);
    if (tags.length) parts.push(tags.slice(0, 3).join(" "));
  }

  return parts.join("\n\n").trim();
}
