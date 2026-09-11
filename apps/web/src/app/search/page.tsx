import { Suspense } from "react";

import { SimilaritySearch } from "@/components/search/similarity-search";

export default function SearchPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Similarity Search</h1>
        <p className="text-sm text-muted-foreground mt-1.5 max-w-2xl">
          Pick a tile, embed it with Clay, and retrieve the most similar scenes
          across the archive (k-NN over the embeddings in B2). Run an Embedding
          Job first so there is an index to search.
        </p>
      </div>
      <Suspense fallback={null}>
        <SimilaritySearch />
      </Suspense>
    </div>
  );
}
