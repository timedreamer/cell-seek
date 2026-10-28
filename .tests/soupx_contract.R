# Run from the repository root: Rscript .tests/soupx_contract.R
suppressPackageStartupMessages(library(Matrix))
source("workflow/scripts/soupx.R")
args <- commandArgs(trailingOnly=TRUE)
if (length(args) == 2L) {
  original_dir <- file.path(args[1], "filtered_feature_bc_matrix")
  corrected_dir <- file.path(args[2], "filtered_feature_bc_matrix")
  annotations <- read_soupx_annotations(original_dir)
  stopifnot(identical(annotations, read_soupx_annotations(corrected_dir)))
  original <- Seurat::Read10X(original_dir, gene.column=1)
  corrected <- Seurat::Read10X(corrected_dir, gene.column=1)
  for (counts in list(original, corrected)) {
    stopifnot(inherits(counts, "sparseMatrix"),
              identical(rownames(counts), annotations$features[[1]]),
              identical(colnames(counts), annotations$barcodes),
              all(is.finite(counts@x)), all(counts@x >= 0),
              all(counts@x == floor(counts@x)))
  }
  stopifnot(identical(dim(original), dim(corrected)), all((corrected-original)@x <= 0))
  summary <- read.delim(file.path(args[2], "soupx_summary.tsv"))
  stopifnot(nrow(summary) == 1L, summary$input_umis == sum(original),
            summary$corrected_umis == sum(corrected),
            summary$removed_umis == sum(original)-sum(corrected),
            isTRUE(all.equal(summary$removed_percent, 100*(sum(original)-sum(corrected))/sum(original))),
            summary$cells == ncol(original), summary$features == nrow(original),
            nrow(Seurat::Read10X(corrected_dir)) == nrow(original))
  print(summary)
  cat("Real-sample round-trip contract passed\n")
  quit(status=0)
}
scratch <- tempfile("soupx-contract-")
dir.create(scratch)

expect_error <- function(expr, pattern) {
  error <- tryCatch({ force(expr); NULL }, error=identity)
  stopifnot(inherits(error, "error"))
  if (!grepl(pattern, conditionMessage(error))) stop(conditionMessage(error))
}

original <- Matrix(matrix(c(8, 4, 0, 2, 6, 0, 0, 0, 0), nrow=3), sparse=TRUE)
dimnames(original) <- list(c("id3", "id1", "id2"), c("cellB-1", "cellA-1", "zero-1"))
annotations <- list(features=data.frame(V1=rownames(original),
                                        V2=c("duplicate", "duplicate", "zero"),
                                        V3="Gene Expression"), barcodes=colnames(original))
corrected <- original
corrected[1, 1] <- 6
result <- file.path(scratch, "result")
dir.create(result)
# A rerun replaces the previous matrix with the newly corrected counts.
write_soupx_result(original, original, annotations, 0.1, "capture", result)
write_soupx_result(corrected, original, annotations, 0.1, "capture", result)
matrix_dir <- file.path(result, "filtered_feature_bc_matrix")
reread_annotations <- read_soupx_annotations(matrix_dir)
stopifnot(identical(annotations, reread_annotations))
reread <- Seurat::Read10X(matrix_dir, gene.column=1)
stopifnot(identical(dimnames(reread), dimnames(original)),
          all(reread == corrected), all(reread <= original),
          all(is.finite(reread@x)), all(reread@x >= 0), all(reread@x == floor(reread@x)))
# The unchanged QC interface uses gene symbols, including Seurat's unique names.
qc_input <- Seurat::Read10X(matrix_dir)
stopifnot(nrow(qc_input) == nrow(original), !anyDuplicated(rownames(qc_input)),
          identical(colnames(qc_input), colnames(original)))
summary <- read.delim(file.path(result, "soupx_summary.tsv"))
stopifnot(summary$input_umis == sum(original), summary$corrected_umis == sum(corrected),
          summary$removed_umis == 2, summary$removed_percent == 100*2/sum(original),
          summary$cells == ncol(original), summary$features == nrow(original),
          summary$seed == 1234, summary$round_to_integer)

# A small homogeneous input tests failure propagation, not meaningful estimation.
outs <- file.path(scratch, "input", "outs")
dir.create(outs, recursive=TRUE)
tiny <- Matrix(matrix(rep(1:3, each=3), nrow=3), sparse=TRUE)
dimnames(tiny) <- dimnames(original)
for (name in c("raw_feature_bc_matrix", "filtered_feature_bc_matrix")) {
  DropletUtils::write10xCounts(file.path(outs, name), tiny, type="mtx", version="3",
                              gene.id=rownames(tiny), gene.symbol=annotations$features$V2)
}
cluster_dir <- file.path(outs, "analysis", "clustering", "gene_expression_graphclust")
dir.create(cluster_dir, recursive=TRUE)
write.csv(data.frame(Barcode=colnames(tiny), Cluster=1),
          file.path(cluster_dir, "clusters.csv"), row.names=FALSE)
failed_output <- file.path(scratch, "failed")
device <- grDevices::dev.cur()
expect_error(run_soupx(outs, failed_output, "capture", "test"), "dimnames|marker|estimat|density")
stopifnot(!file.exists(file.path(failed_output, "filtered_feature_bc_matrix")),
          !file.exists(file.path(failed_output, "soupx_summary.tsv")),
          identical(grDevices::dev.cur(), device))
unlink(scratch, recursive=TRUE)
cat("SoupX matrix contract and failure checks passed\n")
