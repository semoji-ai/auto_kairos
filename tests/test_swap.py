import unicodedata
from scripts.swap_assets import swap_targets


def test_nfd_footage_name_matches_nfc_table_key():
    nfd = unicodedata.normalize("NFD", "세모지감정14_킥킥.mov")
    t = swap_targets([nfd, "other.mov"], {"세모지감정14_킥킥.mov": "/x/en.mov"})
    assert t == {nfd: "/x/en.mov"}
