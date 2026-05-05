from taskmajor.domains.profiles.models import ProfileManifest
from taskmajor.domains.profiles.prompt_loader import PromptLoader


def make_manifest(name="profile"):
    return ProfileManifest(name=name, version="1.0.0")


def make_profile_dir(tmp_path, prompts: dict[str, str], profile_name="profile"):
    profile_dir = tmp_path / profile_name
    prompts_dir = profile_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    for fname, content in prompts.items():
        (prompts_dir / fname).write_text(content, encoding="utf-8")
    return profile_dir


def test_load_prompts_from_directory(tmp_path):
    profile_dir = make_profile_dir(tmp_path, {"p1.md": "content1", "p2.md": "content2"})
    loader = PromptLoader()
    loader.load_from_profile(profile_dir, make_manifest())
    assert loader.get_prompt("p1") == "content1"
    assert loader.get_prompt("p2") == "content2"


def test_no_prompts_dir_is_silent(tmp_path):
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()
    loader = PromptLoader()
    loader.load_from_profile(profile_dir, make_manifest())
    assert loader.list_prompts() == []


def test_subdirectories_are_skipped(tmp_path):
    profile_dir = make_profile_dir(tmp_path, {"top.md": "top content"})
    subdir = profile_dir / "prompts" / "workflows"
    subdir.mkdir()
    (subdir / "nested.md").write_text("nested", encoding="utf-8")
    loader = PromptLoader()
    loader.load_from_profile(profile_dir, make_manifest())
    assert loader.list_prompts() == ["top"]
    assert loader.get_prompt("nested") is None


def test_last_loaded_profile_wins_on_name_collision(tmp_path):
    """Last loaded profile overwrites a same-named prompt (single-profile model)."""
    profileA = make_profile_dir(tmp_path, {"p.md": "A"}, profile_name="profileA")
    profileB = make_profile_dir(tmp_path, {"p.md": "B"}, profile_name="profileB")
    loader = PromptLoader()
    loader.load_from_profile(profileA, make_manifest(name="A"))
    loader.load_from_profile(profileB, make_manifest(name="B"))
    assert loader.get_prompt("p") == "B"
    assert loader.get_prompt_definition("p").source_profile == "B"


def test_get_prompt_returns_content(tmp_path):
    profile_dir = make_profile_dir(tmp_path, {"guide.md": "markdown content"})
    loader = PromptLoader()
    loader.load_from_profile(profile_dir, make_manifest())
    assert loader.get_prompt("guide") == "markdown content"


def test_get_prompt_missing_returns_none(tmp_path):
    loader = PromptLoader()
    assert loader.get_prompt("notfound") is None


def test_list_prompts_returns_all_names(tmp_path):
    profile_dir = make_profile_dir(tmp_path, {"a.md": "A", "b.md": "B", "c.md": "C"})
    loader = PromptLoader()
    loader.load_from_profile(profile_dir, make_manifest())
    assert set(loader.list_prompts()) == {"a", "b", "c"}
