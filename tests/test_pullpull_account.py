from pullpull.account import (
    AccountVideo,
    YtDlpAccountEnumerator,
    enumerate_account,
    read_account_manifest,
    write_account_manifest,
)


class FakePlaylistRunner:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def extract_info(self, url, options):
        self.calls.append((url, options))
        return self.payload


def test_enumerate_account_normalizes_entries_to_video_refs():
    runner = FakePlaylistRunner(
        {
            "entries": [
                {
                    "id": "111",
                    "url": "https://www.douyin.com/video/111?previous_page=x",
                    "title": "第一条",
                    "uploader": "作者",
                    "upload_date": "20260618",
                },
                {
                    "id": "222",
                    "webpage_url": "https://www.douyin.com/video/222",
                    "title": "第二条",
                    "creator": "作者",
                },
            ]
        }
    )

    videos = enumerate_account("https://www.douyin.com/user/MS4wLjAB", runner=runner)

    assert videos == [
        AccountVideo(
            video_id="111",
            source_url="https://www.douyin.com/video/111",
            title="第一条",
            author="作者",
            published_at="20260618",
        ),
        AccountVideo(
            video_id="222",
            source_url="https://www.douyin.com/video/222",
            title="第二条",
            author="作者",
            published_at=None,
        ),
    ]
    assert runner.calls[0][1]["extract_flat"] == "in_playlist"
    assert runner.calls[0][1]["skip_download"] is True


def test_enumerate_account_deduplicates_entries():
    runner = FakePlaylistRunner(
        {
            "entries": [
                {"id": "111", "url": "https://www.douyin.com/video/111"},
                {"id": "111", "url": "https://www.douyin.com/video/111?x=1"},
            ]
        }
    )

    videos = enumerate_account("https://www.douyin.com/user/MS4wLjAB", runner=runner)

    assert [video.video_id for video in videos] == ["111"]


def test_enumerator_passes_browser_cookies():
    runner = FakePlaylistRunner({"entries": []})

    YtDlpAccountEnumerator(runner=runner).enumerate(
        "https://www.douyin.com/user/MS4wLjAB",
        cookies_from_browser="chrome",
    )

    assert runner.calls[0][1]["cookiesfrombrowser"] == ("chrome",)


def test_account_manifest_round_trip(tmp_path):
    path = tmp_path / "account-manifest.json"
    videos = [
        AccountVideo(
            video_id="111",
            source_url="https://www.douyin.com/video/111",
            title="第一条",
            author="作者",
            published_at="20260618",
        )
    ]

    write_account_manifest(
        path,
        videos,
        account_url="https://www.douyin.com/user/MS4wLjAB",
        account_name="作者",
        declared_count=2,
    )

    payload, loaded = read_account_manifest(path)
    assert payload["account_name"] == "作者"
    assert payload["declared_count"] == 2
    assert payload["accessible_count"] == 1
    assert loaded == videos
