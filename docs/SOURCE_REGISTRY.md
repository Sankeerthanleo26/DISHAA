# DISHAA: Source Registry

**Status:** Draft v1 · **Owner:** Sankeerthan Sornapoodi · **Date:** 2026-11-16
**Related:** [PRD](PRD.md) (FR-11, FR-27 to FR-33) · [Risk Register](RISK_REGISTER.md) · [Eval Plan](EVAL_PLAN.md)
**Machine-readable lists:** [`sources/ie_student.toml`](../sources/ie_student.toml) (14) · [`sources/us_student.toml`](../sources/us_student.toml) (33)

## 1. What this is

The TOML files are what the fetcher reads. This document is the human side: why each source is trusted, who owns it, how old it looks, and what we left out. Every fact the system states must trace back to a row here.

## 2. Inclusion rules

1. **Official domain only.** Government agencies and their official programmes. Commercial sites, forums, university marketing pages and embassy-adjacent blogs are out.
2. **Evergreen guidance pages over dated posts.** Study in the States and Education in Ireland both publish blog and news items (URLs with `/2018/08/...` or a `blog.` host). They are not core sources: they are written for a moment and are not maintained when rules change.
3. **One canonical URL per document.** Legacy and duplicate URLs are not ingested.
4. **HTML only in v0.1.** The extractor reads HTML (ADR-010). PDFs are listed as deferred, not silently dropped.
5. **Every source maps to a pathway step** (`visa_category` for now; pathway and step tags come with the pathway graph).
6. **Tier.** `core` = the page itself states the rule. `supporting` = regulation or policy text, overviews and news, used to check or enrich.

## 3. How these entries were checked, and what that does not prove

- **Method:** each URL was found through official-domain web searches on 2026-11-16 and appears in the search index with its title and snippet.
- **What is NOT done:** none of these pages has been fetched and extracted by our pipeline. Live fetches of the 14 Irish URLs were refused by this session's network allowlist, and one US fetch failed. So "found in the index" means the page exists; it does not mean the extractor handles it (risk R10).
- **Page age** below is the "page age" the search index reported on 2026-11-16, in days. Its exact meaning (last modified or last seen) is not documented, so treat it as a hint about staleness, not a date of record. A blank means the index showed no age.
- **robots.txt and terms of use** have not been checked here. The fetcher checks robots.txt at run time (ADR-008). Terms of use for each domain are still to be read.

**Next step:** you run `dishaa-fetch` for both lists on your machine (network access), then `dishaa-chunk --show <id>` on a few pages. That is the first real test of the extractor.

## 4. USA registry (33 sources)

| ID | Owner | Tier | Category | Age (days) | Notes |
|---|---|---|---|---|---|
| us-student-visa | State Dept | core | f1-student | | Indexed with a `?lv=true` suffix; canonical form to confirm at first fetch |
| us-ds160 | State Dept | core | f1-student | | Indexed with tracking parameters; the listed URL is the clean form |
| us-ds160-faq | State Dept | core | f1-student | 1320 | Old; check against the newer student-visa page |
| us-visa-fees | State Dept | core | f1-student | 172 | Fee tables; changes should trigger review |
| us-sevis-fee-faq | ICE (SEVP) | core | f1-student | 187 | Conflicts with an older document, see 6a |
| us-sits-form-i20 | DHS (Study in the States) | core | f1-student | 567 | Replaces a 2025 post as the I-20 source |
| us-sits-maintaining-status | DHS (Study in the States) | core | f1-student | 567 | |
| us-sits-full-course | DHS (Study in the States) | supporting | f1-student | 1015 | |
| us-sits-fixed-period-rule-faq | DHS (Study in the States) | core | f1-student | 78 | **Not yet read, see 6a** |
| us-vetting-announcement | State Dept | supporting | f1-student | 60 | News; a policy-change signal, not a rule page |
| us-ice-sevp-regs | ICE (SEVP) | supporting | f1-student | 474 | Regulation text of 8 CFR 214.2(f) |
| us-sits-working | DHS (Study in the States) | core | f1-employment | 1085 | Old; central to F04 and F05 |
| us-uscis-students-employment | USCIS | core | f1-employment | 362 | |
| us-sits-practical-training | DHS (Study in the States) | core | practical-training | 85 | |
| us-ice-practical-training | ICE (SEVP) | core | practical-training | 707 | Covers CPT |
| us-uscis-pm-practical-training | USCIS | supporting | practical-training | 783 | Policy Manual, Vol. 2, Part F, Ch. 5 |
| us-uscis-opt | USCIS | core | opt | 722 | |
| us-uscis-stem-opt | USCIS | core | stem-opt | 291 | |
| us-sits-stem-opt-hub | DHS (Study in the States) | core | stem-opt | 92 | |
| us-sits-stem-opt-eligibility | DHS (Study in the States) | core | stem-opt | 237 | |
| us-sits-stem-opt-faq | DHS (Study in the States) | core | stem-opt | 568 | |
| us-uscis-h1b | USCIS | core | h1b | 57 | |
| us-uscis-h1b-cap | USCIS | core | h1b | 8 | Youngest page in the set: a good freshness canary |
| us-uscis-o1 | USCIS | core | o1 | 1355 | Old page; the Policy Manual was updated in 2025 |
| us-uscis-pm-o1 | USCIS | supporting | o1 | 470 | Policy Manual, Vol. 2, Part M, Ch. 4 |
| us-uscis-gc-categories | USCIS | core | green-card | 74 | |
| us-uscis-gc-employment | USCIS | core | green-card | 497 | |
| us-uscis-eb1 | USCIS | core | green-card | 662 | |
| us-uscis-eb2 | USCIS | core | green-card | 671 | Includes national interest waivers |
| us-uscis-eb3 | USCIS | core | green-card | 89 | |
| us-uscis-stem-options | USCIS | supporting | pathway-overview | 662 | Used to draft and check the pathway graph |
| us-uscis-stem-nonimmigrant | USCIS | supporting | pathway-overview | 1178 | |
| us-uscis-stem-immigrant | USCIS | supporting | pathway-overview | 805 | |

## 5. Ireland registry (existing 14, status after this check)

Owner of the core pages is Immigration Service Delivery of the Department of Justice (one recent page names it "Department of Justice, Home Affairs and Migration", so the owner name itself is changing).

| ID | Status in the search index | Age (days) | Notes |
|---|---|---|---|
| study-hub | Found | 868 | |
| study-visa-options | Found | 1385 | |
| study-options | Parent page not seen; sub-pages found | | Confirm at first fetch |
| study-travel-path | Found | 978 | Contains a notice about a suspension of consideration of some applications: read in full |
| before-after-arrive | Found | 1391 | |
| student-faq | Found | 595 | Carries a September 2023 notice; states work-hour conditions |
| student-finances | Found | 504 | Rules depend on visa-required status and on course start date (after 1 July 2023) |
| medical-insurance | Found | 724 | |
| registering-permission | Parent page not seen; sub-pages found | | Confirm at first fetch |
| registration-required-documents | Found | 25 | One URL serves many stamp categories; see 6c |
| graduate-programme-1g | Found | 963 | |
| ilep-courses | **Not found**; a similar page `planning-to-study-in-ireland` exists (964) | | Page may have been renamed; confirm |
| visa-application-system-guide | Listed in the site map | | Sits under the "visit Ireland" section |
| education-in-ireland-working | **URL differs** from the indexed one (`.../while-you-re-in-ireland/working-in-ireland/`) | 2128 | Old; promotional agency site; supporting tier only |

## 6. Findings that change the design

**a. Official pages disagree with each other, and with time.**
- A Study in the States FAQ (78 days old) is titled as covering a final rule that establishes a fixed time period of admission ("Admit Until Date") for F students, where they were previously admitted for "duration of status". Older official pages in the same domain still describe the old model. I have only the search snippet, not the full page, so its effective date, transition rules and exceptions are **unknown**. It must be read in full before anything is stated from it.
- The I-901 SEVIS fee appears as $350 for most people on an ICE FAQ (187 days old), and as $200 in a Study in the States tutorial script about 3,885 days old. The old document is not in our lists, and it shows why page age is recorded.
- Consequence for the pipeline: change detection tells us a page changed, not that it is right. Section 4 shows 18 of the 31 US pages with a reported age are over a year old, so "unchanged" is also not proof of "current". The review queue needs a rule for conflicts between sources.

**b. Rules that depend on dates and conditions are common.** The Irish finances page changes by course start date, and the Irish FAQ and student-permission pages carry September 2023 notices. These are the exception traps the Eval Plan needs.

**c. Duplicate and legacy URLs exist.** The Irish "required documents" content is reachable under at least three URL forms, one of them about 1,070 days old and showing different stamp sections. One page serves many stamp categories (Stamp 0, 1G, 2...), so chunk headings must carry the stamp name, or answers will mix stamps.

**d. Key Irish policy documents are PDFs.** The student pathway programme criteria, the Third Level Graduate Programme rules and the TrustEd policy statement are PDFs. The extractor is HTML-only, so these are deferred. **Decided 2026-11-21 (ADR-021):** PDFs stay deferred in v0.1 and are tracked as known gaps; a PDF is promoted only when an eval case cannot be answered without it.

**e. The existing Irish list is missing pages students actually need.** Recommended additions (HTML, found in the index, not yet added to `ie_student.toml`, pending your approval):
- How to apply for a long term study visa (the main student visa page)
- How to apply for a short 'C' visit (study) visa
- Student Permission (immigration permission for students)
- Immigration permission and stamps
- Frequently asked questions for Registration
- Interim List of Eligible Programmes (ILEP) page

**f. Change-signal feeds are a design option.** The Federal Register publishes rules and notices and has a documented API; USCIS, ICE and the State Department publish news and alerts. Watching these could warn us about a rule change before the rule pages are updated. Not verified for use here (access, rate limits, terms); a topic for the design doc.

## 7. Known gaps against the eval questions

- **F09 (visa interview documents):** the only current official source I found is the State Department student visa page, which covers the DS-160 confirmation page, the I-20, a photo and interview scheduling. The dedicated Study in the States interview pages are 2018 and 2019 posts, which are excluded. Embassy-specific checklists exist per consulate; they are origin-dependent and out of v0.1.
- **F13 (days to file after graduation):** expected to be covered by the OPT pages; to be verified when expected facts are written.
- **Internship authorisation (F05):** covered by the practical-training sources; the pathway graph needs a CPT node.
- **University-dependent questions (F01, F02, F07, F08):** no source here covers them; see the Eval Plan scope decision.

## 8. Candidates considered and left out

| Candidate | Reason |
|---|---|
| eCFR 8 CFR 214.2 (full section) | Very long and covers every nonimmigrant class; needs section-level extraction. The F-1 text is covered by `us-ice-sevp-regs` |
| ICE CPT fact sheet (PDF) | PDF |
| Study in the States 2015, 2018 and 2019 interview and fee posts | Dated posts, older than the current guidance |
| Study in the States "F-1 Postsecondary" guide (3,178 days) | Legacy guide that still describes the old duration-of-status model |
| State Department reciprocity-fee page | Built around a drop-down tool; the extractor cannot run it |
| USCIS I-9 handbook pages | Written for employers |
| SEVIS Help Hub pages | Written for school officials |
| H-1B characteristics reports | Statistics, not rules |
| Education in Ireland ambassador blogs | Personal blog posts |
| Embassy "supplement by post" pages | Origin-dependent; out of v0.1 |

## 9. Maintenance

- Review this registry at each milestone and whenever the freshness job flags a source.
- Add a row before adding a URL to any TOML file. A URL without a row has no owner.
- Re-check page ages monthly; sources older than 18 months get a manual read.
