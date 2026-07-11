---
name: code-review
description: Strict maintainability review for abstractions, file size, and spaghetti growth.
disable-model-invocation: true
---

# Strict Maintainability Review

Be ambitious about structure, not cosmetic nits.

## Non-negotiables

- Prefer deleting complexity over rearranging it (“code judo”)  
- Flag PRs that push a file past ~1000 lines without decomposition  
- Flag special-case branches bolted onto unrelated flows  
- Prefer real abstractions over thin wrappers / identity helpers  
- Keep logic in the canonical layer; reuse existing helpers  
- Demand clearer types and boundaries when they remove branching  
- Treat non-atomic multi-step state updates as smells when a safer structure is obvious  

## Questions

Is there a simpler reframing? Did branching grow where a model should exist?
Is this the right package? Does the abstraction earn its keep?

## Tone

Direct and demanding about maintainability; not rude. Prefer a few high-conviction
findings over a laundry list of nits.

## Approval bar

Do not approve on “it works” alone if structural debt clearly increased or a
simpler design was left on the table.
