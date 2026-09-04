# Room service

Backend services related to accommodation listings:

- `chatbot/`: stateless hybrid chatbot (structured filters + database retrieval + optional LLM wording).
- `risk/`: explainable cold-start risk scoring for listings.

The roommate feature is intentionally not included because it is maintained by another team member.

## Risk API

- `GET /risk/listings/{id}`: preview a score without writing to the database.
- `POST /risk/listings/{id}/assess`: admin-only assessment that persists the result.
- `POST /risk/assess-pending?limit=100`: admin-only batch assessment.

Risk levels stay compatible with the current frontend: `safe < 0.3`, `caution < 0.6`, and `suspicious >= 0.6`. A persisted score of `0.01` means the listing was evaluated with no material warning signal; the legacy value `0` still means unknown.
