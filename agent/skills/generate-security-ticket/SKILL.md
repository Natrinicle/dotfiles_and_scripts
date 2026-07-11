---
name: generate-security-ticket
description: Turn confirmed security findings into clear tickets with impact, repro, and remediation.
---

# Generate Security Ticket

For each validated issue:

- Title + severity rationale  
- Component / version / environment  
- Impact (C/I/A)  
- Minimal reproduction the team can run **in authorized environments**  
- Suggested fix + how to verify  
- Related references (CWE, advisory) when known  

No inventing attacks against systems without authorization. Prefer defensive PoCs.
Use the team’s tracker fields when known; otherwise plain structured markdown.
