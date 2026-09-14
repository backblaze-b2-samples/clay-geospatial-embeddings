"use client";

import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { Search as SearchIcon } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EmptyState } from "@/components/ui/empty-state";
import { thumbnailUrl } from "@/lib/api-client";
import { useLibrary, useSearch } from "@/lib/queries";
import type { SearchHit, SensorPreset } from "@clay-geospatial-embeddings/shared";

const SENSORS: { value: SensorPreset; label: string }[] = [
  { value: "sentinel-2-rgb", label: "Sentinel-2 RGB" },
  { value: "sentinel-2-l2a", label: "Sentinel-2 L2A (multispectral)" },
  { value: "naip-rgb", label: "NAIP RGB" },
];

/**
 * De-dupe hits by `tile_key`, keeping the first (best-scoring, since hits
 * arrive sorted most-similar-first) occurrence per tile.
 *
 * The shared archive can hold more than one embedding for the same source
 * tile (e.g. after re-running an Embedding Job), and every duplicate renders
 * the identical `thumbnailUrl(tile_key)`. Rendering one <img> per raw hit then
 * points several elements at the same URL at once, and those concurrent
 * requests race and get cancelled (net::ERR_ABORTED) instead of painting —
 * the failure mode the Imagery Library grid never hits, since it lists each
 * tile once. A pure function keeps this testable without rendering a
 * component — the `hits` memo in `SimilaritySearch` below is its only
 * production caller.
 */
export function dedupeHitsByTileKey(hits: SearchHit[]): SearchHit[] {
  const seen = new Set<string>();
  return hits.filter((hit) => {
    if (seen.has(hit.tile_key)) return false;
    seen.add(hit.tile_key);
    return true;
  });
}

function HitCard({ hit }: { hit: SearchHit }) {
  const [failed, setFailed] = useState(false);
  const pct = Math.round(hit.score * 100);
  return (
    <Card className="overflow-hidden">
      {failed ? (
        <div className="flex aspect-square items-center justify-center bg-muted text-xs text-muted-foreground">
          no preview
        </div>
      ) : (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={thumbnailUrl(hit.tile_key)}
          alt={hit.tile_key}
          className="aspect-square w-full bg-muted object-cover"
          loading="lazy"
          onError={() => setFailed(true)}
        />
      )}
      <CardContent className="space-y-2 p-3">
        <div className="truncate font-mono text-xs" title={hit.tile_key}>
          {hit.tile_key}
        </div>
        <div className="flex items-center gap-2">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary"
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className="font-mono text-xs tabular-nums">{pct}%</span>
        </div>
      </CardContent>
    </Card>
  );
}

export function SimilaritySearch() {
  const params = useSearchParams();
  const { data: imagery = [] } = useLibrary();
  const search = useSearch();

  const hits = useMemo(
    () => (search.data ? dedupeHitsByTileKey(search.data.hits) : []),
    [search.data]
  );

  // Preselect from ?key= (deep link from the Imagery Library "Find similar").
  const [queryKey, setQueryKey] = useState<string>(() => params.get("key") ?? "");
  const [sensor, setSensor] = useState<SensorPreset>("sentinel-2-rgb");
  const [k, setK] = useState(6);

  const options = Array.from(
    new Set([...(queryKey ? [queryKey] : []), ...imagery.map((i) => i.key)])
  );

  const runSearch = () => {
    if (!queryKey) {
      toast.error("Pick a query tile first");
      return;
    }
    search.mutate(
      { query_key: queryKey, k, sensor },
      { onError: (e) => toast.error(e.message) }
    );
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="border-b border-border py-4 px-5">
          <CardTitle className="card-title">Query</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 p-5 sm:grid-cols-[1fr_auto_auto_auto] sm:items-end">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">
              Query tile
            </label>
            <Select value={queryKey} onValueChange={setQueryKey}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Pick an imagery tile…" />
              </SelectTrigger>
              <SelectContent>
                {options.map((key) => (
                  <SelectItem key={key} value={key}>
                    {key}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">
              Sensor
            </label>
            <Select value={sensor} onValueChange={(v) => setSensor(v as SensorPreset)}>
              <SelectTrigger className="w-56">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SENSORS.map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-muted-foreground">
              Results (k)
            </label>
            <Input
              type="number"
              min={1}
              max={50}
              value={k}
              onChange={(e) => setK(Number(e.target.value) || 6)}
              className="w-24 tabular-nums"
            />
          </div>
          <Button onClick={runSearch} disabled={search.isPending}>
            <SearchIcon className="h-4 w-4" />
            {search.isPending ? "Searching…" : "Search"}
          </Button>
        </CardContent>
      </Card>

      {search.data && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            {hits.length} nearest of {search.data.index_size} embedded
            tiles, most similar first.
          </p>
          {hits.length === 0 ? (
            <EmptyState
              icon={SearchIcon}
              title="No matches"
              description="The archive has no embeddings yet — run an Embedding Job first."
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {hits.map((hit) => (
                <HitCard key={hit.tile_key} hit={hit} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
