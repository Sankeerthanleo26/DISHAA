# DISHAA: University Catalog

**Status:** Draft v1 · **Date:** 2026-11-21 · **Related:** ADR-020, ADR-022, [Risk Register](RISK_REGISTER.md) R22

## 1. What the founder asked for

The top 500 US universities and the top 100 Irish ones, ranked by international students, and all of them covered. This document records what we found and how the request fits the release plan.

## 2. Ireland: the list is about 25, not 100

Ireland does not have 100 higher-education institutions. Two official lists give these counts:

- The Higher Education Authority (HEA) lists **17 current** institutions (plus 14 archived institutes of technology that have merged into technological universities): https://hea.ie/higher-education-institutions/
- The Department's publicly-funded list names 12 universities and technological universities and 11 other institutions, which adds 7 not on the HEA current list: https://www.gov.ie/en/department-of-further-and-higher-education-research-innovation-and-science/publications/list-of-publicly-funded-higher-education-institutions-universities-and-colleges/

`sources/universities/ie_institutions.csv` holds all **24** (17 + 7). No ranking is applied, because a ranking of 24 adds little. The official website of each institution is left blank on purpose: it has not been verified yet, and a guessed URL would be an unreviewed source. Privately funded colleges that serve international students are not on either list and are not included. Whether to add them is an open question.

## 3. USA: list not yet built

The ranking source is the IIE Open Doors census (Table 11, "Leading Institutions"): https://opendoorsdata.org/wp-content/uploads/2025/11/OD25_Intl-Student-Census_Tables.xlsx

Our build environment cannot download that file (the shell network allowlist blocks it, and the web fetch tool cannot read spreadsheets). Two things are unknown until the file is read:
1. Whether Table 11 lists 500 institutions or fewer.
2. Its column layout.

Fallback if it lists fewer than 500: IPEDS fall enrollment of U.S. nonresident students, which covers all institutions (NCES).

## 4. Coverage ladder

"Cover them all" is accepted as the direction. It is staged, so the freshness problem is not pushed out of v0.1:

| Level | Meaning | Target |
|---|---|---|
| listed | Name in the intake picker. The answer is "not covered yet, check your university's website" | All |
| registered | Official admissions, tuition, fees, insurance and housing pages are in the source registry and fetched | Waves of about 10, most international students first |
| curated | Pages inspected by eye, exceptions tagged, eval cases written | Pilot first (1 to 2), then each wave |

Release gate for moving a university up a level is the same as for any source: read in full, page age recorded, eval cases pass.

## 5. Open items

- Founder to download the Open Doors file, or attach it here, so the US list can be built and counted.
- Decide whether privately funded Irish colleges are in the list.
- Choose the pilot universities from the top of the list.
