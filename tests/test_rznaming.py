from rznaming import filter_name, parse_filter_name, PREFIX


def test_prefix():
    assert PREFIX == "FALCON_COLOR_"


def test_plain():
    assert filter_name("PVC Box") == "FALCON_COLOR_PVC Box"


def test_type():
    assert filter_name("Fixture", "600x1200 - 120") == "FALCON_COLOR_Fixture__600x1200 - 120"


def test_forbidden():
    # Review Focus 5: forbidden characters replaced, plus a short hash
    name = filter_name("Box: 2-way [20mm]", "T{1}")
    assert name.startswith("FALCON_COLOR_Box_ 2-way _20mm___T_1__")
    for ch in "\\:{}[]|;<>?`~":
        assert ch not in name


def test_sanitised_names_stay_unique():
    # final review #5
    assert filter_name("A[1]") != filter_name("A{1}")
    assert filter_name("X__Y") != filter_name("X", "Y")
    assert filter_name("A[1]") == filter_name("A[1]")


def test_family_and_type_names_stay_distinct():
    assert filter_name("A") != filter_name("A", "B")
    assert filter_name("A", "B") != filter_name("A", "C")


def test_parse():
    assert parse_filter_name("FALCON_COLOR_A__B") == ("A", "B")
    assert parse_filter_name("FALCON_COLOR_A") == ("A", None)
    assert parse_filter_name("Other") is None
