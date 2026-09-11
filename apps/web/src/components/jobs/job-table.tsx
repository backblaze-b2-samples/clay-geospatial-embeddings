"use client";

import Link from "next/link";
import { Layers, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { JobStatusBadge } from "@/components/jobs/status-badge";
import { useDeleteJob, useJobs } from "@/lib/queries";
import { formatDate } from "@/lib/utils";

const SENSOR_LABELS: Record<string, string> = {
  "sentinel-2-rgb": "Sentinel-2 RGB",
  "sentinel-2-l2a": "Sentinel-2 L2A",
  "naip-rgb": "NAIP RGB",
};

export function JobTable() {
  const { data: jobs = [], isLoading, error, refetch } = useJobs();
  const deleteJob = useDeleteJob();

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }
  if (error) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }
  if (jobs.length === 0) {
    return (
      <EmptyState
        icon={Layers}
        title="No embedding jobs yet"
        description="Create a job to embed imagery tiles with Clay. Seed some tiles first (see the README) if your bucket is empty."
      />
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow className="bg-muted/40 hover:bg-muted/40">
          <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Name
          </TableHead>
          <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Status
          </TableHead>
          <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Sensor
          </TableHead>
          <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Tiles
          </TableHead>
          <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Created
          </TableHead>
          <TableHead className="w-10" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {jobs.map((job) => (
          <TableRow key={job.id} className="table-row-hover">
            <TableCell className="font-medium">
              <Link
                href={`/jobs/${job.id}`}
                className="rounded-sm underline-offset-4 hover:underline"
              >
                {job.name}
              </Link>
            </TableCell>
            <TableCell>
              <JobStatusBadge status={job.status} />
            </TableCell>
            <TableCell className="text-muted-foreground whitespace-nowrap">
              {SENSOR_LABELS[job.config.sensor] ?? job.config.sensor}
            </TableCell>
            <TableCell className="font-mono text-xs tabular-nums text-muted-foreground">
              {job.tiles_embedded}/{job.tiles_total}
            </TableCell>
            <TableCell className="text-muted-foreground whitespace-nowrap">
              {formatDate(job.created_at)}
            </TableCell>
            <TableCell>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-[var(--attention)]"
                    disabled={job.status === "running"}
                    aria-label={`Delete ${job.name}`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Delete “{job.name}”?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This removes the job record and only this job&apos;s
                      embeddings (<code>embeddings/{job.id}/</code>). Imagery
                      tiles are not touched. This cannot be undone.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={() =>
                        deleteJob.mutate(job.id, {
                          onSuccess: () => toast.success("Job deleted"),
                          onError: (e) => toast.error(e.message),
                        })
                      }
                    >
                      Delete
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
