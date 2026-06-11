from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "douyin-favorites-to-articles"


def test_skill_has_required_layout():
    assert (SKILL / "SKILL.md").is_file()
    assert (SKILL / "agents" / "openai.yaml").is_file()
    assert (SKILL / "scripts" / "dfa_cli.py").is_file()
    assert (SKILL / "scripts" / "dfa" / "__init__.py").is_file()
    assert (SKILL / "references" / "article-format.md").is_file()
    assert (SKILL / "references" / "error-codes.md").is_file()
