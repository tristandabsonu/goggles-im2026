#!/usr/bin/env python3
"""Generate six synthetic NAIDOC application test documents in Markdown.

The supplied sample application PDF remains the canonical source for the form
wording. Its complete extracted text is included in every generated document,
followed by a completed response schedule and small synthetic attachment stubs.
"""

from __future__ import annotations

import copy
import re
import subprocess
from pathlib import Path

NAIDOC_ROOT = Path(__file__).resolve().parents[1]
SOURCE_FORM = NAIDOC_ROOT / "documents" / "NAIDOC 2026 - Sample Application Form.pdf"
TEST_CASES_DIR = NAIDOC_ROOT / "test-cases"
MARKDOWN_DIR = TEST_CASES_DIR / "source"
WRITER_SMOKE_PATH = TEST_CASES_DIR / "writer-smoke-test.md"


def extract_form_text() -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", str(SOURCE_FORM), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    text = result.stdout.replace("\r\n", "\n").replace("\f", "\n\n")
    text = text.replace("☐", "[ ]")
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return normalise_form_text(text)


# The sample form is a fixed document, so its section headings are curated
# rather than guessed. Level 2 marks the form's main sections, level 3 its
# sub-sections; promoting them keeps headings from merging into the paragraph
# that follows and gives the assessment engine a real heading hierarchy.
HEADING_LEVELS = {
    "2026 NAIDOC Local Grants Opportunity": 3,
    "Application Information": 2,
    "Grant Opportunity Administration": 3,
    "Closing Date/Time": 3,
    "Making Sure Your Application Has Saved": 3,
    "Grant Opportunity Documents": 3,
    "Application Help": 3,
    "Attachment Limits": 3,
    "Submitting an application from": 3,
    "National Relay Service (NRS)": 3,
    "Australian Tax Office (ATO) Reporting": 3,
    "Privacy": 3,
    "Use of Information": 2,
    "Eligibility Requirement": 2,
    "Applicant Contacts": 2,
    "Authorised Contact One": 3,
    "Authorised Contact Two": 3,
    "Existing Grant Recipient": 2,
    "Governance": 2,
    "Activity/Event Details": 2,
    "Delivery Location": 3,
    "Financials": 2,
    "Summary": 3,
    "Additional Information": 2,
    "Attachments": 2,
    "Partnership and Sole Trader Letters of Support": 3,
    "Non-Indigenous Applicants": 3,
    "Assessment Criterion Evidence of Support": 3,
    "Declaration": 2,
    "Program Feedback": 2,
}


def normalise_form_text(text: str) -> str:
    """Convert the pdftotext layout dump into cleanly structured Markdown.

    Dedents every line so pdftotext's centring never becomes a Markdown code
    block, converts bullet glyphs (with their indented continuation lines)
    into real list items, and promotes the form's known section headings.
    """
    lines = text.split("\n")
    out: list[str] = []
    in_list = False
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        if stripped.startswith("•"):
            item = stripped.lstrip("•").strip()
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                nxt_stripped = nxt.strip()
                if (
                    not nxt_stripped
                    or nxt_stripped.startswith("•")
                    or not nxt[:1].isspace()
                ):
                    break
                item = f"{item} {nxt_stripped}"
                j += 1
            if out and out[-1].strip() and not in_list:
                out.append("")
            out.append(f"- {item}")
            in_list = True
            i = j
            continue

        if in_list and stripped:
            out.append("")
        in_list = False

        if stripped in HEADING_LEVELS:
            if out and out[-1].strip():
                out.append("")
            out.append(f"{'#' * HEADING_LEVELS[stripped]} {stripped}")
            out.append("")
            i += 1
            continue

        out.append(stripped)
        i += 1

    result = "\n".join(out)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


BASE = {
    "state": "WA",
    "postcode": "6000",
    "entity_type": "Incorporated association",
    "entity_document": "Attachment B - synthetic certificate of incorporation",
    "stream": "Stream Two - Small-scale (up to $10,000)",
    "start_date": "06/07/2026",
    "end_date": "06/07/2026",
    "service_area": "Perth",
    "attendance": "150",
    "first_nations_profile": (
        "The applicant identifies as a First Nations-controlled organisation but is not "
        "registered with ORIC or Supply Nation."
    ),
    "membership": "75",
    "board": "75",
    "management": "75",
    "employees": "80",
    "criterion": "Not applicable - Stream Two selected.",
    "detailed_cocontributions": "Not applicable - detailed table only appears for Stream Three.",
    "non_indigenous_support": (
        "Not applicable - applicant identifies as a First Nations-controlled organisation."
    ),
    "criterion_evidence": "No optional assessment-criterion evidence attached.",
    "extra_attachments": [],
    "bank_attachment": True,
}


SCENARIOS = [
    {
        **BASE,
        "id": "01",
        "org": "Red Sand Community Arts Association Inc",
        "business_name": "Red Sand Community Arts",
        "abn": "11 111 111 101 (synthetic test value)",
        "state": "WA",
        "postcode": "6530",
        "title": "Geraldton Community Storytelling Dance and Art Day",
        "description": (
            "Red Sand Community Arts Association will hold a free community day in Geraldton "
            "on 11 July 2026. Local First Nations cultural practitioners will lead storytelling, "
            "dance and visual-art activities that share local histories and celebrate the skills "
            "and achievements of First Nations artists. Families will rotate through facilitated "
            "workshops before a public performance and community reflection. The activity was "
            "developed with the association's First Nations-controlled committee and will increase "
            "community participation in cultural expression. Each participant will also receive a "
            "NAIDOC T-shirt, and branded banners and social-media promotion will advertise the day."
        ),
        "start_date": "11/07/2026",
        "end_date": "11/07/2026",
        "service_area": "Geraldton",
        "location_name": "Geraldton Community Hall (synthetic venue)",
        "address": "1 Example Road, Geraldton WA 6530",
        "email": "admin@redsandarts.example.com",
        "contact_one": {
            "title": "Ms",
            "first_name": "Leah",
            "last_name": "Winters",
            "position": "Employee",
            "position_title": "Program Coordinator",
            "telephone": "08 5550 1837",
            "mobile": "0491 570 006",
            "email": "leah.winters@redsandarts.example.com",
        },
        "contact_two": {
            "title": "Mr",
            "first_name": "Tom",
            "last_name": "Garvan",
            "position": "Board member",
            "position_title": "Secretary",
            "telephone": "08 5550 1838",
            "mobile": "0491 570 156",
            "email": "tom.garvan@redsandarts.example.com",
        },
        "cocontribution": (
            "[X] Volunteer time; [X] donations\nThirty volunteer hours are valued at $1,600, "
            "and refreshments valued at $700 will be donated."
        ),
        "grant_amount": 8800,
        "attendance": "220",
        "budget": [
            ("Welcome to Country and cultural performances", 3200),
            ("First Nations artist-led workshops", 2400),
            ("Venue and event equipment hire", 1400),
            ("NAIDOC T-shirts for participants", 1000),
            ("Branded banners and social-media promotion", 800),
        ],
    },
    {
        **BASE,
        "id": "02",
        "org": "Harbour Lights Community Association Inc",
        "business_name": "Harbour Lights Community Association",
        "abn": "22 222 222 202 (synthetic test value)",
        "state": "NSW",
        "postcode": "2300",
        "title": "Newcastle Elders Storytelling and Weaving Afternoon",
        "description": (
            "Harbour Lights Community Association will hold a free afternoon gathering in "
            "Newcastle on 18 July 2026. First Nations cultural practitioners will share stories "
            "with families, lead introductory weaving activities and facilitate a community "
            "conversation about local histories and cultural continuity. The association's "
            "First Nations-controlled committee shaped the program and volunteers will welcome "
            "participants and assist with accessibility. The activity supports cultural expression, "
            "intergenerational engagement and broader understanding of First Nations cultures."
        ),
        "start_date": "18/07/2026",
        "end_date": "18/07/2026",
        "service_area": "Newcastle",
        "location_name": "Newcastle Community Rooms (synthetic venue)",
        "address": "2 Example Street, Newcastle NSW 2300",
        "email": "admin@harbourlights.example.com",
        "contact_one": {
            "title": "Mr",
            "first_name": "Daniel",
            "last_name": "Reyes",
            "position": "Employee",
            "position_title": "Community Programs Coordinator",
            "telephone": "02 5550 2214",
            "mobile": "0491 570 157",
            "email": "daniel.reyes@harbourlights.example.com",
        },
        "contact_two": {
            "title": "Ms",
            "first_name": "Margaret",
            "last_name": "Boyle",
            "position": "Board member",
            "position_title": "Treasurer",
            "telephone": "02 5550 2215",
            "mobile": "0491 570 158",
            "email": "margaret.boyle@harbourlights.example.com",
        },
        "cocontribution": (
            "[X] Volunteer time; [X] venue and equipment hire\nVolunteer support is valued at "
            "$1,200 and donated venue use at $800."
        ),
        "grant_amount": 9000,
        "attendance": "140",
        "budget": [
            ("Event delivery", 5500),
            ("Materials and supplies", 2500),
            ("Other", 1000),
        ],
    },
    {
        **BASE,
        "id": "03",
        "org": "Banksia Coast Independent Primary School Ltd",
        "business_name": "Banksia Coast Primary School",
        "abn": "33 333 333 303 (synthetic test value)",
        "state": "WA",
        "postcode": "6210",
        "entity_type": "Company incorporated in Australia; single educational institution",
        "entity_document": (
            "Attachment B - synthetic company registration and educational institution evidence"
        ),
        "title": "Banksia Coast Primary School Cultural Learning Day Mandurah",
        "description": (
            "Banksia Coast Independent Primary School will hold a free cultural learning day "
            "for its own students and families in Mandurah on 24 July 2026. Confirmed First Nations "
            "cultural presenters will lead storytelling, dance and cultural-learning sessions that "
            "celebrate First Nations histories, cultures and achievements. The activity is solely for "
            "this one school. No other educational institutions are involved, and the school has not "
            "sought or received prior approval to apply under Stream Two."
        ),
        "stream": "Stream Two - Small-scale (up to $10,000)",
        "start_date": "24/07/2026",
        "end_date": "24/07/2026",
        "service_area": "Mandurah",
        "location_name": "Banksia Coast Primary School (synthetic institution)",
        "address": "3 Example Avenue, Mandurah WA 6210",
        "email": "admin@banksiacoastps.example.com",
        "contact_one": {
            "title": "Ms",
            "first_name": "Karen",
            "last_name": "Dwyer",
            "position": "Employee",
            "position_title": "Principal",
            "telephone": "08 5550 3406",
            "mobile": "0491 570 159",
            "email": "karen.dwyer@banksiacoastps.example.com",
        },
        "contact_two": {
            "title": "Mr",
            "first_name": "Sanjay",
            "last_name": "Rao",
            "position": "Board member",
            "position_title": "School Board Chair",
            "telephone": "08 5550 3407",
            "mobile": "0491 570 110",
            "email": "sanjay.rao@banksiacoastps.example.com",
        },
        "cocontribution": (
            "[X] Volunteer time; [X] venue and equipment hire\nSchool staff time and use of the "
            "school grounds are valued at $2,500."
        ),
        "grant_amount": 6000,
        "attendance": "180",
        "budget": [
            ("First Nations cultural presenters", 3000),
            ("First Nations dance performance", 2000),
            ("Welcome to Country", 1000),
        ],
        "first_nations_profile": "Not applicable - applicant is an educational institution.",
        "membership": "Not applicable - educational institution.",
        "board": "Not applicable - educational institution.",
        "management": "Not applicable - educational institution.",
        "employees": "60",
        "non_indigenous_support": (
            "Attachment D - synthetic letter confirming local First Nations community support."
        ),
        "extra_attachments": [
            (
                "Attachment D - Synthetic local First Nations community support letter",
                "Confirms community support for the school's proposed cultural learning day.",
            )
        ],
    },
    {
        **BASE,
        "id": "04",
        "org": "Desert River Cultural Network Inc",
        "business_name": "Desert River Cultural Network",
        "abn": "44 444 444 404 (synthetic test value)",
        "state": "NT",
        "postcode": "0870",
        "title": "Alice Springs Regional Cultural Showcase",
        "description": (
            "Desert River Cultural Network will deliver a free two-day cultural showcase in "
            "Alice Springs on 8 and 9 August 2026. The event will feature First Nations dance and "
            "music performances, artist-led workshops, storytelling sessions and a bush-tucker "
            "cooking demonstration. The program was selected by the network's First Nations-controlled "
            "committee following community meetings. It will provide paid opportunities for cultural "
            "practitioners, support intergenerational sharing and invite the wider community to learn "
            "about and celebrate First Nations histories, cultures and achievements."
        ),
        "stream": "Stream Three - Large-scale (more than $10,000 and up to $25,000)",
        "start_date": "08/08/2026",
        "end_date": "09/08/2026",
        "service_area": "Alice Springs",
        "location_name": "Alice Springs Community Event Ground (synthetic venue)",
        "address": "4 Example Drive, Alice Springs NT 0870",
        "email": "admin@desertriver.example.com",
        "contact_one": {
            "title": "Mr",
            "first_name": "Callum",
            "last_name": "Reid",
            "position": "Employee",
            "position_title": "Events Manager",
            "telephone": "08 5550 4188",
            "mobile": "0491 570 313",
            "email": "callum.reid@desertriver.example.com",
        },
        "contact_two": {
            "title": "Ms",
            "first_name": "Gloria",
            "last_name": "Mendes",
            "position": "Board member",
            "position_title": "Chairperson",
            "telephone": "08 5550 4189",
            "mobile": "0491 570 737",
            "email": "gloria.mendes@desertriver.example.com",
        },
        "cocontribution": (
            "[X] Volunteer time; [X] venue and equipment hire; [X] donations\nSee the detailed "
            "co-contribution breakdown."
        ),
        "grant_amount": 20500,
        "attendance": "600",
        "budget": [
            ("First Nations cultural performers", 7000),
            ("First Nations artist workshop facilitation", 5000),
            ("Venue staging and PA hire", 5000),
            ("Event first-aid and safety services", 2000),
            ("Bush-tucker cooking demonstration supplies", 1500),
        ],
        "criterion": (
            "Our organisation has delivered community events before and has staff and volunteers "
            "available. We believe the event offers value and will benefit the community. Risks "
            "will be managed through our usual processes."
        ),
        "detailed_cocontributions": [
            ("Local council venue support", 4000, "Yes", "Yes"),
            ("Volunteer time", 3000, "Yes", "Yes"),
            ("Community business catering donation", 1500, "Yes", "Yes"),
        ],
    },
    {
        **BASE,
        "id": "05",
        "org": "Southern Coast Cultural Association Inc",
        "business_name": "Southern Coast Cultural Association",
        "abn": "55 555 555 505 (synthetic test value)",
        "state": "TAS",
        "postcode": "7000",
        "title": "Hobart Elders and Youth Storytelling Day",
        "description": (
            "Southern Coast Cultural Association will hold a free Elders and youth storytelling "
            "day in Hobart on 15 August 2026. First Nations cultural practitioners will facilitate "
            "storytelling, creative activities and small-group discussions that support respectful "
            "intergenerational learning. The association's First Nations-controlled committee has "
            "developed the program with local participants. The activity celebrates First Nations "
            "histories and achievements, strengthens cultural expression and promotes broader "
            "community understanding."
        ),
        "start_date": "15/08/2026",
        "end_date": "15/08/2026",
        "service_area": "Hobart",
        "location_name": "Hobart Community Centre (synthetic venue)",
        "address": "5 Example Lane, Hobart TAS 7000",
        "email": "admin@southerncoastcultural.example.com",
        "contact_one": {
            "title": "Ms",
            "first_name": "Erin",
            "last_name": "Callaghan",
            "position": "Employee",
            "position_title": "Program Coordinator",
            "telephone": "03 5550 5522",
            "mobile": "0491 571 266",
            "email": "erin.callaghan@southerncoastcultural.example.com",
        },
        "contact_two": {
            "title": "Mr",
            "first_name": "Nathan",
            "last_name": "Pryor",
            "position": "Board member",
            "position_title": "Secretary",
            "telephone": "03 5550 5523",
            "mobile": "0491 571 491",
            "email": "nathan.pryor@southerncoastcultural.example.com",
        },
        "cocontribution": (
            "[X] Volunteer time; [X] venue and equipment hire\nVolunteer time is valued at $1,400 "
            "and donated venue use at $900."
        ),
        "grant_amount": 7200,
        "attendance": "120",
        "budget": [
            ("First Nations cultural performers", 2500),
            ("Venue and event equipment hire", 1700),
            ("Storytelling facilitators", 1800),
            ("Participant activity materials", 1200),
        ],
        "bank_attachment": False,
    },
    {
        **BASE,
        "id": "06",
        "org": "River Plains Community Association Inc",
        "business_name": "River Plains Community Association",
        "abn": "66 666 666 606 (synthetic test value)",
        "state": "NSW",
        "postcode": "2830",
        "title": "Dubbo Family Cultural Arts and Storytelling Day",
        "description": (
            "River Plains Community Association will hold a free family cultural arts and storytelling "
            "day in Dubbo on 22 August 2026. Two confirmed First Nations cultural facilitators will each "
            "lead three storytelling and cultural-learning sessions at $500 per session, totalling $3,000. "
            "Other First Nations artists will deliver weaving and visual-art workshops, and a cooking "
            "demonstrator will share knowledge through a bush-tucker activity. The First Nations-controlled "
            "committee designed the program to strengthen cultural expression, enable intergenerational "
            "participation and promote respectful community understanding of First Nations histories, "
            "cultures and achievements."
        ),
        "start_date": "22/08/2026",
        "end_date": "22/08/2026",
        "service_area": "Dubbo",
        "location_name": "Dubbo Community Arts Hall (synthetic venue)",
        "address": "6 Example Circuit, Dubbo NSW 2830",
        "email": "admin@riverplains.example.com",
        "contact_one": {
            "title": "Mx",
            "first_name": "Jordan",
            "last_name": "Hale",
            "position": "Employee",
            "position_title": "Community Events Coordinator",
            "telephone": "02 5550 6941",
            "mobile": "0491 571 804",
            "email": "jordan.hale@riverplains.example.com",
        },
        "contact_two": {
            "title": "Ms",
            "first_name": "Paula",
            "last_name": "Whitfield",
            "position": "Board member",
            "position_title": "Chairperson",
            "telephone": "02 5550 6942",
            "mobile": "0491 572 549",
            "email": "paula.whitfield@riverplains.example.com",
        },
        "cocontribution": (
            "[X] Volunteer time; [X] T-shirts; [X] donations\nVolunteer time is valued at $1,800.\n"
            "A local business will donate NAIDOC T-shirts for participants, valued at $1,000.\n"
            "No grant funding is requested for the T-shirts."
        ),
        "grant_amount": 9400,
        "attendance": "260",
        "budget": [
            ("Cultural facilitators", 3000),
            ("First Nations weaving and visual-art workshop facilitators", 2500),
            ("Venue PA and equipment hire", 1800),
            ("Bush-tucker cooking demonstration ingredients and equipment hire", 1400),
            ("Event first-aid services", 700),
        ],
    },
]


def budget_table(s: dict) -> str:
    lines = ["| Budget item | Amount (GST exclusive) |", "|---|---:|"]
    for item, amount in s["budget"]:
        lines.append(f"| {item} | ${amount:,.2f} |")
    lines.append(f"| **Total budget amount** | **${s['grant_amount']:,.2f}** |")
    return "\n".join(lines)


def attachments(s: dict) -> list[tuple[str, str]]:
    result = []
    if s["bank_attachment"]:
        result.append(
            (
                "Attachment A - Synthetic bank account verification",
                (
                    f"Statement date: 15 January 2026. Account name: {s['org']}. "
                    f"BSB: 00000{s['id'][-1]}. Account number: 0000000{s['id'][-1]}. "
                    "Balances and transactions omitted. Synthetic test document."
                ),
            )
        )
    result.extend(
        [
            (
                "Attachment B - Synthetic entity evidence",
                f"Confirms the fictional legal entity and entity type recorded for {s['org']}.",
            ),
            (
                "Attachment C - Synthetic recent financial statements",
                (
                    f"Summary financial statements for {s['org']}. The fictional applicant is "
                    "financially viable for the proposed activity."
                ),
            ),
        ]
    )
    result.extend(s["extra_attachments"])
    return result


def format_checkbox_options(text: str) -> str:
    """Keep each checkbox option on its own line instead of one merged paragraph.

    Consecutive option lines (and the form's bare "or" separators) get Markdown
    hard line breaks; a wrapped option's continuation line is joined back onto
    its option first. Response panels are left untouched.
    """
    lines = text.split("\n")
    out: list[str] = []
    inside_div = False
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith(":::"):
            inside_div = not inside_div
            out.append(lines[i])
            i += 1
            continue
        if inside_div or not (stripped.startswith("[ ]") or stripped == "or"):
            out.append(lines[i])
            i += 1
            continue

        items: list[str] = []
        while i < len(lines):
            current = lines[i].strip()
            if not current or current.startswith(":::"):
                break
            if current.startswith("[ ]") or current == "or":
                items.append(current)
            elif items and not current.endswith("*"):
                items[-1] = f"{items[-1]} {current}"
            else:
                items.append(current)
            i += 1
        for index, item in enumerate(items):
            out.append(f"{item}\\" if index < len(items) - 1 else item)
    return "\n".join(out)


# Residual blank-form furniture that matches no general rule, curated exactly
# (whitespace-collapsed) like the headings: empty money fields and table
# fragments left behind by the layout extraction.
SCAFFOLD_BLOCKS = {
    "$",
    "[ ]",
    "Details",
    "Details 1",
    "Has co-contribution been secured?",
    "Source of co-contribution (List a maximum of 10)",
    "Amount of Funding (exc GST) Can this proposal proceed without this co-contribution? $",
    "$ Total funding amount:",
    "$ Total Budget Amount:",
    "Budget Item (List a maximum of 10) Amount $",
    "2025-2026 (exc GST) * $",
    "Total funding $",
    "Approx. % of Total $",
    "2025-2026 Total $",
    "You have reached the maximum number of records allowed.",
    "Applicant Legal Name",
    "Registered Business Name",
    "Entity Type ABN State",
    "Postcode",
}


def collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def tokenise_blocks(lines: list[str]) -> list[tuple[str, list[str]]]:
    """Split rendered lines into blank lines, fenced divs and text blocks."""
    units: list[tuple[str, list[str]]] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            units.append(("blank", [lines[i]]))
            i += 1
        elif stripped.startswith(":::"):
            group = [lines[i]]
            i += 1
            while i < len(lines):
                group.append(lines[i])
                closed = lines[i].strip() == ":::"
                i += 1
                if closed:
                    break
            units.append(("div", group))
        else:
            block: list[str] = []
            while (
                i < len(lines)
                and lines[i].strip()
                and not lines[i].strip().startswith(":::")
            ):
                block.append(lines[i])
                i += 1
            units.append(("block", block))
    return units


def is_scaffold(block: list[str]) -> bool:
    """Blank-form furniture: unanswered field labels and unticked options."""
    stripped = [line.strip().rstrip("\\").strip() for line in block]
    joined = collapse_whitespace(" ".join(stripped))
    if joined in SCAFFOLD_BLOCKS or joined.startswith("(Limit:"):
        return True
    if len(block) <= 2 and joined.endswith("*"):
        return True
    return all(
        line.startswith("[ ]") or line == "or" or line.endswith("*")
        for line in stripped
    )


def style_question_blocks(text: str, question_anchors: list[str]) -> str:
    """Mark answered questions and blank scaffold with custom-style divs.

    The answered questions are known exactly — they are the anchors the
    responses were placed against — so blocks matching an anchor are styled
    bold, splitting off any attached instruction lines. Scaffold (the blank
    form's leftover field labels, empty money fields and unticked checkbox
    options) is greyed.
    """
    question_set = {
        collapse_whitespace(anchor.replace("\n", " ")) for anchor in question_anchors
    }

    def clean(line: str) -> str:
        return line.strip().rstrip("\\").strip()

    def match_question(
        group: list[str],
    ) -> tuple[list[str], list[str], list[str]] | None:
        """Split a block into (before, question, after) if it contains an anchor."""
        for start in range(len(group)):
            if (
                collapse_whitespace(" ".join(clean(line) for line in group[start:]))
                in question_set
            ):
                return group[:start], group[start:], []
        for end in range(len(group) - 1, 0, -1):
            if (
                collapse_whitespace(" ".join(clean(line) for line in group[:end]))
                in question_set
            ):
                return [], group[:end], group[end:]
        return None

    def question_div(question: list[str]) -> list[str]:
        # Escape list markers so numbered questions stay plain styled text.
        escaped = [re.sub(r"^(\d+)\.", r"\1\\.", line) for line in question]
        return ['::: {custom-style="Form Question"}', *escaped, ":::"]

    units = tokenise_blocks(text.split("\n"))
    out: list[str] = []
    for kind, group in units:
        if kind != "block":
            out.extend(group)
            continue

        first = group[0].lstrip()
        match = (
            None
            if first.startswith(("#", ">", "|", "- ", ":::"))
            else match_question(group)
        )
        if match:
            before, question, after = match
            if before:
                out.extend([*before, ""])
            out.extend(question_div(question))
            if after:
                out.extend(["", *after])
        elif first.startswith(("#", ">", "|", "- ", ":::")):
            out.extend(group)
        elif is_scaffold(group):
            out.append('::: {custom-style="Form Scaffold"}')
            out.extend(group)
            out.append(":::")
        else:
            out.extend(group)
    return "\n".join(out)


def render_application(form_text: str, s: dict) -> str:
    completed_form, question_anchors = fill_form_inline(form_text, s)
    completed_form = format_checkbox_options(completed_form)
    completed_form = style_question_blocks(completed_form, question_anchors)
    return f"""# 2026 NAIDOC Local Grants Opportunity

## Synthetic application {s["id"]}

> **SYNTHETIC TEST APPLICATION - NOT AN OFFICIAL SUBMISSION**\\
> All organisations, people, contact details, identifiers and supporting documents are fictional.\\
> This document is used only to test the GOGgles IM2026 prototype. External entity and identifier verification is out of scope.

**Submission reference:** SYN-NAIDOC-2026-{s["id"]}\\
**Applicant:** {s["org"]}

# Completed synthetic application form

The form below is rebuilt from "NAIDOC 2026 - Sample Application Form.pdf". All original wording is retained; section headings, bullet lists, checkbox options and question labels are restyled for readability, and each synthetic answer appears at its corresponding field rather than in a separate response section.

Answered questions appear in bold and blank form scaffolding (empty field labels and unticked options) appears in grey. Applicant responses are shown in dark blue within lightly shaded response panels; tabular answers such as the budget appear as tables.

{completed_form}
""".rstrip() + "\n"


def panel_lines(value: str) -> list[str]:
    # A multi-field answer keeps one line per field inside a single panel.
    values = [line.strip() for line in str(value).split("\n") if line.strip()]
    body = [f"{line}\\" for line in values[:-1]] + values[-1:]
    return ['::: {custom-style="Applicant Response"}', *body, ":::"]


def cocontribution_table(rows: list[tuple[str, int, str, str]]) -> str:
    lines = [
        "| Source of co-contribution | Amount (exc GST) | Secured | Can proceed without it |",
        "|---|---:|---|---|",
    ]
    for source, amount, secured, can_proceed in rows:
        lines.append(f"| {source} | ${amount:,.2f} | {secured} | {can_proceed} |")
    total = sum(amount for _, amount, _, _ in rows)
    lines.append(f"| **Total co-contributions** | **${total:,.2f}** | | |")
    return "\n".join(lines)


def format_inline_attachments(s: dict) -> str:
    lines = []
    for title, body in attachments(s):
        lines.append(f"{title}: {body}")
    if not s["bank_attachment"]:
        lines.insert(0, "Bank account verification: Not provided")
    return "\n".join(lines)


def contact_lines(contact: dict) -> str:
    return (
        f"Title: {contact['title']}\n"
        f"First name: {contact['first_name']}\n"
        f"Last name: {contact['last_name']}\n"
        f"Position: {contact['position']}\n"
        f"Position title: {contact['position_title']}\n"
        f"Telephone: {contact['telephone']}\n"
        f"Mobile: {contact['mobile']}\n"
        f"Email: {contact['email']}"
    )


def fill_form_inline(form_text: str, s: dict) -> tuple[str, list[str]]:
    """Place each response at the bottom of its form field's section.

    Every placement anchors on the field's question (or section heading). The
    response panel — or answer table — is inserted at the end of the field's
    section, after its instructions and options, just before the next question
    or heading. A placement may carry an explicit third element naming the
    line the response must be inserted before, for fields whose section is
    followed by text that belongs to the next field.

    Returns the completed text and the question anchors, so the styling pass
    can bold exactly the answered questions.
    """
    officer = s["contact_one"]
    bsb = f"00000{s['id'][-1]}"
    account = f"0000000{s['id'][-1]}"
    bank_response = (
        "Attachment A - synthetic bank account verification"
        if s["bank_attachment"]
        else "Not provided - no bank-verification document is attached."
    )

    text = form_text.replace(
        "Submission Reference: XXX",
        f"Submission Reference: SYN-NAIDOC-2026-{s['id']}",
        1,
    )

    placements = [
        (
            "Your Submission Reference is:",
            f"SYN-NAIDOC-2026-{s['id']}",
            "Enter your email address below to receive a link to access the saved form and a unique Submission",
        ),
        ("Your email address *", s["email"]),
        ("Confirm your email address *", s["email"]),
        ("[ ] I agree *", "[X] I agree"),
        ("What is the Applicant’s legal entity type? *", s["entity_type"]),
        (
            "Is the Applicant able to provide documentation to support the entity\ntype? *",
            "[X] Yes; [ ] No",
        ),
        ("Please provide your supporting documentation. *", s["entity_document"]),
        (
            "Permanent resident of Australia? *",
            "Not applicable - applicant is not a Sole Trader.",
        ),
        (
            "Commonwealth agreement compliance*",
            [
                ("[ ] Yes; [X] No", "(Limit: approx. 38 words, 250 characters)"),
                (
                    "No outstanding compliance issues with Commonwealth agreements.",
                    None,
                ),
            ],
        ),
        ("Child Safety Statement*", "[X] Yes - I can confirm"),
        (
            "Working with vulnerable persons *",
            "[X] Yes - relevant personnel hold the required checks.",
        ),
        (
            "Applicant Bank Account Details*",
            f"BSB: {bsb}\nAccount number: {account}\nAccount name: {s['org']}",
        ),
        ("Documentation to verify bank account details. *", bank_response),
        ("### Authorised Contact One", contact_lines(s["contact_one"])),
        ("### Authorised Contact Two", contact_lines(s["contact_two"])),
        (
            "Is the Applicant an existing Grant Recipient?",
            [
                ("[ ] Yes; [X] No", "If Yes, provide the Organisation ID number"),
                (
                    f"Organisation ID: Not applicable\nApplicant legal name: {s['org']}\n"
                    f"Registered business name: {s['business_name']}\nEntity type: {s['entity_type']}\n"
                    f"ABN: {s['abn']}\nState: {s['state']}\nPostcode: {s['postcode']}\n"
                    "GST registered: [X] Yes\nCharity: [ ] No\nFor profit: [ ] No\n"
                    "Withholding tax exempt: [ ] No",
                    None,
                ),
            ],
        ),
        (
            "Are updates required to the Applicant’s details displayed? *",
            [
                (
                    "[ ] Yes; [X] No",
                    "Please contact your Grant Agreement Manager to update your",
                ),
                ("Grant Agreement Manager confirmation: Not applicable.", None),
            ],
        ),
        (
            "Relevant Persons *",
            [
                (
                    "[X] None of the above apply and there is no adverse information.",
                    "First Name *",
                ),
                (
                    "Conditional name, position and description fields: Not applicable.",
                    None,
                ),
            ],
        ),
        (
            "Reportable Events *",
            "[X] None of the above events apply and there is no adverse information.",
            "Does the Applicant have the following documents? *",
        ),
        (
            "1. Documented organisational and financial policies and procedures. *",
            "[X] Yes; [ ] No",
        ),
        ("2. Business plan and/or strategic plan. *", "[X] Yes; [ ] No"),
        ("3. Risk management plan. *", "[X] Yes; [ ] No"),
        (
            "4. If applying as a Partnership – a formal agreement. *",
            "Not applicable - applicant is not a Partnership.",
        ),
        ("Which Funding Stream are you applying under?*", s["stream"]),
        (
            "Provide a short title (including location, suburb or school name) of\nyour Application for this activity/event. *",
            s["title"],
        ),
        (
            "Provide a brief description of your activity/event and how it meets\nthe objectives of the NAIDOC Local Grants Opportunity. *",
            s["description"],
        ),
        ("Proposal Start Date *", s["start_date"]),
        ("Proposal End Date *", s["end_date"]),
        (
            "In which service area/s is the Applicant proposing to deliver the\nProject/Activity? *",
            s["service_area"],
        ),
        ("Selected service area/s *", s["service_area"]),
        ("Location Name *", s["location_name"]),
        ("Please input your address *", s["address"]),
        (
            "Co-contributions *",
            s["cocontribution"],
            "Note: If you select Stream Three – Large-scale (more than $10,000 and up to $25,000)",
        ),
        (
            "Criterion 1: Demonstrated Experience, Resources and Capability *",
            s["criterion"],
        ),
        (
            "Face to Face events - Social Distancing and COVID-19*",
            [
                ("[X] Yes; [ ] No", "(Limit: approx. 300 words, 2000 characters)"),
                (
                    "The event risk plan will follow current government and health advice. "
                    "Hand hygiene will be available, indoor spaces will be ventilated, unwell "
                    "participants will be asked not to attend, and seating options will support "
                    "Elders and people with health vulnerabilities.",
                    None,
                ),
            ],
        ),
        (
            "Provide a breakdown of the NAIDOC Local Grant funding requested\nfor each service area/s.",
            [
                (
                    f"2025-2026 (exc GST): ${s['grant_amount']:,.2f}\nTotal funding: "
                    f"${s['grant_amount']:,.2f}\nApproximate percentage: 100%",
                    None,
                ),
                (
                    f"2025-2026 total: ${s['grant_amount']:,.2f}\nTotal funding: ${s['grant_amount']:,.2f}",
                    "Activity/Event Attendance*",
                ),
            ],
        ),
        ("Activity/Event Attendance*", s["attendance"]),
        (
            "Activity/Event Attendance Cost *",
            [
                ("Is attendance free: [X] Yes; [ ] No", "Provide your response *"),
                ("Attendance cost: $0.00", None),
            ],
        ),
        (
            "Compliance *",
            "[ ] Yes; [X] No\nNo relevant criminal proceedings or formal complaints.",
        ),
        (
            "Indigenous Organisation Registration *",
            [
                ("[ ] Yes; [X] No", "Provide your response. *"),
                (s["first_nations_profile"], None),
            ],
        ),
        ("Organisational Membership/Ownership", s["membership"]),
        ("Organisational Board/Management Committee", s["board"]),
        ("Organisational Management", s["management"]),
        ("First Nations Employees", s["employees"]),
        (
            "Consortium Applications (including joint, partnership or auspice\napplications) *",
            [
                ("[ ] Yes; [X] No", "Details 1"),
                (
                    "Consortium member legal name and ABN: Not applicable",
                    "You have reached the maximum number of records allowed.",
                ),
                (
                    "More than 20 consortium members: [ ] Yes; [X] No",
                    "More than 20 consortium members. *",
                ),
                (
                    "Additional attachment: Not applicable",
                    "If the Application is successful,",
                ),
            ],
        ),
        (
            "Subcontractor Arrangements *",
            [
                (
                    "[ ] Yes; [X] No",
                    "Have you confirmed the subcontractor arrangements",
                ),
                ("Subcontractor arrangements confirmed: Not applicable", "Details 1"),
                (
                    "Subcontractor legal name and ABN: Not applicable",
                    "You have reached the maximum number of records allowed.",
                ),
                (
                    "More than 20 subcontractors: [ ] Yes; [X] No",
                    "More than 20 Subcontractors. *",
                ),
                (
                    "Additional attachment: Not applicable",
                    "If the Application is successful,",
                ),
            ],
        ),
        ("Privacy declaration*", "[X] I confirm"),
        (
            "## Attachments",
            format_inline_attachments(s),
        ),
        (
            "### Partnership and Sole Trader Letters of Support",
            "Not applicable - applicant is neither a Partnership nor a Sole Trader.",
        ),
        ("### Non-Indigenous Applicants", s["non_indigenous_support"]),
        ("### Assessment Criterion Evidence of Support", s["criterion_evidence"]),
        (
            "Do you have any conflicts of interest that may occur related to or\nfrom submitting this Application? *",
            "[ ] Yes; [X] No",
        ),
        (
            "Describe any conflicts of interest that may occur from submitting this Application. *",
            "Not applicable - no conflict identified.",
            "Please read and complete the following declaration.",
        ),
        (
            "[ ] I understand and agree to the declaration above. *",
            "[X] I understand and agree to the declaration above.",
        ),
        (
            "[ ] I acknowledge that giving false or misleading information to the Community Grants Hub is a serious\n"
            "offence under Section 137.1 of the Criminal Code Act 1995 (Cth). *",
            "[X] I acknowledge the false or misleading information warning.",
        ),
        (
            "Full name of Authorised Officer*              Position of Authorised Officer*           Date",
            (
                f"Full name: {officer['first_name']} {officer['last_name']}\n"
                f"Position: {officer['position_title']}\nDate: 20/02/2026"
            ),
        ),
        (
            "How did you hear about the NAIDOC Local Grants Opportunity? *",
            "GrantConnect notification",
        ),
        (
            "Did you read the NAIDOC Local Grants Opportunity - Grant Opportunity Guidelines? *",
            "[X] Yes; [ ] No",
        ),
        (
            "We welcome any additional feedback on the NAIDOC Local Grants Opportunity - Grant Opportunity\nGuidelines.",
            "The Guidelines were sufficiently clear for this synthetic test application.",
        ),
        (
            "How satisfied were you with the process of applying for a grant?",
            "Satisfied",
        ),
        (
            "We welcome any additional feedback on the Application process.",
            "No additional feedback for this synthetic test application.",
            "Please provide an estimate of the time taken to complete this Application Form,",
        ),
        (
            "Hours                          Minutes",
            "Hours: 4; Minutes: 30",
        ),
        (
            "A copy of the receipt will be sent to: (the email provided)",
            s["email"],
        ),
    ]

    # (anchor, parts) where each part is (response lines, optional insert-before
    # line). A field whose section holds several sub-questions supplies one part
    # per sub-question, so each answer sits directly under its own options.
    entries: list[tuple[str, list[tuple[list[str], str | None]]]] = []
    for placement in placements:
        anchor, value = placement[0], placement[1]
        if isinstance(value, list):
            parts = [
                (panel_lines(part_value), part_before)
                for part_value, part_before in value
            ]
        else:
            before = placement[2] if len(placement) > 2 else None
            parts = [(panel_lines(value), before)]
        entries.append((anchor, parts))

    # Tabular answers render as tables rather than one-line panels.
    entries.append(("Budget *", [(budget_table(s).split("\n"), None)]))
    detailed = s["detailed_cocontributions"]
    if isinstance(detailed, str):
        entries.append(
            ("Co-contributions (detailed breakdown) *", [(panel_lines(detailed), None)])
        )
    else:
        entries.append(
            (
                "Co-contributions (detailed breakdown) *",
                [(cocontribution_table(detailed).split("\n"), None)],
            )
        )

    lines = text.split("\n")

    def find_anchor(anchor: str) -> tuple[int, int]:
        parts = anchor.split("\n")
        for idx in range(len(lines) - len(parts) + 1):
            if lines[idx : idx + len(parts)] == parts:
                return idx, idx + len(parts)
        raise ValueError(f"Could not find form anchor: {anchor!r}")

    def find_line(prefix: str, start: int) -> int:
        for idx in range(start, len(lines)):
            if lines[idx].startswith(prefix):
                return idx
        raise ValueError(f"Could not find form line: {prefix!r}")

    spans = [find_anchor(anchor) for anchor, _ in entries]
    boundaries = sorted(
        {idx for idx, line in enumerate(lines) if line.startswith(("## ", "### "))}
        | {start for start, _ in spans}
        | {len(lines)}
    )

    insertions = []
    for (anchor, parts), (start, end) in zip(entries, spans):
        for content, before in parts:
            if before is not None:
                target = find_line(before, end)
            else:
                target = next(boundary for boundary in boundaries if boundary >= end)
            insertions.append((target, content))

    for target, content in sorted(insertions, key=lambda item: item[0], reverse=True):
        block = list(content)
        if target and lines[target - 1].strip():
            block = ["", *block]
        lines[target:target] = [*block, ""]

    question_anchors = [anchor for anchor, _ in entries if not anchor.startswith("#")]
    return "\n".join(lines), question_anchors


def render_writer_smoke() -> str:
    return """# Writer-view smoke test - isolated budget field

> **SYNTHETIC TEST INPUT - NOT AN OFFICIAL SUBMISSION**

Only this budget field is supplied to the writer-view assessment call. No other draft fields are in context.

## Application Form instructions

Budget: Provide a FULL breakdown of costs for the funding requested for your activity/event. You must separate out costs using two or more line items to describe the different components of the activity/event. All budget figures must be GST exclusive.

## Applicant draft

| Budget item | Amount |
|---|---:|
| First Nations storytelling | $600 |
| Event delivery | $5,500 |
| Workshop costs | $1,000 |
| NAIDOC T-shirts for participants | $1,000 |
| **Total** | **$8,100** |
"""


def main() -> None:
    MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)
    form_text = extract_form_text()

    for original in SCENARIOS:
        scenario = copy.deepcopy(original)
        expected_total = sum(amount for _, amount in scenario["budget"])
        if expected_total != scenario["grant_amount"]:
            raise ValueError(
                f"Application {scenario['id']} budget total {expected_total} does not match "
                f"grant request {scenario['grant_amount']}"
            )
        target = MARKDOWN_DIR / f"synthetic-application-{scenario['id']}.md"
        target.write_text(render_application(form_text, scenario), encoding="utf-8")

    WRITER_SMOKE_PATH.write_text(render_writer_smoke(), encoding="utf-8")


if __name__ == "__main__":
    main()
