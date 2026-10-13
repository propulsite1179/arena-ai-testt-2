# Privacy and legal launch checklist

Public legal pages are explicitly **drafts requiring operator review**. Configure legal entity, contact, address, jurisdiction, hosting/processor details, retention policy and billing terms. Generated text is not a substitute for legal counsel.

The application stores account email/name/password hash, expiring session hashes, necessary anonymous visitor identifiers, preference data, persisted professional requests and votes. It uses no third-party analytics or advertising cookies. Theme selection is local browser storage. Necessary functionality is not automatically exempt from every notice/consent obligation; assess the actual jurisdiction and deployment.

Account export and authenticated deletion are implemented. Deletion removes the account/session/follows/comparisons and direct contact leads for the email, while anonymizing user linkage in scientific decisions/votes. Billing processors may hold records subject to separate retention rules. Scientific records must not silently expose deleted names or emails in free text: administrators must review notes and artifacts separately.

`python -m gamedev.cli cleanup` expires sessions/rate records, removes old fixture votes/matches and old leads under the documented default policy. Run it through the operator's scheduler after confirming retention periods. No automatic scheduler is installed. Backups need their own retention/deletion procedure. Do not enroll minors in public accounts or paid subscriptions before reviewing age/guardian requirements.

No partnership, sponsorship, verified customer count, brand availability, trademark registration or domain ownership is claimed. Provider names identify factual catalog sources, not endorsements. No proprietary benchmark database or copyrighted game/media assets were imported.
