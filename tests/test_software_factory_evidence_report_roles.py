import importlib.util
from pathlib import Path


def load_report_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "software_factory_evidence_report.py"
    spec = importlib.util.spec_from_file_location("software_factory_evidence_report", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_reviewer_assignee_takes_precedence_over_pm_title_body_words():
    report = load_report_module()
    role = report.task_role(
        {
            "assignee": "metasoftwarefactoryreviewer",
            "title": "Reviewer: source gate for Phase 1 Software Factory PM report generator",
            "body": "Review the PM evidence report implementation and create PM remediation if needed.",
        },
        [],
    )
    assert role == "reviewer"


def test_run_profile_takes_precedence_over_incidental_pm_text_when_assignee_missing():
    report = load_report_module()
    role = report.task_role(
        {
            "title": "Source gate for Phase 1 Software Factory PM report generator",
            "body": "Review the PM evidence report implementation.",
        },
        [{"profile": "metasoftwarefactoryreviewer"}],
    )
    assert role == "reviewer"


def test_actual_pm_assignee_still_classifies_as_pm():
    report = load_report_module()
    role = report.task_role(
        {
            "assignee": "metasoftwarefactorypm",
            "title": "Decision gate: evidence timeline/reporting spec and source target",
            "body": "Create a task graph and source map for the PM-owned decision.",
        },
        [],
    )
    assert role == "pm"
