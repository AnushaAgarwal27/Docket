# Docket agents

Five Fetch.ai uAgents (uagents 0.26.1). Addresses come from each agent's seed in `.env`, so they stay
the same as long as the seeds do. Regenerate this file with `python -m scripts.print_agents`.

| Agent | Role | Port | Address | Inspector |
|---|---|---|---|---|
| docket-coordinator | Talks to the student in ASI:One (chat protocol), sends cards, narrates the Hearing | 8001 | `agent1qwj0e7jf5gu6lw3tael5ld2v8xeg4jrzgs8wx7yg22a82du6dcqeqtr0686` | [open](https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A8001&address=agent1qwj0e7jf5gu6lw3tael5ld2v8xeg4jrzgs8wx7yg22a82du6dcqeqtr0686) |
| docket-ledger | Reads paystub PDFs and the Nessie bank feed; matches refund deposits | 8002 | `agent1qtf9k33ql2zj8urx6cnrdggs7q95u3mzv52cu7mlw3sf3p7m5m3rvsuafct` | [open](https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A8002&address=agent1qtf9k33ql2zj8urx6cnrdggs7q95u3mzv52cu7mlw3sf3p7m5m3rvsuafct) |
| docket-tax | Runs the rules in code and argues the student's side in the Hearing (Advocate) | 8003 | `agent1qdf9lwqa5nytzqren5jmq90x2087m08agusvu57w5c2m0sy25yjykzjdskm` | [open](https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A8003&address=agent1qdf9lwqa5nytzqren5jmq90x2087m08agusvu57w5c2m0sy25yjykzjdskm) |
| docket-auditor | Argues the employer's side in the Hearing and issues the verdict in code | 8006 | `agent1qvqezkjvxsf7uv0eakd0mtvntx2tts5h7ceqejqcautyhqhc2t62kh7lvsl` | [open](https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A8006&address=agent1qvqezkjvxsf7uv0eakd0mtvntx2tts5h7ceqejqcautyhqhc2t62kh7lvsl) |
| docket-caseworker | Refund case state machine, approvals, payroll calls and letters | 8004 | `agent1qdkme4g80e6c2vq2ujepfczqffa4zgzkkv2rp54getlgtl37wryg27z34cc` | [open](https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A8004&address=agent1qdkme4g80e6c2vq2ujepfczqffa4zgzkkv2rp54getlgtl37wryg27z34cc) |

Each agent logs `Agentverse mailbox: connected` (or how to fix it) about 20 seconds after it starts.
Agentverse profile URL for docket-coordinator: TODO paste from Agentverse (Agent Profile page).
