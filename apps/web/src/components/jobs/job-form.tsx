"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useCreateJob, useJobSourcePrefixes, useUpdateJob } from "@/lib/queries";
import type { JobRecord } from "@clay-geospatial-embeddings/shared";

const SENSORS = [
  { value: "sentinel-2-rgb", label: "Sentinel-2 RGB" },
  { value: "sentinel-2-l2a", label: "Sentinel-2 L2A (multispectral)" },
  { value: "naip-rgb", label: "NAIP RGB" },
] as const;

const CUSTOM = "__custom__";

const schema = z.object({
  name: z.string().min(1, "Give the job a name").max(120),
  source_prefix: z.string().min(1),
  custom_prefix: z.string().optional(),
  tile_size: z.enum(["256", "512"]),
  model: z.enum(["clay-v1.5"]),
  sensor: z.enum(["sentinel-2-rgb", "sentinel-2-l2a", "naip-rgb"]),
});

type FormValues = z.infer<typeof schema>;

interface JobFormProps {
  mode: "create" | "edit";
  job?: JobRecord;
  onSuccess?: (job: JobRecord) => void;
  onCancel?: () => void;
}

export function JobForm({ mode, job, onSuccess, onCancel }: JobFormProps) {
  const { data: prefixes = [] } = useJobSourcePrefixes();
  const createJob = useCreateJob();
  const updateJob = useUpdateJob(job?.id ?? "");
  const pending = createJob.isPending || updateJob.isPending;

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: job?.name ?? "",
      source_prefix: job?.config.source_prefix ?? "imagery/",
      custom_prefix: "",
      tile_size: String(job?.config.tile_size ?? 256) as "256" | "512",
      model: job?.config.model ?? "clay-v1.5",
      sensor: job?.config.sensor ?? "sentinel-2-rgb",
    },
  });

  const [prefixMode, setPrefixMode] = useState<string>(
    job?.config.source_prefix ?? "imagery/"
  );

  const prefixOptions = Array.from(new Set(["imagery/", ...prefixes]));
  const isCreate = mode === "create";

  const onSubmit = async (values: FormValues) => {
    const source_prefix =
      values.source_prefix === CUSTOM
        ? (values.custom_prefix || "").trim()
        : values.source_prefix;
    if (!source_prefix) {
      form.setError("custom_prefix", { message: "Enter a source prefix" });
      return;
    }
    const config = {
      source_prefix,
      tile_size: Number(values.tile_size) as 256 | 512,
      model: values.model,
      sensor: values.sensor,
    };
    try {
      const result = isCreate
        ? await createJob.mutateAsync({ name: values.name.trim(), config })
        : await updateJob.mutateAsync({ name: values.name.trim(), config });
      toast.success(isCreate ? "Job created" : "Job updated");
      onSuccess?.(result);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Save failed");
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Job name</FormLabel>
              <FormControl>
                <Input placeholder="e.g. sentinel2-tirana-2024" {...field} />
              </FormControl>
              {isCreate && (
                <FormDescription>
                  A memorable label — the only free-text field.
                </FormDescription>
              )}
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="source_prefix"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Source prefix</FormLabel>
              <Select
                value={field.value}
                onValueChange={(v) => {
                  field.onChange(v);
                  setPrefixMode(v);
                }}
              >
                <FormControl>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {prefixOptions.map((p) => (
                    <SelectItem key={p} value={p}>
                      {p}
                    </SelectItem>
                  ))}
                  <SelectItem value={CUSTOM}>Custom prefix…</SelectItem>
                </SelectContent>
              </Select>
              {isCreate && (
                <FormDescription>
                  Which B2 prefix to embed. Default <code>imagery/</code>.
                </FormDescription>
              )}
              <FormMessage />
            </FormItem>
          )}
        />

        {prefixMode === CUSTOM && (
          <FormField
            control={form.control}
            name="custom_prefix"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Custom prefix</FormLabel>
                <FormControl>
                  <Input placeholder="imagery/my-scenes/" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        )}

        <FormField
          control={form.control}
          name="tile_size"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Tile size</FormLabel>
              <FormControl>
                <RadioGroup
                  onValueChange={field.onChange}
                  value={field.value}
                  className="flex gap-6"
                >
                  {["256", "512"].map((s) => (
                    <label
                      key={s}
                      className="flex items-center gap-2 text-sm cursor-pointer"
                    >
                      <RadioGroupItem value={s} />
                      {s} px
                    </label>
                  ))}
                </RadioGroup>
              </FormControl>
              {isCreate && (
                <FormDescription>256 is a sound first run.</FormDescription>
              )}
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="model"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Model</FormLabel>
              <Select value={field.value} onValueChange={field.onChange}>
                <FormControl>
                  <SelectTrigger className="w-60">
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="clay-v1.5">Clay v1.5</SelectItem>
                </SelectContent>
              </Select>
              {isCreate && (
                <FormDescription>
                  Clay&apos;s own foundation model, run locally.
                </FormDescription>
              )}
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="sensor"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Sensor / band preset</FormLabel>
              <Select value={field.value} onValueChange={field.onChange}>
                <FormControl>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {SENSORS.map((s) => (
                    <SelectItem key={s.value} value={s.value}>
                      {s.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {isCreate && (
                <FormDescription>
                  Sentinel-2 RGB matches the seed tiles.
                </FormDescription>
              )}
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="flex items-center justify-end gap-2 pt-2">
          {onCancel && (
            <Button type="button" variant="outline" onClick={onCancel}>
              Cancel
            </Button>
          )}
          <Button type="submit" disabled={pending}>
            {pending
              ? "Saving…"
              : isCreate
                ? "Create job"
                : "Save changes"}
          </Button>
        </div>
      </form>
    </Form>
  );
}
