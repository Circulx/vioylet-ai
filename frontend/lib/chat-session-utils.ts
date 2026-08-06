import type { ChatSessionResponse, StudioPanelSelection } from "@/lib/api/contracts";

type FormatMode = "static" | "carousel" | "infographic" | "video";
type Platform = "instagram" | "linkedin" | "x" | "youtube_thumbnail";
type FileType = "doc" | "pdf" | "jpg" | "png";

export type StudioPanelState = {
  format: FormatMode;
  platform: Platform;
  fileType: FileType;
  sizeLabel: string;
};

const sizeOptionsByFormatPlatform: Record<
  Exclude<FormatMode, "video">,
  Partial<Record<Platform, Array<{ label: string; width: number; height: number }>>>
> = {
  static: {
    linkedin: [
      { label: "1.91:1 · 1200×627", width: 1200, height: 627 },
      { label: "1:1 · 1080×1080", width: 1080, height: 1080 },
    ],
    instagram: [
      { label: "1:1 · 1080×1080", width: 1080, height: 1080 },
      { label: "4:5 · 1080×1350", width: 1080, height: 1350 },
      { label: "9:16 · 1080×1920", width: 1080, height: 1920 },
    ],
    x: [
      { label: "16:9 · 1200×675", width: 1200, height: 675 },
      { label: "1:1 · 1080×1080", width: 1080, height: 1080 },
    ],
  },
  carousel: {
    linkedin: [{ label: "4:5 · 1080×1350", width: 1080, height: 1350 }],
    instagram: [{ label: "4:5 · 1080×1350", width: 1080, height: 1350 }],
    x: [{ label: "1:1 · 1080×1080", width: 1080, height: 1080 }],
  },
  infographic: {
    linkedin: [{ label: "4:5 · 1080×1350", width: 1080, height: 1350 }],
    instagram: [{ label: "4:5 · 1080×1350", width: 1080, height: 1350 }],
    x: [{ label: "4:5 · 1080×1350", width: 1080, height: 1350 }],
  },
};

function resolveSizeLabel(
  format: FormatMode,
  platform: Platform,
  size?: { width: number; height: number },
): string {
  const fmt = format === "video" ? "static" : format;
  const options =
    sizeOptionsByFormatPlatform[fmt]?.[platform] ||
    sizeOptionsByFormatPlatform[fmt]?.linkedin ||
    [{ label: "1:1 · 1080×1080", width: 1080, height: 1080 }];
  if (size?.width && size?.height) {
    const match = options.find((entry) => entry.width === size.width && entry.height === size.height);
    if (match) {
      return match.label;
    }
    return `${size.width}×${size.height}`;
  }
  return options[0].label;
}

export function studioPanelToState(panel?: StudioPanelSelection | null): StudioPanelState | null {
  if (!panel) {
    return null;
  }
  const format = (panel.format === "pdf" ? "static" : panel.format) as FormatMode;
  const platform = (panel.platform_preset || "linkedin") as Platform;
  const fileType = (panel.file_type || "png") as FileType;
  return {
    format,
    platform,
    fileType,
    sizeLabel: resolveSizeLabel(format, platform, panel.size),
  };
}

export function deriveChatTitle(prompt: string, fallback = "New chat"): string {
  const cleaned = prompt.replace(/\s+/g, " ").trim();
  if (!cleaned) {
    return fallback;
  }
  const sentence = cleaned.split(/[.!?\n]/)[0]?.trim() || cleaned;
  const words = sentence.split(/\s+/).slice(0, 8).join(" ");
  if (words.length <= 60) {
    return words;
  }
  return `${words.slice(0, 57)}...`;
}

export function isSessionFromToday(session: ChatSessionResponse): boolean {
  const value = session.updated_at || session.created_at;
  if (!value) {
    return false;
  }
  const updated = new Date(value);
  if (Number.isNaN(updated.getTime())) {
    return false;
  }
  const startOfToday = new Date();
  startOfToday.setHours(0, 0, 0, 0);
  return updated >= startOfToday;
}

export function filterTodaySessions(sessions: ChatSessionResponse[]): ChatSessionResponse[] {
  return sessions.filter(isSessionFromToday);
}

export function formatChatSessionDate(value?: string): string {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const now = new Date();
  const isToday =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();
  if (isToday) {
    return date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  }
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export const defaultStudioPanel: StudioPanelSelection = {
  format: "static",
  platform_preset: "instagram",
  file_type: "png",
  size: { width: 1080, height: 1080 },
};
