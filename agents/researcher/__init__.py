"""Athena: the research layer behind everything Docket says that is not already in the student file.

Two jobs:

    watch   On an interval, read the official pages and the news for the things that actually bear on
            this student — her visa category, her employer, her school, the rules that fired on her
            paystubs — and raise a finding only when something changed what she should do.

    ask     Answer a question she asked, on the phone or in chat, by researching it properly rather
            than by guessing. The voice line hands over anything it cannot answer from the file, and
            the answer comes back to her as a message.

Engines, in order: ASI:One's agentic models (api.asi1.ai), which plan a research task and can reach
other agents on Agentverse; then Claude with web search as the fallback. Whichever answers, the same
rule applies: a source only counts if code fetched the page and found the supporting text in it.
A claim with no fetchable source is not reported as fact.
"""
