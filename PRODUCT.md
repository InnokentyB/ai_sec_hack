# Product

<!-- impeccable:product-schema 1 -->

## Platform
web

## Stack
Python 3.12, FastAPI, Jinja2, vanilla CSS/JS, SQLite WAL, Ed25519 and RFC 8785.
Approved in docs/ARCHITECTURE_CONTRACT.md on 2026-10-22.

## Users
The owner authorizes a synthetic delivery and inspects a chain of agent delegation.
Hackathon reviewers inspect actual effects and independently verify exported evidence.

## Product Purpose
Constrain delegated authority and link owner approval, executor action and receiver confirmation.

## Capabilities and Constraints
One depth, one action, one root-wide dispatch. Scripted A/B/C agents; no live LLM.
Local synthetic documents only. Unknown delivery outcomes stay uncertain until a read-only receipt lookup.
Three panels: permissions, signed event chain, actual isolated inbox. Separate offline verifier.
The owner must still perform UAT; automated checks do not establish usefulness or legal validity.

## Accessibility & Inclusion
English controls, explicit labels and keyboard focus, textual verdicts, responsive layout.
