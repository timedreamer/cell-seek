# Optional SoupX implementation and local verification

Date: 2026-10-27. Branch: `add_soupX`. Base commit:
`3ce9b4289a9e8305f80693aba01f4ea7800b89c3`; implementation is uncommitted.
No commit, push, image publication, transfer, or remote execution was performed.
The existing development-environment guide edit was preserved.

## Implementation

The new `--ambient-rna-method {none,soupx}` setting defaults to `none`.
Older configurations without the key retain default processing. Validation
rejects non-GEX pipelines, unsupported methods, and every explicit aggregation
setting with SoupX, including `--aggregate none` for a single sample.

The enabled GEX DAG declares raw/filtered matrix files and graph clusters as
Cell Ranger products and SoupX inputs. Imported layouts are checked before DAG
construction; incomplete imports fail without scheduling Cell Ranger to repair
the source. Correction writes outside source directories. Each Seurat QC job
depends on its corrected matrix files, and integration still depends on all
sample QC RDS files. The GEX rules and integration script were inspected for
original-count bypasses: expression analysis uses those RDS files; the native
summary uses original Cell Ranger metrics as intended. Aggregation is rejected.

`workflow/scripts/soupx.R` uses stable feature IDs with the installed SoupX
1.6.2 loader, including its normal soup-profile estimation and input handling.
Repeated R-side file, annotation, cluster, count and output-location checks have
been removed. The workflow selects GEX and sets a separate SoupX output directory;
the script retains the contamination-estimate check.
Correction uses seed 1234 (updated on 2026-10-28), automatic estimation,
subtraction and integer rounding. The channel is labelled with the sample ID,
and the estimation plot is saved to `soupx_estimation.pdf` in the sample's
SoupX output directory. Estimation parameters are unchanged. The writer
preserves all annotations and filtered barcodes, including zero rows/columns.
After correction succeeds, files are written directly to the SoupX output
directory, replacing previous matrix files on reruns. Snakemake handles failed
jobs; there is no fallback path. QC algorithms and settings are unchanged; metadata and the
sample report identify the selected matrix source.

## Checks completed locally

On 2026-10-28, after the seed/plot update, all 21 focused Python tests passed
in 5.37 seconds, including the per-sample PDF output in enabled DAGs. The R
matrix/rerun checks and PDF-device cleanup on estimation failure passed, as did
`git diff --check`. Real-sample correction with the new seed was not rerun.

After the R-module transition, all 21 focused Python tests passed in 4.92 seconds.
The former SIF-cache test was replaced with a check that the parsed SoupX rule
uses the configured R module without an image configuration. The R matrix
contract/failure checks and script `--help` passed with the simplified function
and CLI, as did Python 3.9 syntax, container JSON and `git diff --check` checks.
No package installation or actual module execution was performed locally.
Biowulf R/4.4.0 compatibility remains unverified.

The following records the original integration checks and real-sample runs,
before this runtime transition and the seed/plot update. Those correction runs
used seed 12345 and were not repeated.

Environment: Python 3.9.15, Snakemake 7.32.4, PuLP 2.7.0; system R 4.6.1,
SoupX 1.6.2, Seurat 5.5.1, DropletUtils 1.32.1 and optparse 1.8.2.
The Python checks build the actual GEX workflow with synthetic file fixtures,
without enabling containers or modules. They do not execute processing jobs.

Run from `/Users/huangj21/Projects/cell-seek`:

```bash
/Users/huangj21/miniforge3/envs/cellseek-dev/bin/python -B -m pytest -q .tests/test_soupx.py
/usr/local/bin/Rscript .tests/soupx_contract.R
git diff --check
```

Before the R-module transition, all 21 Python tests passed; the R contract
checks, parsing checks and `git diff --check` also passed. The checks cover option/configuration validation,
missing imported files, local
SIF-cache selection, default and enabled two-sample DAGs for new and imported
Cell Ranger data, and the matrix round-trip/failure contract. The R checks cover
duplicate symbols, unchanged feature/barcode order, zeros, integer counts,
summary arithmetic, mixed-feature rejection, bad clusters, missing raw counts,
and automatic-estimation failure without successful outputs.

Both supplied datasets were inspected and corrected locally. Their reports
corroborate Cell Ranger 10.0.0 and mm10-2020-A. Both have 32,285 GEX features
and 40 duplicate symbols; feature IDs are unique. Graph-cluster files cover
all filtered barcodes in order.

| Sample / tissue | Cells | Input UMIs | Corrected UMIs | Removed UMIs | Estimated fraction |
| --- | ---: | ---: | ---: | ---: | ---: |
| 20150 / thalamus | 6,270 | 46,608,355 | 39,521,848 | 7,086,507 | 0.152 |
| 20151 / cortex | 7,383 | 51,451,929 | 47,695,885 | 3,756,044 | 0.073 |

Actual successful correction commands (outputs must be fresh when reproducing):

```bash
/usr/local/bin/Rscript workflow/scripts/soupx.R --outs .tests/soupx_local/20150/outs --output .tests/soupx_checks_20261027/20150_verified --sample 20150 --commit working-tree > .tests/soupx_checks_20261027/20150_verified.log 2>&1
/usr/local/bin/Rscript workflow/scripts/soupx.R --outs .tests/soupx_local/20151/outs --output .tests/soupx_checks_20261027/20151 --sample 20151 --commit working-tree > .tests/soupx_checks_20261027/20151.log 2>&1
/usr/local/bin/Rscript .tests/soupx_contract.R .tests/soupx_local/20150/outs .tests/soupx_checks_20261027/20150_verified
/usr/local/bin/Rscript .tests/soupx_contract.R .tests/soupx_local/20151/outs .tests/soupx_checks_20261027/20151
```

Source script SHA-256 for these historical correction runs:
`3ab31601ff8431c1f7a7064c2989c6ca181eb65f58ec9aa1d34006785d47111a`.
The first 20150 attempt was superseded by the successful `_verified` run.
Correction results and an independent round-trip check agree for both samples.
SoupX emitted its Matrix `giveCsparse` deprecation warning; logs retain it.
All 37 supplied source files match the SHA-256 manifest recorded before testing
at `.tests/soupx_checks_20261027/source_sha256.json`. Results, logs, matrices and
session information stay in ignored `.tests/` directories.

These are local correction/file-contract results. They do not establish
biological suitability, successful Seurat QC or multi-sample integration.

## Runtime and remaining verification

SoupX now runs with the configured `R/4.4.0` module. Before starting cell-seek,
the user installs compatible SoupX, DropletUtils and optparse packages in a
library R/4.4.0 normally searches; Seurat remains an existing GEX prerequisite.
There is no automatic installation, extra package preflight or library-path
override in the SoupX rule. Missing packages produce ordinary R errors.
The SoupX image recipe, image configuration and image CLI argument were removed.
Other workflow containers and the launcher Singularity requirement are unchanged.
Resource settings (2 CPUs, 32 GB, 4 hours) remain provisional until Linux measurement.
The existing CI's Snakemake 5.24.2 workflow was inspected and left unchanged;
it was not run and is not equivalent to these Snakemake 7.32.4 checks.

After authorized code synchronization and manual package installation, the user must run
the full workflow on a Biowulf compute node. The recorded development checkout
is `/data/huangj21/projects/cell-seek-dev`. `TEST_ROOT` below is an unresolved
user-selected path, not a literal working destination. Set it to an existing
writable directory before using these commands.

```bash
sinteractive --cpus-per-task=2 --mem=8g --time=1:00:00
# After allocation starts:
module purge
module load singularity snakemake
python --version
snakemake --version
cd /data/huangj21/projects/cell-seek-dev
git rev-parse HEAD
git status --short
```

Confirm Python 3.9.15, Snakemake 7.32.4, and the intended development commit.
Slurm submission enables `--use-envmodules`, which loads R/4.4.0 for SoupX.
For `--mode local`, first run `module load R/4.4.0` in the compute session.
The following complete dry-run command uses the reported genome and Cell Ranger
version. Use a separate fresh output and omit the ambient option for a baseline.

```bash
: "${TEST_ROOT:?Set TEST_ROOT to the integration output parent}"
test_output=$(mktemp -d "$TEST_ROOT/soupx-single.XXXXXX")
./cell-seek run \
    --input /data/NCBR/projects/NIAID-1314/cell-seek_output/20150 \
    --output "$test_output" --pipeline gex --genome mm10 --cellranger 10.0.0 \
    --ambient-rna-method soupx --mode slurm --dry-run
```

After a successful dry run, execute the same command without `--dry-run` from
an allocation sized for actual processing, or use the normal batch setup.
The 2-CPU/8-GB allocation above is for setup/dry runs. For multi-sample testing,
use a fresh output and pass both `20150` and `20151` sample parents after
`--input`. Verify job completion, summaries, unchanged source inputs, sample QC,
and that integrated RNA counts trace to corrected matrices after filtering and
cell renaming. Review ambient markers and tissue biology separately. Record
commit, generated configuration, R/package versions, commands and logs.
