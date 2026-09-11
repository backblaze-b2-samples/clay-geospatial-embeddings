import { Badge } from "@/components/ui/badge";
import type { JobStatus } from "@clay-geospatial-embeddings/shared";

const STYLES: Record<JobStatus, string> = {
  pending: "bg-muted text-muted-foreground",
  running: "bg-[var(--attention-subtle)] text-[var(--attention)]",
  succeeded: "bg-[color-mix(in_oklab,var(--success)_15%,transparent)] text-[var(--success)]",
  failed: "bg-[color-mix(in_oklab,var(--attention)_15%,transparent)] text-[var(--attention)]",
};

const LABELS: Record<JobStatus, string> = {
  pending: "Pending",
  running: "Running",
  succeeded: "Succeeded",
  failed: "Failed",
};

export function JobStatusBadge({ status }: { status: JobStatus }) {
  return (
    <Badge className={`border-transparent font-medium ${STYLES[status]}`}>
      {status === "running" && (
        <span className="mr-1.5 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
      )}
      {LABELS[status]}
    </Badge>
  );
}
