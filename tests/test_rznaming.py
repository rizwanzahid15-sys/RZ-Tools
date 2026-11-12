from rznaming import filter_name, parse_filter_name, PREFIX


def test_prefix():
    assert PREFIX == "RZ_COLOR_"


def test_plain():
    assert filter_name("PVC Box") == "RZ_COLOR_PVC Box"


def test_type():
    assert filter_name("Fixture", "600x1200 - 120") == "RZ_COLOR_Fixture__600x1200 - 120"


def test_forbidden():
    # Review Focus 5
    assert filter_name("Box: 2-way [20mm]", "T{1}") == "RZ_COLOR_Box_ 2-way _20mm___T_1_"
    assert filter_name("a\\b|c;d<e>f?g`h~i") == "RZ_COLOR_a_b_c_d_e_f_g_h_i"


def test_family_and_type_names_stay_distinct():
    assert filter_name("A") != filter_name("A", "B")
    assert filter_name("A", "B") != filter_name("A", "C")


def test_parse():
    assert parse_filter_name("RZ_COLOR_A__B") == ("A", "B")
    assert parse_filter_name("RZ_COLOR_A") == ("A", None)
    assert parse_filter_name("Other") is None
