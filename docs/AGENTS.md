# Docket agents

8 Fetch.ai uAgents (uagents 0.26.1). Addresses come from each agent's seed in `.env`, so they stay
the same as long as the seeds do. Regenerate this file with `python -m scripts.print_agents`.

| Agent | Role | Port | Address | Inspector |
|---|---|---|---|---|
| docket-coordinator | Talks to the student in ASI:One (chat protocol), sends cards, narrates the Hearing | 8001 | `agent1qdcydhdy3drfp5amt48hqqspvyzu8ggv6me59v8rek7mvk8y4q6csnk3dz2` | [open](https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A8001&address=agent1qdcydhdy3drfp5amt48hqqspvyzu8ggv6me59v8rek7mvk8y4q6csnk3dz2) |
| docket-ledger | Reads paystub PDFs and the Nessie bank feed; matches refund deposits | 8002 | `agent1qfx8zr76aza0tvrxszqgzyu6skdf3ulr3kqflve9tewj2xdvj44q52m32vd` | [open](https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A8002&address=agent1qfx8zr76aza0tvrxszqgzyu6skdf3ulr3kqflve9tewj2xdvj44q52m32vd) |
| docket-tax | Runs the rules in code and argues the student's side in the Hearing (Advocate) | 8003 | `agent1qt4l5mr37zcvfhk0fqt9cs0pzlp60t5qy8vqcf3r2qlwlcu7gpkq79vevvr` | [open](https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A8003&address=agent1qt4l5mr37zcvfhk0fqt9cs0pzlp60t5qy8vqcf3r2qlwlcu7gpkq79vevvr) |
| docket-auditor | Argues the employer's side in the Hearing and issues the verdict in code | 8006 | `agent1qvqezkjvxsf7uv0eakd0mtvntx2tts5h7ceqejqcautyhqhc2t62kh7lvsl` | [open](https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A8006&address=agent1qvqezkjvxsf7uv0eakd0mtvntx2tts5h7ceqejqcautyhqhc2t62kh7lvsl) |
| docket-caseworker | Refund case state machine, approvals, payroll calls and letters | 8004 | `agent1qdl8d9m2ul4sr7r48r5ayakwwhdm6x40j65ax5sjww6hc2m2hqezszkma2j` | [open](https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A8004&address=agent1qdl8d9m2ul4sr7r48r5ayakwwhdm6x40j65ax5sjww6hc2m2hqezszkma2j) |
| docket-researcher | Athena: researches what the file cannot answer and watches the rules that fired, verifying every source in code | 8005 | `agent1qtlke98gyp2ynpgn5ztpmps094kup2hwjd583u4jg4q62jt407dhj08y9nd` | [open](https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A8005&address=agent1qtlke98gyp2ynpgn5ztpmps094kup2hwjd583u4jg4q62jt407dhj08y9nd) |
| docket-organizer | Finds employers where several students share a finding and runs the combined request for the ones who opt in | 8007 | `agent1q25kkfyjnx9kp370e5qnqagx6hy065q7z7pvqa284tnckwvltnukvpqanzf` | [open](https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A8007&address=agent1q25kkfyjnx9kp370e5qnqagx6hy065q7z7pvqa284tnckwvltnukvpqanzf) |
| docket-filer | Fills in the student's forms from stored records and submits only what she approves | 8008 | `agent1qwf28zyfhmjrj0ygts5uugv8xjzwa3274apagvugym9s3h6v4fdpykc899r` | [open](https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A8008&address=agent1qwf28zyfhmjrj0ygts5uugv8xjzwa3274apagvugym9s3h6v4fdpykc899r) |

Each agent logs `Agentverse mailbox: connected` (or how to fix it) about 20 seconds after it starts.
Agentverse profile URL for docket-coordinator: TODO paste from Agentverse (Agent Profile page).
