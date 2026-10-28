"""Focused option validation and real GEX DAG checks (no runtime execution)."""

import json
from pathlib import Path
import runpy
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.run import check_conditional_parameters, init, setup
from workflow.scripts.ambient import validate_ambient_options, validate_soupx_import


@pytest.mark.parametrize("pipeline", ["cite", "multi", "vdj", "atac", "multiome"])
def test_soupx_requires_gex(pipeline):
    with pytest.raises(ValueError, match="--pipeline gex"):
        validate_ambient_options({"pipeline": pipeline, "ambient_rna_method": "soupx"})


@pytest.mark.parametrize("aggregate", ["none", "mapped"])
def test_aggregation_conflict_even_for_one_sample(aggregate):
    with pytest.raises(ValueError, match="omit --aggregate"):
        validate_ambient_options({"pipeline": "gex", "ambient_rna_method": "soupx",
                                  "aggregate": aggregate, "samples": ["one"]})
    assert validate_ambient_options({"pipeline": "gex", "aggregate": aggregate}) == "none"


def test_invalid_method():
    with pytest.raises(ValueError, match="ambient_rna_method"):
        validate_ambient_options({"pipeline": "gex", "ambient_rna_method": "unknown"})


def test_missing_import_cannot_schedule_count(tmp_path):
    with pytest.raises(ValueError, match="SoupX sample 'capture'.*raw_feature_bc_matrix"):
        validate_soupx_import(str(tmp_path / "capture"))


def make_run(tmp_path, monkeypatch, method, imported=False):
    inputs = []
    for sample in ("one", "two"):
        if imported:
            parent = tmp_path / "inputs" / sample
            outs = parent / "outs"
            for matrix in ("raw_feature_bc_matrix", "filtered_feature_bc_matrix"):
                for name in ("matrix.mtx.gz", "features.tsv.gz", "barcodes.tsv.gz"):
                    path = outs / matrix / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.touch()
            path = outs / "analysis/clustering/graphclust/clusters.csv"
            path.parent.mkdir(parents=True)
            path.touch()
            (outs / "web_summary.html").touch()
            inputs.append(str(parent))
        else:
            for mate in ("R1", "R2"):
                path = tmp_path / (sample + "_S1_L001_" + mate + "_001.fastq.gz")
                path.touch()
                inputs.append(str(path))
    output = tmp_path / "run"
    argv = [str(ROOT / "cell-seek"), "run", "--input"] + inputs + [
        "--output", str(output), "--pipeline", "gex", "--genome", "mm10",
        "--cellranger", "10.0.0"]
    if method is not None:
        argv += ["--ambient-rna-method", method]
    monkeypatch.setattr(sys, "argv", argv)
    cli = runpy.run_path(str(ROOT / "cell-seek"))
    args = cli["parsed_arguments"]("cell-seek", "test")
    files = init(str(ROOT), str(output), links=args.input, sym_link=False)
    config = setup(args, files, str(ROOT), str(output))
    if method is None:
        del config["options"]["ambient_rna_method"]  # Older generated configs.
    (output / "config.json").write_text(json.dumps(config))
    return output, config


def snakemake(output, *args):
    result = subprocess.run(
        [str(Path(sys.executable).with_name("snakemake")), "-s", "workflow/Snakefile",
         "--cores", "1"] + list(args), cwd=output, text=True, capture_output=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout + result.stderr


@pytest.mark.parametrize("method", [None, "none", "soupx"])
@pytest.mark.parametrize("imported", [False, True])
def test_two_sample_gex_dag(tmp_path, monkeypatch, method, imported):
    output, config = make_run(tmp_path, monkeypatch, method, imported)
    dryrun = snakemake(output, "-n", "-p", "all")
    dag = snakemake(output, "--dag", "all")
    if method == "soupx":
        assert dryrun.count("rule soupx:") == 2
        for sample in ("one", "two"):
            assert "--datapath " + str(output / "soupx" / sample / "filtered_feature_bc_matrix") in dryrun
            assert str(output / "soupx" / sample / "soupx_summary.tsv") in dryrun
            assert str(output / "soupx" / sample / "soupx_estimation.pdf") in dryrun
        # Each QC node depends on its correction; integration depends on both QC nodes.
        import re
        nodes = dict(re.findall(r'(\d+)\[label = "([^"\\]+)', dag))
        edges = re.findall(r'(\d+) -> (\d+)', dag)
        qc = [node for node, label in nodes.items() if label == "seuratQC"]
        assert len(qc) == 2
        for node in qc:
            assert any(b == node and nodes[a] == "soupx" for a, b in edges)
        if not imported:
            correction = [node for node, label in nodes.items() if label == "soupx"]
            assert all(any(b == node and nodes[a] == "count" for a, b in edges)
                       for node in correction)
        integration = next(node for node, label in nodes.items() if label == "seuratIntegrate")
        assert all((node, integration) in edges for node in qc)
    else:
        assert "rule soupx:" not in dryrun
        assert "soupx" not in dag
        for sample in ("one", "two"):
            assert "--datapath " + str(output / sample / "outs/filtered_feature_bc_matrix") in dryrun
    assert ("rule count:" not in dryrun) == imported


@pytest.mark.parametrize("options, message", [
    ({"ambient_rna_method": "invalid"}, "ambient_rna_method"),
    ({"ambient_rna_method": "soupx", "pipeline": "cite"}, "--pipeline gex"),
    ({"ambient_rna_method": "soupx", "aggregate": "none"}, "omit --aggregate"),
    ({"ambient_rna_method": "soupx", "aggregate": "mapped"}, "omit --aggregate"),
])
def test_direct_config_rejected(tmp_path, monkeypatch, options, message):
    output, config = make_run(tmp_path, monkeypatch, "none")
    config["options"].update(options)
    with pytest.raises(SystemExit):
        check_conditional_parameters(config)
    (output / "config.json").write_text(json.dumps(config))
    result = subprocess.run([str(Path(sys.executable).with_name("snakemake")),
                             "-s", "workflow/Snakefile", "-n", "all"],
                            cwd=output, text=True, capture_output=True)
    assert result.returncode != 0
    assert message in result.stdout + result.stderr


def test_soupx_uses_configured_r_module(tmp_path, monkeypatch):
    from snakemake.workflow import Workflow

    output, config = make_run(tmp_path, monkeypatch, "soupx", imported=True)
    assert "soupx" not in config["images"]
    monkeypatch.chdir(output)
    workflow = Workflow(snakefile="workflow/Snakefile")
    workflow.include("workflow/Snakefile")
    rule = workflow.get_rule("soupx")
    assert rule.env_modules.names == (config["tools"]["rversion"],)
    assert rule.container_img is None
    assert "--image" not in rule.shellcmd


def test_incomplete_import_fails_before_dag(tmp_path, monkeypatch):
    output, config = make_run(tmp_path, monkeypatch, "soupx", imported=True)
    (Path(config["options"]["input"][0]) / "outs/raw_feature_bc_matrix/matrix.mtx.gz").unlink()
    result = subprocess.run([str(Path(sys.executable).with_name("snakemake")),
                             "-s", "workflow/Snakefile", "-n", "all"],
                            cwd=output, text=True, capture_output=True)
    assert result.returncode != 0
    assert "SoupX sample 'one': missing required input" in result.stdout + result.stderr
