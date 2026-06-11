from dfa.urls import normalize_source_url, video_id_from_url


def test_normalizes_tracking_query_and_fragment():
    source = "https://www.douyin.com/video/7412345678901234567?previous_page=web_code_link#x"
    assert normalize_source_url(source) == "https://www.douyin.com/video/7412345678901234567"


def test_extracts_numeric_video_id():
    source = "https://www.douyin.com/video/7412345678901234567"
    assert video_id_from_url(source) == "7412345678901234567"


def test_short_link_gets_stable_url_identity():
    source = "https://v.douyin.com/AbCdEf/"
    first = video_id_from_url(source)
    second = video_id_from_url(source)
    assert first == second
    assert first.startswith("url-")
    assert len(first) == 20


def test_rejects_non_douyin_hosts():
    try:
        normalize_source_url("https://example.com/video/1")
    except ValueError as error:
        assert str(error) == "仅支持 douyin.com 域名的链接"
    else:
        raise AssertionError("non-Douyin URL should be rejected")
