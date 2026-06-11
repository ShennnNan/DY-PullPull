from dfa.paths import AppPaths


def test_initialize_creates_expected_directories(tmp_path):
    paths = AppPaths.from_root(tmp_path)
    paths.initialize()

    assert paths.database == tmp_path / "library.db"
    assert paths.articles.is_dir()
    assert paths.browser_profile.is_dir()
    assert paths.logs.is_dir()
    assert paths.temp.is_dir()


def test_default_root_uses_local_app_data(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    paths = AppPaths.default()

    assert paths.root == tmp_path / "DouyinFavoritesToArticles"
