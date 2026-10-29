"""Validation and Cell Ranger file contracts for optional ambient correction."""

from pathlib import Path


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
    outs = Path(outs)
    # These are the two GEX graph-clustering layouts supported by SoupX 1.6.2.
    modern = outs / "analysis" / "clustering" / "gene_expression_graphclust"
    # Expect the modern layout when Cell Ranger has not generated its outputs yet.
    if modern.is_dir() or not outs.is_dir():
        cluster_dir = modern
    else:
        cluster_dir = outs / "analysis" / "clustering" / "graphclust"
    return [
        str(outs / matrix / name)
        for matrix in ("raw_feature_bc_matrix", "filtered_feature_bc_matrix")
        for name in MATRIX_FILES
    ] + [str(cluster_dir / "clusters.csv")]


def validate_soupx_import(sample_dir):
    sample_dir = Path(sample_dir)
    missing = [p for p in soupx_inputs(sample_dir / "outs")
               if not Path(p).is_file()]
    if missing:
        raise ValueError("SoupX sample '{}': missing required input(s): {}".format(
            sample_dir.name, ", ".join(missing)
        ))
