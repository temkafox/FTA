import auto_update


def test_ordering():
    vt = auto_update._version_tuple
    assert vt("1.2.0") > vt("1.1.0")
    assert vt("v1.10.0") > vt("v1.9.9")
    assert vt("1.1.0") == vt("v1.1.0")


def test_suffix_stripped():
    vt = auto_update._version_tuple
    assert vt("1.2.0-beta") == vt("1.2.0")


def test_garbage_is_lowest():
    vt = auto_update._version_tuple
    assert vt("garbage") == (0,)
    assert vt("garbage") < vt("0.0.1")
