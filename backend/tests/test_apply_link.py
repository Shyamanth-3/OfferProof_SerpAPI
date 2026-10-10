from app.checks import text_red_flags
from app.models import Ctx, Identifiers


def flags(t):
    return text_red_flags.detect(t)


def run(t):
    return text_red_flags.run(Ctx(t, None, None, None, Identifiers()))


def test_form_and_shortener_links_are_flagged():
    for url in ("https://forms.gle/kur4DXDUrHwXXbPT7", "https://docs.google.com/forms/d/e/abc/viewform",
                "forms.office.com/r/xyz", "https://bit.ly/3abcd", "http://tinyurl.com/x1"):
        assert "APPLY_VIA_FORM" in flags(f"Apply here: {url}"), url


def test_company_links_and_lookalike_words_are_not_flagged():
    assert "APPLY_VIA_FORM" not in flags("Apply at https://careers.infosys.com/job/123")
    assert "APPLY_VIA_FORM" not in flags("Fill in the form on our website: https://www.wipro.com/careers/form")


def test_negated_mention_is_ignored():
    assert "APPLY_VIA_FORM" not in flags("We never ask you to apply through forms.gle/ links.")


def test_one_form_link_warns_two_hard_flags_fail():
    assert run("Complete your application: https://forms.gle/abc").status == "warn"
    assert run("Complete your application: https://forms.gle/abc within 24 hours").status == "fail"


def test_finding_is_plain_english():
    f = run("Apply: https://forms.gle/abc").finding
    assert "generic form or shortened link" in f and "APPLY_VIA_FORM" not in f
