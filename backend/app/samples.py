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


# ---- journey samples (served by /api/samples with kind="journey"; kept apart from SAMPLES so quick-check
# tests, fixtures and the eval seed keep iterating only quick-check offers) ----
JOURNEY_SAMPLES = {
    "J1_CLONED_LISTING": {
        "kind": "journey",
        "label": "Cloned listing",
        "source": "synthetic",
        "journey": {
            "company": "Infosys Limited",
            "listing": {
                "url": "https://careers-infosys.in/jobs/associate-software-engineer",
                "text": "Infosys Limited is hiring an Associate Software Engineer in Bengaluru. Stipend ₹20,000 per month. Apply after an online assessment and a technical interview.",
            },
            "recruiter": {"name": "Rohit Verma", "email": "infosys.hr.rohit@gmail.com", "phone": "9000000001", "channel": "telegram"},
            "interview": {"format": "chat_only", "asked_to_pay": True, "asked_for_documents_before_offer": True},
            "offer_text": "Greetings from Infosys Limited. You are selected as Data Entry Executive in Noida. Stipend ₹40,000 per month. Pay ₹1,500 refundable registration fee to infosys.hr@okaxis and send your Aadhaar copy on Telegram t.me/infosyshr today.",
        },
    },
    # Synthetic: every text here is ours. A real-listing swap was tried on 2026-10-10: Google Jobs results for Infosys
    # ("Infosys Systems Engineer", India) were real, but every apply link was a third-party aggregator (jobsnet.in,
    # niyukjobs.ai, yohire.in, campusdrive.in, fresherjobinfo.in), not infosys.com or a known job board, so the tool
    # rightly flags them as "not the company's site" and they can't illustrate a clean journey. A second query timed out.
    "J2_GENUINE_JOURNEY": {
        "kind": "journey",
        "label": "Genuine journey",
        "source": "synthetic",
        "journey": {
            "company": "Infosys Limited",
            "listing": {
                "url": "https://www.infosys.com/careers/",
                "text": "Infosys Limited is hiring a Systems Engineer in Bengaluru. Stipend ₹30,000 per month during training. Selection is through an online assessment and interviews.",
            },
            "recruiter": {"name": "Campus Hiring Team", "email": "campus@infosys.com", "channel": "email"},
            "interview": {"format": "official_portal_or_video", "asked_to_pay": False, "asked_for_documents_before_offer": False},
            "offer_text": "Dear Candidate, Greetings from Infosys Limited. Following your interviews, we are pleased to offer you the role of Systems Engineer in Bengaluru with a stipend of ₹30,000 per month. Your detailed offer letter and joining instructions are on the Infosys candidate portal. Please do not share your credentials with anyone.",
        },
    },
}
