from sg.asrnorm import tokens


def test_cjk_tokens_simplify_and_drop_punctuation():
    assert tokens("索爾在洛杉磯，看到FedMart。", cjk=True) == list("索尔在洛杉矶看到") + ["fedmart"]


def test_latin_tokens_unchanged_for_english():
    assert tokens("Costco opened, in 1998!", cjk=False) == ["costco", "opened", "in", "1998"]
