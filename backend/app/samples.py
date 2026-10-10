"""Demo offers. Served at /api/samples (frontend chips) and used by tests, fixtures and the eval seed."""

SAMPLES = {
    "SCAM_FEE": {
        "label": "Fee scam",
        "offer_text": "Congratulations! You are selected for Work From Home Data Entry Internship at Nexora Global Solutions without interview. Stipend ₹45,000/month. Pay ₹1,999 refundable registration fee to nexora.hr@okaxis and join our Telegram t.me/nexorahr within 24 hours. Limited seats.",
    },
    "IMPERSONATION": {
        "label": "Fake TCS offer",
        "offer_text": "Dear Candidate,\nGreetings from Tata Consultancy Services. You have been shortlisted for the position of Associate Software Engineer. To proceed, complete your document verification on WhatsApp wa.me/919876543210 today.\nRegards,\nTCS HR Team\nhr@tcs-careers-india.in",
        "company": "Tata Consultancy Services",
        "sender_email": "hr@tcs-careers-india.in",
    },
    "GENUINE_NEGATED_FEE": {
        "label": "Genuine (says no fee)",
        "offer_text": "Dear Candidate,\nGreetings from Wipro Limited. We are pleased to offer you a 6-month Software Engineering Internship with a stipend of ₹30,000 per month, after your interviews on campus. Please confirm your acceptance by replying to this email. We never charge any registration fee at any stage of hiring.\nRegards,\nCampus Hiring Team\ncampus.hr@wipro.com",
        "company": "Wipro Limited",
        "sender_email": "campus.hr@wipro.com",
    },
    "UNCLEAR_STARTUP": {
        "label": "Unclear startup",
        "offer_text": "Hi,\nWe liked your profile and would like to offer you a Marketing Intern role at Brightleaf Labs, a small startup based in Pune. The stipend is ₹15,000 per month for 3 months. Reply to this email if you are interested and we will share the joining date.\nThanks,\nAnita\nhr.brightleaf@gmail.com",
        "company": "Brightleaf Labs",
        "sender_email": "hr.brightleaf@gmail.com",
    },
    "GENUINE_BIG_BRAND": {
        "label": "Genuine big brand",
        "offer_text": "Dear Candidate,\nGreetings from Infosys Limited. Following your interviews, we are pleased to offer you the role of Systems Engineer Trainee. Your detailed offer letter and joining instructions are available on the Infosys candidate portal. Please do not share your credentials with anyone.\nRegards,\nInfosys Talent Acquisition\ncampus@infosys.com",
        "company": "Infosys Limited",
        "sender_email": "campus@infosys.com",
    },
}
