"""Fitness checks on the reusable workflows: the deploy gate and the history depth cannot regress."""
from pathlib import Path

import yaml

WF = Path(__file__).resolve().parent.parent / ".github" / "workflows"


def load(name):
    doc = yaml.safe_load((WF / name).read_text(encoding="utf-8"))
    return doc, doc.get(True, doc.get("on"))  # PyYAML reads the key `on` as True


GATE = ("inputs.deploy", "github.event_name != 'pull_request'", "github.ref == 'refs/heads/main'",
        "!github.event.repository.private")


def test_pages_is_reusable_and_deploys_only_from_public_main():
    doc, on = load("pages.yml")
    assert set(on) == {"workflow_call"}
    deploy = doc["jobs"]["deploy"]
    assert deploy["needs"] == "build"
    for cond in GATE:
        assert cond in deploy["if"], cond
    assert "||" not in deploy["if"]
    upload = next(s for s in doc["jobs"]["build"]["steps"] if s.get("uses", "").startswith("actions/upload-pages-artifact"))
    assert upload["if"] == deploy["if"]


def test_build_job_cannot_write_pages():
    doc, _ = load("pages.yml")
    assert doc["permissions"] == {"contents": "read"}
    assert "permissions" not in doc["jobs"]["build"]


def test_checkouts_fetch_full_history():
    for name in ("pages.yml", "validate.yml"):
        doc, _ = load(name)
        for job in doc["jobs"].values():
            for step in job.get("steps", []):
                if step.get("uses", "").startswith("actions/checkout"):
                    assert step["with"]["fetch-depth"] == 0, name


def test_inputs_reach_shell_only_through_env():
    for name in ("pages.yml", "validate.yml"):
        doc, _ = load(name)
        for job in doc["jobs"].values():
            for step in job.get("steps", []):
                assert "${{" not in step.get("run", ""), f"{name}: {step.get('name')}"
