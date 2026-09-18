# Resume and cover letter rules

## Score that actually matters

ATS checkers often pass keyword and structure scores and fail Quantified Impact. The durable rule is action + scope + outcome. Duty statements without a number or a before/after are the default failure mode.

## Title

Pick the posting's primary title when the work supports it. Keep header and summary titles consistent. Do not inflate to Staff or Principal unless facts say that is the real title.

For infrastructure roles a safe allowed set is:

- Senior DevOps Engineer
- Senior SRE
- Senior Platform Engineer
- Senior DevSecOps Engineer

Swap the set if the user's field is different. DevSecOps is allowed when the JD is security-in-the-pipeline. It is the wrong default for a pure platform role.

## Summary

Two or three sentences. Years and domain, then one or two confirmed outcomes that match this JD, then a close on the stack they named. Not a capability list.

## Bullets

Formula: action + tool + scope + result. At least one of scope or result should be a number from facts.

Reorder bullets inside each job so the best JD match is first. Four bullets per recent role is enough. Older roles can drop to three.

Drop process-only bullets ("used AI to keep a wiki current") unless the posting is actually about that tool.

## Dates and concurrent work

Keep the date ranges in facts. Label side practice / consulting so overlaps with full-time roles are explained.

## Skills section

Keep the existing group labels. Deduplicate. Promote JD tools to the front of their group when the user actually used them.

## Layout

Keep the existing YAML header, color boxes, Symbola contact icons, and `\sectionrule`. Do not introduce a `\newpage` that leaves a blank page. Two pages is fine if both pages have content.

Compile with `md2pdf` when the toolkit shell aliases are loaded. That wrapper is `pandoc "$input" -o "${input%.md}.pdf" --pdf-engine=xelatex`.

## Cover letter

Cold professional. Short paragraphs. No em dashes. No ellipses. No trailing `?`.

Shape:

1. I am applying for {role} at {company}.
2. Two proof points that map to their must-haves.
3. One sentence on why this posting's stack matches work already done.
4. Close. Happy to walk through the work. Sign the short name from facts.

Do not retell the whole resume. Do not mention salary, disability, legal disputes, or unemployment.

## Honesty

If a posting wants DORA metrics, SLO math, dollar savings, or clearance and facts does not have them, say the gap in the delivery notes. Do not fill the gap on the page.

When the user supplies a new number in chat, that number becomes canonical. Patch facts and the master resume in the same turn.
