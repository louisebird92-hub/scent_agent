from scent_finder.fragrance.tools import bands_under, clean, parse_pasted_list


def test_parse_fragrantica_lines():
    text = "1. Santal 33 by Le Labo for women and men\n• Diptyque – Tam Dao\nGypsy Water Eau de Parfum (2008)\n\n"
    assert parse_pasted_list(text) == ["Santal 33 Le Labo", "Diptyque Tam Dao", "Gypsy Water"]


def test_price_bands_under_200_are_budget_and_mid():
    assert bands_under(200) == ["budget", "mid"]
    assert bands_under(50) == ["budget"]  # never empty


def test_clean_drops_empty_but_keeps_inferred_flag():
    assert clean({"a": None, "b": [], "season_inferred": True, "name": "x"}) == {"name": "x", "season_inferred": True}


def test_parse_csv_upload_with_name_and_brand():
    text = "Name,Brand,Rating\nSantal 33,Le Labo,5\nTam Dao,Diptyque,\n"
    assert parse_pasted_list(text) == ["Santal 33 Le Labo", "Tam Dao Diptyque"]


def test_user_scoping_defaults_and_normalises():
    from scent_finder.fragrance import tools
    tools.set_user("Someone@Example.com")
    assert tools.current_user() == "someone@example.com"
