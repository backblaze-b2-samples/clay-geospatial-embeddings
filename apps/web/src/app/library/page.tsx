import { ImageryGallery } from "@/components/library/imagery-gallery";

export default function LibraryPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Imagery Library</h1>
        <p className="text-sm text-muted-foreground mt-1.5 max-w-2xl">
          Scoped gallery of GeoTIFF tiles under <code>imagery/</code> in your B2
          bucket, with PNG thumbnails and parsed geospatial metadata (CRS,
          bounds, band count, ground sample distance). The whole bucket stays
          browsable under Files.
        </p>
      </div>
      <ImageryGallery />
    </div>
  );
}
