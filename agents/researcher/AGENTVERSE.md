![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

# Docket Researcher (Athena): the deep-research layer behind every answer

When a student asks something her file cannot answer, this agent researches it properly instead of
guessing. It also watches, unasked, for changes to the rules that actually fired on her paystubs, and
tells her when one of them changes what she should do. It is part of Docket, a caseworker for F-1
international students; students talk to Docket through the **docket-coordinator** agent in ASI:One.

## Key features
- Runs on ASI:One's agentic models, which plan the research and can call other agents on Agentverse; falls back to Claude with web search
- Every source is fetched by code and has to contain the claim's wording before it counts; a source that 404s or does not support the answer is dropped
- An answer with no surviving source is marked low confidence and is never stated as fact
- Takes questions asked on the phone: the voice line records them, this agent answers and texts her back
- Watches the IRS, USCIS, eCFR and the news for the rules on her file, not for F-1 news in general
- Sends only de-identified context to the research service: visa category, rule id and employer kind, with her name, employer, school, phone and amounts stripped in code first

## Usage
Not chatted with directly. Ask **docket-coordinator** in ASI:One, or call Docket's student line and
ask out loud; anything that needs research is handed to this agent and the answer comes back as a
message.

## Limitations
Research, not advice. It reports what official sources say and how confident the check was; it is not
a lawyer or a tax advisor, and an uncertain answer is returned with its uncertainty attached.

## Credits
Built at Cal Hacks 13.0 by Anusha, Rhianna and Soham.
