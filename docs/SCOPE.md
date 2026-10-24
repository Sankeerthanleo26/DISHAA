# DISHAA: Scope (v1)

## In scope

**Geography:** Ireland only.

**Audience:** international students (non-EEA) planning to study in Ireland or already studying there.

**Topics covered:**
- Study visa application and required documents
- Proof of funds and financial requirements
- Stamp 2 and registration with immigration (IRP)
- Work-hour limits during term and holidays
- Course and school requirements (for example approved programmes)
- Graduate pathway (Stamp 1G)
- Renewals and common compliance rules

**Sources (official only):**
- Irish Immigration Service Delivery (irishimmigration.ie)
- Department of Justice
- Citizens Information (citizensinformation.ie)
- Other official Irish government pages as needed

**System components:**
- Scraping, cleaning, chunking, embedding, indexing
- Retrieval with country and visa-type filters
- Grounded generation through a hosted LLM with citations and refusals
- Evaluation harness and experiment log
- FastAPI backend and a simple web frontend
- Freshness pipeline
- AWS deployment with logging and cost tracking
- README, architecture diagram, demo

## Out of scope for v1

- Other countries (planned: UK, Canada, UAE, then USA)
- Work, family, refugee and asylum pathways
- Personalized legal advice or case-specific eligibility decisions
- User accounts, saved chats, document upload
- Training or pretraining a model from scratch (a small separate GPT project may follow for learning)
- Fine-tuning (optional stretch after RAG works)
- Mobile app
- Multilingual interface

## Future phases

| Phase | Addition |
|---|---|
| 2 | UK and Canada student pathways |
| 3 | UAE |
| 4 | USA (F-1 and OPT first) |
| 5 | Worker, family and refugee pathways |
| Stretch | Eligibility checker (rules engine plus LLM explanation), LoRA fine-tune vs plain RAG comparison |

## Definition of done (v1)

- Public HTTPS URL answering Ireland student visa questions with citations
- Eval report with metrics and at least three documented experiments
- Freshness job running on a schedule
- README with architecture, decisions, failures and results
- Repository public with a clear commit history

## Ground rules

- Official sources only; every claim cites a source
- When unsure, say so and link to the official page
- Not legal advice, and the interface says so
- Ireland works end to end before any new country is added
