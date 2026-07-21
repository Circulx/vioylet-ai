import { NextRequest, NextResponse } from "next/server";
import { apiOrigin, serverApiOrigin } from "@/lib/env";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const assetUrl = request.nextUrl.searchParams.get("url") || "";
  if (!assetUrl) {
    return NextResponse.json({ error: "Asset URL is required" }, { status: 400 });
  }

  let parsedUrl: URL;
  try {
    parsedUrl = new URL(assetUrl);
  } catch {
    return NextResponse.json({ error: "Invalid asset URL" }, { status: 400 });
  }

  if (parsedUrl.origin !== apiOrigin || !parsedUrl.pathname.startsWith("/api/v1/storage/download")) {
    return NextResponse.json({ error: "Asset URL is not allowed" }, { status: 400 });
  }

  const fetchUrl = new URL(parsedUrl.pathname + parsedUrl.search, serverApiOrigin);
  const response = await fetch(fetchUrl.toString(), { cache: "no-store" });
  if (!response.ok) {
    return NextResponse.json({ error: "Asset could not be loaded" }, { status: response.status });
  }

  const headers = new Headers();
  const contentType = response.headers.get("content-type");
  const contentLength = response.headers.get("content-length");
  if (contentType) {
    headers.set("content-type", contentType);
  }
  if (contentLength) {
    headers.set("content-length", contentLength);
  }
  headers.set("cache-control", "no-store");

  return new NextResponse(response.body, { status: 200, headers });
}
