from app.extract import extract

BODY = "Dear Students,\nGreetings from the Program Operations Team.\nRegistrations are open."


def test_company_from_subject_line():
    assert extract("Wipro | Industry Skill Development & Internship Program Registration Open\n" + BODY).company == "Wipro"
    assert extract("Re: Tech Mahindra | Offer\n" + BODY).company == "Tech Mahindra"


def test_generic_subject_word_is_not_a_company():
    assert extract("Congratulations | You are selected\n" + BODY).company is None


def test_priority_subject_over_body_but_user_field_wins():
    assert extract("Wipro | Hello\nGreetings from Infosys Limited. Join us.").company == "Wipro"
    assert extract("Wipro | Hello\n" + BODY, company="Zoho").company == "Zoho"
