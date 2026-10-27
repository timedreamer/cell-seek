# cell-seek Development Environment Setup

Date: 2026-10-27

Prepared a local development environment for the optional SoupX integration in
cell-seek 3.4.2. Code is edited and checked on the Mac, pushed to the personal
GitHub fork, and pulled into a separate Biowulf checkout for final integration
testing. No SoupX implementation or full cell-seek workflow test was performed
during this setup.

## Locations and repositories

| Item | Location |
| --- | --- |
| Mac checkout | `/Users/huangj21/Projects/cell-seek` |
| Local pipeline entry point | `/Users/huangj21/Projects/cell-seek/cell-seek` |
| Local mamba environment | `/Users/huangj21/miniforge3/envs/cellseek-dev` |
| Personal fork (`origin`) | `https://github.com/timedreamer/cell-seek.git` |
| Official repository (`upstream` on the Mac) | `https://github.com/OpenOmics/cell-seek.git` |
| Development branch | `add_soupX`, tracking `origin/add_soupX` |
| Biowulf development checkout, confirmed by the user | `/data/huangj21/projects/cell-seek-dev` |
| Existing Biowulf production launcher | `/data/OpenOmics/prod/cell-seek/v3.4.2/cell-seek` |

Biowulf uses the personal fork as `origin`; adding `upstream` there was
intentionally skipped. The Mac already has `upstream` for fetching official
updates. Default development pushes from the Mac go to the personal fork.

## Recreate the local environment

Mamba was already available at `/Users/huangj21/miniforge3/bin/mamba`. No
Homebrew, administrator access, or installation into `base` was needed.
The final environment matches the Python and Snakemake versions reported from
the user's Biowulf session:

| Component | Verified local version |
| --- | --- |
| Python | **3.9.15** |
| Snakemake | **7.32.4**, supplied by `snakemake-minimal` |
| PuLP | **2.7.0**, compatible with the API used by this Snakemake release |
| pytest | **8.4.1** |
| GitHub CLI (`gh`) | **2.103.3** |

For a fresh installation where `cellseek-dev` does not yet exist, create the
final environment directly:

```bash
mamba create --name cellseek-dev \
    --override-channels --channel conda-forge --channel bioconda \
    python=3.9.15 snakemake-minimal=7.32.4 pulp=2.7.0 \
    pytest=8.4.1 gh=2.103.3 --yes

mamba activate cellseek-dev
python --version
snakemake --version
pytest --version
gh --version
python -c 'import pulp; print(pulp.__version__)'
```

These pins reproduce the primary tool versions; this is not a complete lock of
all transitive dependencies. Install future local development tools into this
environment while preserving the Python, Snakemake, and PuLP pins.

For commands that do not rely on an already activated terminal:

```bash
mamba run -n cellseek-dev python -B \
    /Users/huangj21/Projects/cell-seek/cell-seek --version
```

The repository's `python/3.8` module entry is separate from the launcher runtime.
The Biowulf session actually reported Python 3.9.15, so the local environment was
aligned with that version rather than changing the pipeline's module settings.

## GitHub and local checkout setup

Authenticated GitHub CLI as `timedreamer`, created the personal fork, retained
the existing local checkout and `add_soupX` branch, and published the branch to
the fork. To repeat authentication on a new machine:

```bash
mamba activate cellseek-dev
gh auth login --hostname github.com --git-protocol https --web
gh auth status
```

Complete the browser login as `timedreamer`. The fork already exists; it does
not need to be recreated. For a new local checkout, use the following only
when the destination directory does not already exist:

```bash
git clone --branch add_soupX \
    https://github.com/timedreamer/cell-seek.git \
    /Users/huangj21/Projects/cell-seek

cd /Users/huangj21/Projects/cell-seek
git remote add upstream https://github.com/OpenOmics/cell-seek.git
git config remote.pushDefault origin
git config branch.add_soupX.pushRemote origin
git remote -v
git status --short --branch
```

During the original setup, the existing official `origin` remote was renamed
to `upstream`, and the personal fork was added as the new `origin`; recloning
was unnecessary. The existing branch was published with
`git push --set-upstream origin add_soupX`.

## VS Code environment selection

Created `/Users/huangj21/Projects/cell-seek/.vscode/settings.json` with:

```json
{
    "python.defaultInterpreterPath": "/Users/huangj21/miniforge3/envs/cellseek-dev/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.terminal.activateEnvInCurrentTerminal": true
}
```

In VS Code, run **Python: Select Interpreter** from the Command Palette and
select that Python path once, especially if the folder already has another
interpreter selected. Close old terminals and open a new integrated terminal.
Confirm the selection with:

```bash
echo "$CONDA_DEFAULT_ENV"
which python
python --version
```

The expected environment is `cellseek-dev`, with Python 3.9.15 at the path
above. Personal editor settings are kept local by `.vscode/.gitignore`, which
contains `*`. Personal Codex instructions in the root `AGENTS.md` are also
untracked: `.git/info/exclude` contains `/AGENTS.md`. Reapply these local ignore
rules when recreating the checkout; they are not supplied by a clone.

## Biowulf checkout and compute-node environment

The user completed setup at `/data/huangj21/projects/cell-seek-dev`. To recreate
that checkout, run these commands on Biowulf only when the destination does not
already exist:

```bash
mkdir -p /data/huangj21/projects
git clone --branch add_soupX \
    https://github.com/timedreamer/cell-seek.git \
    /data/huangj21/projects/cell-seek-dev
```

For each interactive testing session, allocate a compute node and then load
the runtime modules:

```bash
sinteractive --cpus-per-task=2 --mem=8g --time=1:00:00

# Continue after the allocation starts on a compute node.
module purge
module load singularity snakemake

cd /data/huangj21/projects/cell-seek-dev
python3 --version
snakemake --version
./cell-seek --version
```

The user's reported Biowulf versions were Python **3.9.15**, Snakemake
**7.32.4**, Singularity **4.3.7**, and production cell-seek **3.4.2**.
Recheck module versions because unversioned module defaults can change.
The two-CPU, 8 GB, one-hour allocation is the starting point for setup and dry
runs; actual analysis jobs may require more resources.

## Routine development and testing cycle

1. Edit code locally in VS Code using `cellseek-dev` and run the appropriate
   lightweight tests.
2. Commit the intended changes on `add_soupX` and push to the personal fork.
3. In the Biowulf development checkout, inspect the working tree and pull the
   committed changes before testing:

   ```bash
   cd /data/huangj21/projects/cell-seek-dev
   git status --short --branch
   # With a clean working tree on add_soupX:
   git pull --ff-only origin add_soupX
   git rev-parse HEAD
   ```

4. Run the real cell-seek dry run and final integration tests on the allocated
   compute node, using this checkout's `./cell-seek`. The production launcher
   does not test edits in the development checkout.
5. Review the results, fix issues locally, and repeat as needed. Record the
   tested commit, inputs, configuration, commands, and material results.

Use fresh output directories for workflow changes: initialization copies
`workflow/`, `resources/`, and `config/` only if those destination directories
do not already exist. Updating the checkout does not refresh copied workflow
files in an old output directory.

## Verification completed and testing limits

- Verified the local versions listed above and successfully ran the local
  launcher with `python -B ./cell-seek --version`, which reported 3.4.2.
- Verified Snakemake parsing and job-graph construction with a temporary
  two-rule synthetic dry run. No analysis jobs were executed.
- The user reported completing the Biowulf checkout setup. No remote commands
  were executed by Codex.
- Local Snakemake can support focused workflow checks with suitable local
  inputs and configuration. It does not install Cell Ranger, R/Seurat, SoupX,
  Singularity, Slurm, or Biowulf reference data.
- `./cell-seek run --dry-run` still requires Singularity through the launcher.
  A complete pipeline command also needs `--input`, `--output`, `--pipeline`,
  and `--genome`, plus an appropriate Cell Ranger version where needed. The
  abbreviated dry-run command alone is not a complete test.
- No full cell-seek dry run, SoupX correction, or downstream Seurat integration
  test was completed during environment setup. Those require a selected test
  sample and final execution on Biowulf.
