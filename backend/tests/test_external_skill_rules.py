from __future__ import annotations

from pathlib import Path

from app.services.external_skill_rules import ExternalSkillRulesLoader


def test_external_skill_loader_extracts_numbered_rules(tmp_path: Path) -> None:
    skill_dir = tmp_path / "de-AI-writing"
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        "---\nname: de-AI-writing\n---\n"
        "## 1. 规则项\n"
        "规则一。\n"
        "规则二。",
        encoding="utf-8",
    )
    
    ref_dir = skill_dir / "references"
    ref_dir.mkdir(parents=True, exist_ok=True)
    ref_file = ref_dir / "style-base.md"
    ref_file.write_text("这是被引用的外部风格指南内容。", encoding="utf-8")

    loader = ExternalSkillRulesLoader(
        enabled=True,
        repo_root=tmp_path,
        mode="de-AI-writing",
        max_items=2,
    )
    suffix = loader.build_instruction_suffix()

    assert loader.has_rules() is True
    assert "规则一。" in suffix
    assert "规则二。" in suffix
    assert "name: de-AI-writing" not in suffix
    assert "这是被引用的外部风格指南内容。" in suffix


def test_external_skill_loader_handles_missing_repo(tmp_path: Path) -> None:
    loader = ExternalSkillRulesLoader(enabled=True, repo_root=tmp_path, mode="missing-mode")
    assert loader.has_rules() is False
    assert loader.build_instruction_suffix() == ""

