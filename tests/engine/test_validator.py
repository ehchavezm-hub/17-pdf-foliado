from pdf_foliado.engine.validator import validate_file


def test_valid_pdf(pdf_1p):
    r = validate_file(pdf_1p)
    assert r.ok is True
    assert r.error is None


def test_zero_pages_rejected(pdf_0p):
    r = validate_file(pdf_0p)
    assert r.ok is False
    assert r.error is not None
    assert "0" in r.error or "página" in r.error.lower()


def test_encrypted_no_password(pdf_encrypted):
    r = validate_file(pdf_encrypted)
    assert r.ok is False
    assert r.error is not None
    assert "contraseña" in r.error.lower() or "password" in r.error.lower()


def test_encrypted_wrong_password(pdf_encrypted):
    r = validate_file(pdf_encrypted, password="wrong")
    assert r.ok is False


def test_encrypted_correct_password(pdf_encrypted):
    r = validate_file(pdf_encrypted, password="user123")
    assert r.ok is True


def test_signature_warning(pdf_signed):
    r = validate_file(pdf_signed)
    assert r.ok is True
    assert any("firma" in w.lower() for w in r.warnings)


def test_valid_has_no_warnings_for_normal_pdf(pdf_10p):
    r = validate_file(pdf_10p)
    assert r.ok is True
    assert r.warnings == []
