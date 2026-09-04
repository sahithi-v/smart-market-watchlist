from app.auth import hash_password, verify_password


def test_correct_password_verifies():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed) is True


def test_wrong_password_fails():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("wrong password", hashed) is False


def test_same_password_hashes_differently_each_time():
    a = hash_password("same password")
    b = hash_password("same password")
    assert a != b
    assert verify_password("same password", a) is True
    assert verify_password("same password", b) is True