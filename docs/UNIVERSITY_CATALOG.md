# DISHAA: University Catalog

**Status:** Draft v1 · **Date:** 2026-11-21 · **Related:** ADR-020, ADR-022, [Risk Register](RISK_REGISTER.md) R22

## 1. What the founder asked for

The top 500 US universities and the top 100 Irish ones, ranked by international students, and all of them covered. This document records what we found and how the request fits the release plan.

## 2. Ireland: the list is about 25, not 100

Ireland does not have 100 higher-education institutions. Two official lists give these counts:

- The Higher Education Authority (HEA) lists **17 current** institutions (plus 14 archived institutes of technology that have merged into technological universities): https://hea.ie/higher-education-institutions/
- The Department's publicly-funded list names 12 universities and technological universities and 11 other institutions, which adds 7 not on the HEA current list: https://www.gov.ie/en/department-of-further-and-higher-education-research-innovation-and-science/publications/list-of-publicly-funded-higher-education-institutions-universities-and-colleges/

`sources/universities/ie_institutions.csv` holds all **24** (17 + 7). No ranking is applied, because a ranking of 24 adds little. The official website of each institution is left blank on purpose: it has not been verified yet, and a guessed URL would be an unreviewed source. Privately funded colleges that serve international students are not on either list and are not included. Whether to add them is an open question.

## 3. USA: 350 institutions, not 500

Source: IIE Open Doors 2025 International Student Census Tables (2024/25 data), supplied by the founder. Table 17 lists every institution hosting 1,000 or more international students, and that is **240** institutions (smallest has 1,006). Tables 12 to 16 add each institution class's top list, which brings in **110** more institutions below 1,000. Together that is **350** unique institutions in `sources/universities/us_institutions.csv`, ranked by 2024/25 international students.

**This file cannot give 500.** Below about 1,000 students only the class top-lists exist, so ranks past 350 are not in this data. Reaching 500 needs another source: IPEDS fall enrollment of U.S. nonresident students covers all institutions (NCES). Our build environment cannot download it, so the founder would need to download it.

Notes:
- **Ranks 1 to 240 are a true ranking. Ranks 241 to 350 are not**: they are only the top of each institution class, so a school with 900 students in a crowded class may be missing while a school with 90 in a small class is listed. Treat 241 to 350 as "included, order approximate".
- Names follow Open Doors (for example "Arizona State University - Campus Immersion"), not necessarily the school's own spelling. Official sites are blank until verified.
- Counts are as reported to Open Doors for 2024/25. Whether Open Doors terms allow republishing the table is not checked: the CSV holds names and counts only and credits IIE, but read their terms before making the repo public.

## 4. Coverage ladder

"Cover them all" is accepted as the direction. It is staged, so the freshness problem is not pushed out of v0.1:

| Level | Meaning | Target |
|---|---|---|
| listed | Name in the intake picker. The answer is "not covered yet, check your university's website" | All |
| registered | Official admissions, tuition, fees, insurance and housing pages are in the source registry and fetched | Waves of about 10, most international students first |
| curated | Pages inspected by eye, exceptions tagged, eval cases written | Pilot first (1 to 2), then each wave |

Release gate for moving a university up a level is the same as for any source: read in full, page age recorded, eval cases pass.

## 5. Open items

- Decide whether 350 is enough for the US or whether to add the IPEDS list to reach 500.
- Check IIE's terms of use before the repo goes public.
- Decide whether privately funded Irish colleges are in the list.
- Choose the pilot universities from the top of the list.
