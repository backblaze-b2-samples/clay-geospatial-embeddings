"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, Pencil, Play, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { JobForm } from "@/components/jobs/job-form";
import { JobStatusBadge } from "@/components/jobs/status-badge";
import { useDeleteJob, useJob, useRunJob } from "@/lib/queries";
import { formatDate } from "@/lib/utils";

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="text-sm">{value}</div>
    </div>
  );
}

export function JobDetail({ id }: { id: string }) {
  const { data: job, isLoading, error, refetch } = useJob(id);
  const runJob = useRunJob(id);
  const deleteJob = useDeleteJob();
  const router = useRouter();
  const [editing, setEditing] = useState(false);

  if (isLoading) {
    return <Skeleton className="h-64 w-full" />;
  }
  if (error || !job) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const running = runJob.isPending || job.status === "running";

  return (
    <div className="space-y-6">
      <div className="animate-fade-in flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="space-y-2">
          <Link
            href="/jobs"
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" /> All jobs
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="page-title">{job.name}</h1>
            <JobStatusBadge status={job.status} />
          </div>
          <p className="font-mono text-xs text-muted-foreground">{job.id}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={() =>
              runJob.mutate(undefined, {
                onSuccess: (j) =>
                  toast[j.status === "succeeded" ? "success" : "error"](
                    j.message ?? "Run finished"
                  ),
                onError: (e) => toast.error(e.message),
              })
            }
            disabled={running}
          >
            <Play className="h-3.5 w-3.5" />
            {running ? "Running…" : "Run"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setEditing((v) => !v)}
            disabled={running}
          >
            <Pencil className="h-3.5 w-3.5" />
            Edit
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button size="sm" variant="outline" disabled={running}>
                <Trash2 className="h-3.5 w-3.5" />
                Delete
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete “{job.name}”?</AlertDialogTitle>
                <AlertDialogDescription>
                  Removes the job record and only its embeddings
                  (<code>embeddings/{job.id}/</code>). Imagery is untouched.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={() =>
                    deleteJob.mutate(job.id, {
                      onSuccess: () => {
                        toast.success("Job deleted");
                        router.push("/jobs");
                      },
                      onError: (e) => toast.error(e.message),
                    })
                  }
                >
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {running && (
        <Alert>
          <AlertTitle>Embedding in progress</AlertTitle>
          <AlertDescription>
            Streaming tiles from B2, running Clay on-device, and writing
            embeddings back to B2. A CPU run over the seed set takes a minute or
            two — this page updates when it finishes.
          </AlertDescription>
        </Alert>
      )}

      {job.message && !running && (
        <Alert
          variant={job.status === "failed" ? "destructive" : "default"}
        >
          <AlertTitle>
            {job.status === "failed" ? "Run failed" : "Last run"}
          </AlertTitle>
          <AlertDescription>{job.message}</AlertDescription>
        </Alert>
      )}

      {editing ? (
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Edit job</CardTitle>
          </CardHeader>
          <CardContent className="p-5">
            <JobForm
              mode="edit"
              job={job}
              onCancel={() => setEditing(false)}
              onSuccess={() => setEditing(false)}
            />
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Configuration & results</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-5 p-5 sm:grid-cols-2 lg:grid-cols-3">
            <Field label="Source prefix" value={<code>{job.config.source_prefix}</code>} />
            <Field label="Tile size" value={`${job.config.tile_size} px`} />
            <Field label="Model" value={job.config.model} />
            <Field label="Sensor" value={job.config.sensor} />
            <Field label="Device" value={job.device ?? "—"} />
            <Field
              label="Tiles embedded"
              value={`${job.tiles_embedded} / ${job.tiles_total}`}
            />
            <Field
              label="Duration"
              value={job.duration_seconds !== null ? `${job.duration_seconds}s` : "—"}
            />
            <Field label="Created" value={formatDate(job.created_at)} />
            <Field
              label="Finished"
              value={job.finished_at ? formatDate(job.finished_at) : "—"}
            />
          </CardContent>
        </Card>
      )}

      {job.embeddings.length > 0 && (
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">
              Embeddings ({job.embeddings.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40 hover:bg-muted/40">
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Tile
                  </TableHead>
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Embedding
                  </TableHead>
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Dims
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {job.embeddings.map((emb) => (
                  <TableRow key={emb.embedding_key} className="table-row-hover">
                    <TableCell className="font-mono text-xs">{emb.tile_key}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {emb.embedding_key}
                    </TableCell>
                    <TableCell className="font-mono text-xs tabular-nums">
                      {emb.dims}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
