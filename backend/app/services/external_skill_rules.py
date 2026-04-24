from __future__ import annotations

import re
from pathlib import Path
from threading import RLock


class ExternalSkillRulesLoader:
    def __init__(
        self,
        enabled: bool,
        repo_root: Path,
        mode: str = "de-AI-writing",
        max_items: int = 12,
    ):
        self.enabled = enabled
        self.repo_root = repo_root
        self.mode = mode
        self.max_items = max_items
        self._lock = RLock()
        self._source_file = ""
        self._compact_rules = ""
        self.reload()

    def reload(self) -> None:
        if not self.enabled:
            with self._lock:
                self._source_file = ""
                self._compact_rules = ""
            return

        skill_dir = self.repo_root / self.mode
        source_file = skill_dir / "SKILL.md"
        if not source_file.exists():
            with self._lock:
                self._source_file = ""
                self._compact_rules = ""
            return

        text = source_file.read_text(encoding="utf-8", errors="ignore")
        rules_text = self._extract_compact_rules(text, self.max_items)

        # 尝试读取引用的额外规则文件
        references_dir = skill_dir / "references"
        if references_dir.exists() and references_dir.is_dir():
            ref_texts = []
            for ref_file in sorted(references_dir.glob("*.md")):
                content = ref_file.read_text(encoding="utf-8", errors="ignore")
                ref_texts.append(f"\n\n### 【引用附件: {ref_file.name}】 ###\n{content}")
            if ref_texts:
                rules_text += "".join(ref_texts)

        with self._lock:
            self._source_file = str(source_file)
            self._compact_rules = rules_text

    def build_instruction_suffix(self) -> str:
        with self._lock:
            if not self._compact_rules:
                return ""
            source_file = self._source_file
            compact_rules = self._compact_rules

        return (
            "外部规则增强（来自 De-AI-Prompt-Enhancer-Writer-Booster-SKILL）:\n"
            f"来源: {source_file}\n"
            "执行要求: 保真改写优先，不增删核心事实，不输出说明性元话术。\n"
            f"{compact_rules}"
        )

    def has_rules(self) -> bool:
        with self._lock:
            return bool(self._compact_rules)

    @staticmethod
    def _extract_compact_rules(text: str, max_items: int) -> str:
        # 直接注入整个 SKILL.md 文档的正文部分（去除开头的 YAML frontmatter）
        # 匹配 --- ... --- 头部
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                # 剔除 header
                text = parts[2].strip()
        
        return text

    @staticmethod
    def _find_section_block(text: str, title: str) -> str:
        start = text.find(title)
        if start < 0:
            return ""
        next_heading = text.find("\n## ", start + len(title))
        if next_heading < 0:
            return text[start:]
        return text[start:next_heading]

    @staticmethod
    def _extract_numbered_items(block: str) -> list[str]:
        if not block:
            return []
        items: list[str] = []
        for line in block.splitlines():
            stripped = line.strip()
            if re.match(r"^\d+\.\s+", stripped):
                items.append(re.sub(r"^\d+\.\s*", "", stripped))
        return items

    @staticmethod
    def _extract_hard_bans(block: str) -> list[str]:
        if not block:
            return []
        items: list[str] = []
        for line in block.splitlines():
            stripped = line.strip()
            if stripped.startswith("- 禁用"):
                items.append(stripped.lstrip("- ").strip())
        return items

