"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { JobForm } from "@/components/jobs/job-form";
import { JobTable } from "@/components/jobs/job-table";

export default function JobsPage() {
  const [creating, setCreating] = useState(false);
  const router = useRouter();

  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Embedding Jobs</h1>
          <p className="text-sm text-muted-foreground mt-1.5 max-w-2xl">
            Create, run, and manage jobs that embed B2 imagery tiles with the
            Clay foundation model. Job records and embeddings are stored in your
            B2 bucket — no database.
          </p>
        </div>
        <Button size="sm" className="h-8" onClick={() => setCreating((v) => !v)}>
          {creating ? <X className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
          {creating ? "Close" : "New job"}
        </Button>
      </div>

      {creating && (
        <Card className="animate-fade-in-up">
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">New embedding job</CardTitle>
          </CardHeader>
          <CardContent className="p-5">
            <JobForm
              mode="create"
              onCancel={() => setCreating(false)}
              onSuccess={(job) => router.push(`/jobs/${job.id}`)}
            />
          </CardContent>
        </Card>
      )}

      <JobTable />
    </div>
  );
}
