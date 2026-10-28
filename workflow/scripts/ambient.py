"""Validation and Cell Ranger file contracts for optional ambient correction."""

import os


MATRIX_FILES = ("matrix.mtx.gz", "barcodes.tsv.gz", "features.tsv.gz")


def validate_ambient_options(options):
    method = options.get("ambient_rna_method", "none")
    if method not in ("none", "soupx"):
        raise ValueError("ambient_rna_method must be 'none' or 'soupx'.")
    if method == "soupx":
        if options["pipeline"] != "gex":
            raise ValueError("SoupX requires --pipeline gex (gene expression only).")
        if options.get("aggregate", "") != "":
            raise ValueError("SoupX cannot use Cell Ranger aggregation; omit --aggregate.")
    return method


def soupx_inputs(outs):
    # These are the two GEX graph-clustering layouts supported by SoupX 1.6.2.
    modern = os.path.join(outs, "analysis", "clustering", "gene_expression_graphclust")
    cluster_dir = modern if os.path.isdir(modern) or not os.path.isdir(outs) else os.path.join(
        outs, "analysis", "clustering", "graphclust"
    )
    return [
        os.path.join(outs, matrix, name)
        for matrix in ("raw_feature_bc_matrix", "filtered_feature_bc_matrix")
        for name in MATRIX_FILES
    ] + [os.path.join(cluster_dir, "clusters.csv")]


def validate_soupx_import(sample_dir):
    missing = [p for p in soupx_inputs(os.path.join(sample_dir, "outs"))
               if not os.path.isfile(p)]
    if missing:
        raise ValueError("SoupX sample '{}': missing required input(s): {}".format(
            os.path.basename(os.path.normpath(sample_dir)), ", ".join(missing)
        ))
