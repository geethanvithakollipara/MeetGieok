"""Realistic synthetic dataset: 3 contacts, 3-4 past meetings each + 1 upcoming.

The notes are written as a story arc per contact so the brief visibly improves
(generic -> personalized) as memory accumulates. Includes missed commitments,
shifting objections and preferences so recall has real work to do.
"""

CONTACTS = {
    "Sarah Johnson": {
        "name": "Sarah Johnson", "role": "Product Manager", "company": "TechNova",
        "background": "Evaluating our analytics API for her product's reporting module.",
    },
    "Alex Morgan": {
        "name": "Alex Morgan", "role": "Engineering Manager", "company": "CloudWorks",
        "background": "Evaluating our observability platform for 4 platform teams.",
    },
    "Priya Sharma": {
        "name": "Priya Sharma", "role": "Marketing Director", "company": "FinEdge",
        "background": "Planning a Q4 SME-lending campaign with our agency; based in Mumbai.",
    },
}

MEETINGS = {
    "Sarah Johnson": [
        {"date": "2026-06-02", "title": "Discovery call", "notes": """
Sarah's team spends ~3 days a month building manual reports; goal is to cut that to hours.
Biggest concern: SSO. TechNova requires SAML, no exceptions. Also asked about data retention.
She asked for short emails - 'three bullets max, I skim on my phone'. Prefers Tuesday mornings.
I committed to send API docs by Thursday and our security whitepaper by next week.
She will check internally who signs off on vendor security reviews."""},
        {"date": "2026-06-16", "title": "API walkthrough", "notes": """
Docs were reviewed by her two engineers - they liked the REST design but asked about rate limits.
I had promised the security whitepaper; it went out 5 days late and she mentioned it, mildly annoyed.
Their security team now also wants our SOC2 report. I promised to send it by Friday.
She brought up competitor DataPulse, who quoted lower per-seat pricing. No decision on that.
SAML support is still unconfirmed - I need to get an answer from our engineering team.
Sarah will introduce me to their CTO, Ravi Menon, before the pilot discussion."""},
        {"date": "2026-07-07", "title": "Pilot scoping", "notes": """
SOC2 report received and accepted by their security team - closed. Ravi Menon joined for 15 minutes.
Agreed pilot: 3 teams, 60 days, starting Aug 1. Success metric: reporting time down 70%.
Pricing: Sarah wants a 15% discount for an annual commitment; I said I'd take it to my manager.
SAML: I told her engineering targets a beta in August. She was cautiously OK but wants it in writing.
Sarah liked the data-driven slides; said 'no fluff, show me numbers and timelines'."""},
        {"date": "2026-08-11", "title": "Pilot midpoint review", "notes": """
Pilot is running, 2 of 3 teams onboarded. Reporting time already down 55%.
Problem: hitting API rate limits in staging during nightly report runs; engineers frustrated.
SAML beta delivered on Aug 5 and works - the written SAML commitment is now fulfilled.
Discount: my manager approved 10%, not 15%. I haven't communicated this yet - Sarah will be disappointed.
Budget approval for full rollout happens in Q4; she needs a one-page ROI summary for finance.
She asked for a named customer success manager. I promised to send the ROI one-pager by Aug 25 and a rate-limit fix ETA."""},
    ],
    "Alex Morgan": [
        {"date": "2026-06-09", "title": "Intro / pain discovery", "notes": """
Alex manages 4 platform teams at CloudWorks; on-call burnout and alert fatigue are the main pains (~300 alerts/week, 70% noise).
Very technical. Said clearly: 'skip the sales deck, show me architecture'. Dislikes Monday meetings.
He wants to see how ingestion scales with Kafka. I promised architecture diagrams by Friday."""},
        {"date": "2026-07-14", "title": "Technical deep-dive", "notes": """
Diagrams were sent on time, he appreciated the Kafka ingestion detail.
Hard requirements: Terraform provider for config-as-code, and EU data residency (Frankfurt region).
I committed to give his team a sandbox environment by July 21. Alex will share two anonymised incident postmortems.
Open question: does our alert deduplication handle Kafka consumer-lag storms? I don't know yet.
Procurement at CloudWorks is wary of vendor lock-in."""},
        {"date": "2026-08-25", "title": "Sandbox feedback", "notes": """
Sandbox was delivered a week late (July 28). Alex noted it; said reliability of promises matters to him.
He shared the postmortems; both involved noisy alerts during Kafka lag events - dedup question is still open.
Terraform provider is only in beta and lacks alert-policy resources - a blocker for him.
Frankfurt region confirmed for Q4 - he wants that in writing in the SLA.
Procurement now asks for a written SLA and data-export guarantees to address lock-in fears.
I promised: SLA draft, Terraform roadmap, and a dedup test against his postmortem scenario, all by Sept 15."""},
    ],
    "Priya Sharma": [
        {"date": "2026-06-23", "title": "Campaign kickoff briefing", "notes": """
Priya (Mumbai) wants a Q4 campaign for FinEdge's SME loan product. Audience: shop owners and small manufacturers.
Brand voice: trustworthy, plain language, zero jargon. Legal review takes ~5 working days for anything customer-facing.
She prefers quick WhatsApp check-ins and meetings before 11am IST. Dislikes long decks.
She will send brand guidelines by end of week. I will bring 3 campaign concepts next time."""},
        {"date": "2026-07-28", "title": "Concept review round 1", "notes": """
Brand guidelines have NOT arrived yet; I chased on WhatsApp.
She rejected the tagline 'instant approval' - regulatory risk, RBI guidelines on lending claims. Wants 'quick decision' style wording only.
Budget confirmed: Rs 18 lakh for Q4. She wants A/B testing on subject lines and CTAs.
She liked the visual direction of concept B but said the copy is too formal.
I promised revised copy in simple language and a channel plan (email + WhatsApp + LinkedIn) in two weeks."""},
        {"date": "2026-09-08", "title": "Concept review round 2", "notes": """
Revised copy approved in principle; concept B 'Growth without the paperwork' selected.
Brand guidelines still missing - Priya apologised, said her brand team is slow.
Legal sign-off pending, needs to be submitted by Sept 12 to allow the 5-day review.
Her CMO Rohan Mehta wants a 10-minute presentation before launch. Priya is worried about CAC targets.
She wants a weekly performance dashboard once live. I promised the dashboard mock and a legal submission pack."""},
    ],
}

UPCOMING = {
    "Sarah Johnson": {"title": "Pilot wrap-up & renewal decision", "date": "2026-10-01",
                      "agenda": "Review pilot results, pricing, rollout plan for Q4."},
    "Alex Morgan": {"title": "Technical validation checkpoint", "date": "2026-10-01",
                    "agenda": "Review SLA draft, Terraform roadmap and dedup test results."},
    "Priya Sharma": {"title": "Pre-launch review", "date": "2026-10-01",
                     "agenda": "Final creatives, legal status, CMO presentation, dashboard."},
}
