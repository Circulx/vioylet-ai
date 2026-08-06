"use client";

import { useState } from "react";
import { useBrands } from "@/hooks/useBrands";
import { request } from "@/lib/api/request";
import { API } from "@/lib/api/endpoints";
import { toast } from "@/components/ui/use-toast";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Spinner } from "@/components/ui/spinner";
import type {
  RetrievalPreviewResponse,
  RankedChunkResponse,
  RetrievedChunkResponse,
} from "@/lib/api/contracts";

const PLATFORMS = [
  { value: "instagram", label: "Instagram" },
  { value: "linkedin", label: "LinkedIn" },
  { value: "x", label: "X (Twitter)" },
  { value: "youtube_thumbnail", label: "YouTube Thumbnail" },
];

const FORMATS = [
  { value: "static", label: "Static" },
  { value: "carousel", label: "Carousel" },
  { value: "pdf", label: "PDF" },
  { value: "infographic", label: "Infographic" },
];

function isolationBadgeVariant(
  status: string,
): "default" | "secondary" | "destructive" | "outline" {
  if (status === "pass") return "default";
  if (status === "warning") return "secondary";
  return "destructive";
}

function tierColor(tier: string) {
  if (tier === "high") return "text-green-600";
  if (tier === "medium") return "text-yellow-600";
  return "text-slate-500";
}

function ChunkList({
  title,
  chunks,
}: {
  title: string;
  chunks: RetrievedChunkResponse[];
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-semibold">
          {title} ({chunks.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {chunks.length === 0 ? (
          <p className="text-xs text-slate-400">No chunks in this tier.</p>
        ) : (
          chunks.map((chunk, i) => (
            <div
              key={i}
              className="rounded-md border border-slate-200 p-3 text-xs"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-slate-700">
                  {chunk.source} / {chunk.section}
                </span>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-[10px]">
                    {chunk.influence_area}
                  </Badge>
                  {(chunk.used ?? chunk.used_in_output) && (
                    <Badge className="bg-primary/70 text-[10px]">USED</Badge>
                  )}
                  <span className="font-mono text-slate-600">
                    {(chunk.relevance_score ?? 0).toFixed(3)}
                  </span>
                </div>
              </div>
              {chunk.content_summary && (
                <p className="mt-2 text-[11px] leading-relaxed text-slate-600">
                  {chunk.content_summary}
                </p>
              )}
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

export default function BrandRetrievalPage() {
  const { data: brands, isLoading: brandsLoading } = useBrands();
  const [brandId, setBrandId] = useState("");
  const [userPrompt, setUserPrompt] = useState("");
  const [platform, setPlatform] = useState("instagram");
  const [format, setFormat] = useState("static");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RetrievalPreviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runRetrieval = async () => {
    if (!brandId) {
      toast({
        title: "Select a brand first",
        variant: "destructive",
      });
      return;
    }
    if (!userPrompt.trim()) {
      toast({
        title: "Enter a prompt to search",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await request(API.BRANDS.RETRIEVAL_PREVIEW, {
        pathParams: brandId,
        data: {
          user_prompt: userPrompt,
          platform,
          format,
        },
      });
      setResult(res);
      toast({
        title: "Retrieval complete",
        variant: "success",
      });
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Retrieval request failed";
      setError(msg);
      toast({
        title: "Retrieval failed",
        description: msg,
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const highChunks = result?.brand_context.high_relevance_context ?? [];
  const mediumChunks = result?.brand_context.medium_relevance_context ?? [];
  const lowChunks = result?.brand_context.low_relevance_context ?? [];
  const ranked = result?.ranked_chunks ?? [];

  return (
    <div className="w-full px-4 py-6">
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-slate-900">Brand Retrieval</h1>
        <p className="text-sm text-slate-500">
          Developer / QA tool for Layer 1 brand knowledge lookup. Paste a prompt, pick a Brand Space,
          and inspect which uploaded documents the AI retrieves before generation. This is not the
          chat Studio — use Brand Space → Open Studio for content creation.
        </p>

        {/* Input Form */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Retrieval Inputs</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="brand-select">Brand</Label>
                <Select
                  value={brandId}
                  onValueChange={setBrandId}
                  disabled={brandsLoading}
                >
                  <SelectTrigger id="brand-select" className="w-full">
                    <SelectValue
                      placeholder={
                        brandsLoading
                          ? "Loading brands..."
                          : "Select a brand"
                      }
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {(brands ?? [])
                      .filter(
                        (b) =>
                          b.lifecycle_state !== "archived" &&
                          b.lifecycle_state !== "deleted",
                      )
                      .map((b) => (
                        <SelectItem key={b.id} value={b.id}>
                          {b.name}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="platform-select">Platform</Label>
                  <Select value={platform} onValueChange={setPlatform}>
                    <SelectTrigger id="platform-select" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {PLATFORMS.map((p) => (
                        <SelectItem key={p.value} value={p.value}>
                          {p.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="format-select">Format</Label>
                  <Select value={format} onValueChange={setFormat}>
                    <SelectTrigger id="format-select" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {FORMATS.map((f) => (
                        <SelectItem key={f.value} value={f.value}>
                          {f.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="prompt-input">Prompt</Label>
              <Textarea
                id="prompt-input"
                placeholder="e.g. Create a campaign announcement post about our new product launch"
                value={userPrompt}
                onChange={(e) => setUserPrompt(e.target.value)}
                rows={3}
              />
            </div>

            <div className="flex justify-end">
              <Button
                onClick={() => void runRetrieval()}
                disabled={loading}
                className="min-w-40"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <Spinner className="h-4 w-4" /> Running...
                  </span>
                ) : (
                  "Run Retrieval"
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {error && (
          <Card className="border-destructive">
            <CardContent className="py-4">
              <p className="text-sm text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-6">
            {/* Summary */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Retrieval Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                  <div className="space-y-1">
                    <p className="text-xs text-slate-500">
                      Isolation Status
                    </p>
                    <Badge
                      variant={isolationBadgeVariant(
                        result.brand_context.brand_isolation_status,
                      )}
                    >
                      {(result.brand_context.brand_isolation_status ?? "unknown").toUpperCase()}
                    </Badge>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-slate-500">
                      Retrieval Confidence
                    </p>
                    <p className="text-lg font-semibold">
                      {((result.brand_context.retrieval_confidence ?? 0) * 100).toFixed(1)}%
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-slate-500">
                      Total Chunks Retrieved
                    </p>
                    <p className="text-lg font-semibold">
                      {result.brand_context.total_chunks_retrieved}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs text-slate-500">
                      Sections Covered
                    </p>
                    <p className="text-sm font-medium">
                      {result.brand_context.retrieved_sections.join(", ") ||
                        "—"}
                    </p>
                  </div>
                </div>

                <div className="mt-4 space-y-1">
                  <p className="text-xs text-slate-500">Retrieval Query</p>
                  <p className="rounded bg-slate-50 p-2 font-mono text-xs text-slate-700">
                    {result.brand_context.retrieval_query}
                  </p>
                </div>

                {result.brand_context.missing_context.length > 0 && (
                  <div className="mt-4 space-y-1">
                    <p className="text-xs text-slate-500">Missing Context</p>
                    <div className="flex flex-wrap gap-2">
                      {result.brand_context.missing_context.map((m, i) => (
                        <Badge
                          key={i}
                          variant="outline"
                          className="text-xs text-destructive"
                        >
                          {m}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Tier Sections */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <ChunkList title="High Relevance" chunks={highChunks} />
              <ChunkList title="Medium Relevance" chunks={mediumChunks} />
              <ChunkList title="Low Relevance" chunks={lowChunks} />
            </div>

            {/* Ranked Chunks with Signal Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  Ranked Chunks — Signal Breakdown
                </CardTitle>
              </CardHeader>
              <CardContent>
                {ranked.length === 0 ? (
                  <p className="text-sm text-slate-400">
                    No ranked chunks returned.
                  </p>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-8">#</TableHead>
                        <TableHead>Source / Section</TableHead>
                        <TableHead>Influence</TableHead>
                        <TableHead className="text-right">Pinecone</TableHead>
                        <TableHead className="text-right">Campaign</TableHead>
                        <TableHead className="text-right">Audience</TableHead>
                        <TableHead className="text-right">Compliance</TableHead>
                        <TableHead className="text-right">Visual</TableHead>
                        <TableHead className="text-right">Composite</TableHead>
                        <TableHead>Tier</TableHead>
                        <TableHead>Used</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {ranked.map((chunk: RankedChunkResponse, i) => (
                        <TableRow key={i}>
                          <TableCell className="text-xs text-slate-400">
                            {i + 1}
                          </TableCell>
                          <TableCell className="text-xs">
                            <div className="font-medium">
                              {chunk.source}
                            </div>
                            <div className="text-slate-500">
                              {chunk.section}
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant="outline"
                              className="text-[10px]"
                            >
                              {chunk.influence_area}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right font-mono text-xs">
                            {(chunk.pinecone_score ?? 0).toFixed(3)}
                          </TableCell>
                          <TableCell className="text-right font-mono text-xs">
                            {(chunk.campaign_score ?? chunk.signal_scores?.campaign ?? 0).toFixed(2)}
                          </TableCell>
                          <TableCell className="text-right font-mono text-xs">
                            {(chunk.audience_score ?? chunk.signal_scores?.audience ?? 0).toFixed(2)}
                          </TableCell>
                          <TableCell className="text-right font-mono text-xs">
                            {(chunk.compliance_score ?? chunk.signal_scores?.compliance ?? 0).toFixed(2)}
                          </TableCell>
                          <TableCell className="text-right font-mono text-xs">
                            {(chunk.visual_score ?? chunk.signal_scores?.visual ?? 0).toFixed(2)}
                          </TableCell>
                          <TableCell className="text-right font-mono text-xs font-semibold">
                            {(chunk.composite_score ?? 0).toFixed(3)}
                          </TableCell>
                          <TableCell
                            className={`text-xs font-medium ${tierColor(chunk.tier)}`}
                          >
                            {chunk.tier}
                          </TableCell>
                          <TableCell>
                            {(chunk.used ?? chunk.used_in_output) ? (
                              <Badge className="bg-primary/70 text-[10px]">
                                YES
                              </Badge>
                            ) : (
                              <span className="text-xs text-slate-400">—</span>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>

            {/* Retrieval Log */}
            {result.retrieval_log && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Retrieval Log</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="mb-3 grid grid-cols-2 gap-4 md:grid-cols-3">
                    <div>
                      <p className="text-xs text-slate-500">Namespace</p>
                      <p className="font-mono text-xs">
                        {result.retrieval_log.namespace}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">Total Chunks</p>
                      <p className="font-mono text-xs">
                        {result.retrieval_log.total_chunks}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">Query</p>
                      <p className="font-mono text-xs">
                        {result.retrieval_log.query}
                      </p>
                    </div>
                  </div>

                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-8">#</TableHead>
                        <TableHead>Source</TableHead>
                        <TableHead>Section</TableHead>
                        <TableHead>Influence</TableHead>
                        <TableHead className="text-right">Score</TableHead>
                        <TableHead>Used</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {result.retrieval_log.chunks.map((chunk, i) => (
                        <TableRow key={i}>
                          <TableCell className="text-xs text-slate-400">
                            {i + 1}
                          </TableCell>
                          <TableCell className="text-xs">
                            {chunk.source}
                          </TableCell>
                          <TableCell className="text-xs">
                            {chunk.section}
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant="outline"
                              className="text-[10px]"
                            >
                              {chunk.influence_area}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right font-mono text-xs">
                            {(chunk.relevance_score ?? 0).toFixed(3)}
                          </TableCell>
                          <TableCell>
                            {chunk.used ? (
                              <Badge className="bg-primary/70 text-[10px]">
                                YES
                              </Badge>
                            ) : (
                              <span className="text-xs text-slate-400">—</span>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
