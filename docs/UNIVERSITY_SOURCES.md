# DISHAA: Pilot University Sources (CU Denver and UCD)

**Status:** Draft v1 · **Date:** 2026-11-21 · **Related:** [University Catalog](UNIVERSITY_CATALOG.md) · [Source Registry](SOURCE_REGISTRY.md) · ADR-020, ADR-021, ADR-022 · Risk R22
**Lists:** [`sources/cu_denver.toml`](../sources/cu_denver.toml) (17) · [`sources/ucd.toml`](../sources/ucd.toml) (14)

## 1. How these were checked

Same limits as the main registry. Every URL came from an official-domain web search on 2026-11-21 and appears in the index with a title and snippet. **None has been fetched or extracted by our pipeline, and none has been read in full.** The notes below come from search snippets only, so every "hook" is a question to settle by reading the page, not a fact to state. Topics follow ADR-020: admissions, fees, payment plans, health insurance, on-campus housing, plus the university's own immigration-office pages for CU Denver.

## 2. CU Denver (17 sources)

| ID | Topic | Tier | Age (days) | Hook to read for |
|---|---|---|---|---|
| cud-elp | admissions | core | | University minimum test scores exist, but programmes may set higher ones |
| cud-intl-costs-grad | fees | core | | 2026-27 cost estimates assume 6 credit hours a semester for most graduate programmes; check what that means for full-time students |
| cud-grad-tuition | fees | core | | Hub for year-specific tables; the 2026-27 table URL was not found |
| cud-cost-of-attendance | fees | core | | Estimates, not bills |
| cud-bursar-faq | payment | core | | Deferred payment plan; instalment count |
| cud-pay-your-bill | payment | core | | International payment route and card service fee |
| cud-sponsored-financial-responsibility | payment | core | | Charges a sponsor does not cover |
| cud-health-requirements | insurance | core | | Mandatory for F-1 and J-1 |
| cud-health-waiver | insurance | core | | Waiver conditions, deadlines each term |
| cud-health-dates-costs | insurance | core | | Rates by term; year not stated in snippet |
| cud-health-resources | insurance | supporting | | |
| cud-student-affairs-policies | insurance | supporting | | Policy 7010 listing, not the policy text |
| cud-housing-faq | housing | core | | Contract terms and cancellation |
| cud-lynx-crossing-rates | housing | core | | Fall 2026 to Spring 2027 rates |
| cud-isss-students | immigration | supporting | | Hub |
| cud-cpt | immigration | core | | **A new CPT policy followed DHS guidance of August 12, 2026, and the CPT eligibility course was unavailable.** Read before stating any CPT rule |
| cud-maintaining-status | immigration | core | | Insurance and status rules in one place |

### Exception traps visible already

1. **Test scores:** a university minimum plus programme-specific minimums. A department page shows a different TOEFL minimum and subscore floors from the university table, and the One Year MBA FAQ shows another (90 iBT or 6.5 IELTS). The answer must say "your programme may require more".
2. **Health insurance:** mandatory for F-1 and J-1, with a waiver that must be requested each term and that has requirements. One 2025-26 fee table says the insurance charge also applies to students on practical training (OPT). The ISSS rates page lists two terms and a summer rate without naming the academic year, while the fee table is for 2025-26. These may disagree, so they must be reconciled before any amount is stated (compare R21).
3. **Housing:** the resident handbook says the contract binds for the entire academic year. That is a PDF (deferred) and the HTML FAQ must be read to see whether it says the same.
4. **CPT:** policy changed in August 2026 (above). This is also a freshness canary for the review queue.

### Gaps

- **Current graduate admissions requirements** (GPA, test requirements; question F01): only the 2024-25 and 2022-23 catalog PDFs were found, and both are dated. The current catalog HTML page is not yet located.
- **2026-27 graduate tuition table** and the **payment plan landing page** were not found by URL.
- **The ISSS "Immigration Updates" page** is referenced by the CPT page and is not yet located. It probably holds the CPT policy text.
- **Legacy and duplicate URLs left out:** an old `ucdenver.edu/tuition-cost/cost-of-attendance` page (1,397 days), the old Flywire payments page, the ISSS housing page (3,293 days), and 2025-26 year-specific fee pages.

## 3. UCD (14 sources)

| ID | Topic | Tier | Age (days) | Hook to read for |
|---|---|---|---|---|
| ucd-grad-entry | admissions | core | | Standard English test minimums; some courses require more |
| ucd-global-apply-faqs | admissions | core | | |
| ucd-fees-noneu | fees | core | | Hub; fees for multi-year programmes stay at the start-year rate |
| ucd-fees-noneu-ug-2026-27 | fees | core | | A €5 levy is **not** included in the published fees |
| ucd-fees-noneu-gradresearch-2026-27 | fees | core | | Some programmes are exceptions to the college rate |
| ucd-fees-noneu-certdip-2026-27 | fees | supporting | | |
| ucd-living-costs | fees | supporting | | Residence permit and insurance estimates; cross-check against the Irish immigration pages |
| ucd-fee-deadlines | payment | core | | Instalments depend on how many trimesters the programme has |
| ucd-deposit | payment | core | | Deposits are non-refundable; amount varies by course |
| ucd-health-insurance | insurance | core | | Non-EEA students must hold private insurance |
| ucd-offerholder-faqs | insurance | supporting | | |
| ucd-residences-fees-payments | housing | core | 131 | Pay in full or monthly instalments |
| ucd-residences-faqs | housing | core | | Allocation priorities |
| ucd-global-oncampus | housing | core | | Not guaranteed for all international students |

### Exception traps visible already

1. **Instalments:** one-trimester and per-credit programmes pay in full in advance, while two- and three-trimester programmes pay in instalments. A generic "you can pay in instalments" answer is wrong for some students.
2. **Published fees exclude a €5 levy**, so "the fee is X" needs that caveat.
3. **English tests:** standard minimums, with higher options for some graduate taught programmes (in a PDF, deferred).
4. **Accommodation:** guaranteed for some groups, not for all international students. The answer depends on level and year.
5. **Cross-tier link:** the UCD offer pack (a PDF, deferred) mentions a rule from the immigration side about paying fees in full or a minimum deposit before a student visa is issued. This is the same issue as the Irish student finance rules in the main registry, so the university answer and the immigration answer must agree. **This is the kind of fact that is in a PDF and matters, so it is the first candidate for promotion under ADR-021.**

### Gaps

- **Non-EU graduate taught fees 2026/27**: no such page was found. The founder's likely audience is master's students, so this is the most important missing page.
- **Left out:** PDFs (English language requirements document, international prospectus, offer pack, accommodation price lists), a test-host copy of the residences page (`elatest.ucd.ie`) that still describes 2024/25, and school-level pages (individual departments).

## 4. What this does not prove

Finding a page in a search index does not show that the extractor can read it, that robots.txt allows collection, or that the page is current. Section 2's insurance rates and section 3's fee rules are the first things to check by eye after `dishaa-fetch` runs for these two lists on your machine.

## 5. Next steps

1. Founder runs `dishaa-fetch` on `sources/cu_denver.toml` and `sources/ucd.toml`, then `dishaa-chunk --show <id>` on a few pages.
2. Locate the missing pages in section 2 and 3 gaps (UCD non-EU graduate taught fees first).
3. Read each core page in full, record its date, and only then write expected facts for eval cases F01, F02, F07, F08 and F11.
