import { UploadForm } from "@/components/upload/upload-form";

export default function UploadPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Ingest Imagery</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
          Drag GeoTIFF tiles in or click to browse — they upload directly to B2
          under <code>imagery/</code> and appear in the Imagery Library, ready to
          embed. Up to 100 MB per file. No imagery to hand? Run the seed script
          (see the README).
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <UploadForm />
      </div>
    </div>
  );
}
