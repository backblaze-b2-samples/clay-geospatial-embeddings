"use client";

import { useState } from "react";
import Link from "next/link";
import { Images, Search } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { thumbnailUrl } from "@/lib/api-client";
import { useLibrary } from "@/lib/queries";
import type { ImageryItem } from "@clay-geospatial-embeddings/shared";

function Thumb({ item }: { item: ImageryItem }) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <div className="flex aspect-square w-full items-center justify-center bg-muted text-muted-foreground">
        <Images className="h-8 w-8" />
      </div>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={thumbnailUrl(item.key)}
      alt={item.filename}
      className="aspect-square w-full bg-muted object-cover"
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2 text-xs">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono tabular-nums">{value}</span>
    </div>
  );
}

export function ImageryGallery() {
  const { data: items = [], isLoading, error, refetch } = useLibrary();

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="aspect-[3/4] w-full" />
        ))}
      </div>
    );
  }
  if (error) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }
  if (items.length === 0) {
    return (
      <EmptyState
        icon={Images}
        title="No imagery tiles yet"
        description="Upload GeoTIFFs or run the seed script (see the README) to populate imagery/."
      />
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {items.map((item) => {
        const m = item.metadata;
        return (
          <Card key={item.key} className="overflow-hidden">
            <Thumb item={item} />
            <CardContent className="space-y-2 p-4">
              <div className="truncate text-sm font-medium" title={item.filename}>
                {item.filename}
              </div>
              {m ? (
                <div className="space-y-1">
                  <MetaRow label="Size" value={`${m.width}×${m.height}`} />
                  <MetaRow label="Bands" value={m.band_count ?? "—"} />
                  <MetaRow label="CRS" value={m.crs ?? "—"} />
                  <MetaRow
                    label="GSD"
                    value={m.gsd !== null ? `${m.gsd.toFixed(1)} m` : "—"}
                  />
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">
                  {item.metadata_warning ?? "No geospatial metadata."}
                </p>
              )}
              <div className="flex items-center justify-between pt-1">
                <span className="text-xs text-muted-foreground">
                  {item.size_human}
                </span>
                <Button asChild size="sm" variant="outline" className="h-7">
                  <Link href={`/search?key=${encodeURIComponent(item.key)}`}>
                    <Search className="h-3 w-3" />
                    Find similar
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
