import { NextResponse } from "next/server";

type GoogleFontsApiItem = {
  family: string;
  category?: string;
  variants?: string[];
  version?: string;
  lastModified?: string;
};

type GoogleFontsApiResponse = {
  items?: GoogleFontsApiItem[];
};

const GOOGLE_FONTS_API_URL = "https://www.googleapis.com/webfonts/v1/webfonts";

export async function GET() {
  const apiKey = process.env.GOOGLE_FONTS_API_KEY;

  if (!apiKey) {
    return NextResponse.json(
      {
        error: "Missing GOOGLE_FONTS_API_KEY.",
        items: [],
      },
      { status: 503 },
    );
  }

  const searchParams = new URLSearchParams({
    key: apiKey,
    sort: "popularity",
    fields: "items(family,category,variants,version,lastModified)",
  });

  try {
    const response = await fetch(`${GOOGLE_FONTS_API_URL}?${searchParams.toString()}`, {
      next: { revalidate: 60 * 60 * 12 },
    });

    if (!response.ok) {
      return NextResponse.json(
        {
          error: "Unable to load Google Fonts right now.",
          items: [],
        },
        { status: response.status },
      );
    }

    const payload = (await response.json()) as GoogleFontsApiResponse;

    return NextResponse.json({
      items: (payload.items || []).map((item) => ({
        family: item.family,
        category: item.category || "",
        variants: item.variants || [],
        version: item.version || "",
        lastModified: item.lastModified || "",
      })),
    });
  } catch {
    return NextResponse.json(
      {
        error: "Unable to reach Google Fonts right now.",
        items: [],
      },
      { status: 502 },
    );
  }
}
