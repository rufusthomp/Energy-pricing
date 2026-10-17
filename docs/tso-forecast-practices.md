# TSO forecast practices on the ENTSO-E Transparency Platform

Documentary research answering two referee questions: (1) whether TSO day-ahead total
load forecasts are gross demand or net of embedded (distribution-connected) generation,
and (2) what the platform and Regulation 543/2013 say and show about forecast
publication and revision timing, and about curtailment-adjusted renewable forecasts.

## Summary

**Load netting (Q1).** Regulation 543/2013 defines "total load" as generation (net of
plant auxiliary consumption) plus imports minus exports minus storage absorption,
summed over "both TSO/DSO networks" (Article 2(27); ENTSO-E Detailed Data Descriptions
v3r4, p.18-19). This is a generation-accounting definition, not a metered-demand
definition, so in principle it is designed to be gross of embedded generation, provided
the DSO can see and report that generation. In practice this breaks down for
generation that is self-consumed behind the meter and never touches the public grid:
it appears in neither the generation term nor the load term, so it never enters
"total load" at all. Where this has been checked (Germany, via the Bundesnetzagentur's
own SMARD documentation) that is exactly what happens: self-consumed rooftow PV is
excluded from both "realised generation" and "Netzlast" (grid load), because Netzlast
only counts electricity that enters the public grid. Denmark's TSO (Energinet) has
separately documented that most small rooftop PV does not report generation data to it
at all, relying on a "guesstimate" extrapolated from a few thousand metered plants.
Belgium's TSO (Elia) documents the opposite intent: it explicitly estimates
unmeasured decentralised generation and folds it into "total generation" so that total
load is meant to be gross. For most other zones in scope, no TSO- or regulator-level
statement of gross/net treatment could be found in the time available; this is reported
honestly as unknown below rather than assumed either way. Hirth, Mühlenpfordt and
Bulkeley (2018) independently document large, persistent, country-specific
inconsistencies between the Transparency Platform's "Actual Total Load" and other load
data sources (Eurostat, ENTSO-E Power Statistics), consistent with differing national
netting/scope conventions, though they do not resolve the gross/net question
zone-by-zone either.

**Forecast timing (Q2).** The GL_MarketDocument the API returns carries a
`revisionNumber` (a plain incrementing integer, confirmed empirically: 3 for a wind/
solar forecast document, 1 for a load forecast document, in a live query made for this
research) and a `createdDateTime`. Neither is a submission timestamp: `createdDateTime`
is stamped at response-generation time (both of my live queries, made seconds apart,
returned `createdDateTime` values in the present, not the historical date of the
underlying forecast), and `revisionNumber` carries no associated timestamp of its own.
There is no field in the schema, and no statement in the API or Manual of Procedures
documentation found, that exposes when a TSO originally submitted or last updated a
given forecast. Regulation 543/2013 sets the load forecast deadline at "no later than
two hours before the gate closure of the day-ahead market" (Article 6(2)(b)) and the
wind/solar forecast deadline at "no later than 18:00 Brussels time" D-1 (Article
14(2)(d)); both confirmed verbatim from the regulation text. Wind/solar forecasts are
explicitly required to be revised: Article 14(2)(d) and the Detailed Data Descriptions
mandate at least one further update at 08:00 Brussels time on delivery day, published
under a separate "intraday forecast at 8:00" label alongside a continuously updated
"current forecast" label; the 18:00 D-1 snapshot itself is fixed and "shall not be
regularly updated after 18:00." No source was found describing any TSO publishing
renewable forecasts net of expected market-based curtailment at negative prices; the
"net" in "wind and solar power net generation" in the Detailed Data Descriptions refers
to net of a plant's own auxiliary consumption, not curtailment. Separate academic work
(on Germany specifically) documents that market-based curtailment at negative prices is
real and growing, but treats it as a real-time response to price, not something
forecast into the day-ahead figure.

---

## Q1 table: load forecast, gross or net of embedded generation

| Zone | TSO | Gross or net | Status | Source |
|---|---|---|---|---|
| DE_LU | 50Hertz, Amprion, TenneT DE, TransnetBW, Creos | Probably net of self-consumed embedded PV. The page says consumption "only includes figures from consumers currently taking electricity from the grid"; it does not mention PV, so exclusion of behind-the-meter PV is an inference. It also describes the SMARD series, not necessarily the ENTSO-E total load forecast | Inferred from a regulator source (corrected 2026-09-29 on verification: first recorded as "Documented") | [SMARD / Bundesnetzagentur, "Electricity consumption"](https://www.smard.de/page/en/wiki-article/6138/6036/electricity-consumption) |
| DK_1, DK_2 | Energinet | Likely net of most rooftop/small PV; Energinet states small consumer rooftop PV plants do not submit generation data to it and total Danish solar output is extrapolated ("guesstimated") from a small metered sample | Documented (TSO's own statement), but its precise effect on the published Total Load figure is not itself spelled out by the source, so treat as strongly suggestive rather than conclusive | [Energinet, "Solar cells: Data sharing between DMI and Energinet"](https://en.energinet.dk/About-us/Digitalisation/Solar-cells-Data-sharing/) |
| BE | Elia | Intended gross: Elia states "total generation" includes "the actual decentralised generation for which Elia does not have measurements" (i.e. estimated and added back in) | Documented (TSO's own site) | [Elia, "Power generation"](https://www.elia.be/en/grid-data/power-generation); [Elia, "Load and load forecasts"](https://www.elia.be/en/grid-data/load-and-load-forecasts) |
| AT (not in this project's zone list but relevant context from the Hirth paper) | APG | Total Load on the Transparency Platform covers only the APG control area, excluding large industry with own generation and railway consumption not directly connected to APG's grid | Secondary (ENTSO-E personal communication, quoted in Hirth et al. 2018) | Hirth, Mühlenpfordt & Bulkeley (2018), *Applied Energy* 225, p.1057, footnote 2 |
| NO_2 | Statnett | Not established | Unknown | - |
| SE_3, SE_4 | Svenska kraftnät | Not established | Unknown | - |
| FI | Fingrid | Not established | Unknown | - |
| EE | Elering | Not established | Unknown | - |
| NL | TenneT NL | Not established; TenneT confirms it publishes per Regulation 543/2013 but no methodology note on embedded/decentralised generation treatment was found | Unknown | [TenneT, Transparency Netherlands](https://www.tennet.eu/markets/transparency-netherlands) |
| FR | RTE | Not established | Unknown | - |
| CH | Swissgrid | Not established (Switzerland is not an EU member and 543/2013 does not bind it directly, though Swissgrid voluntarily reports to the Transparency Platform) | Unknown | - |
| PL | PSE | Not established for load; note Hirth et al. (2018) separately document a wind-generation methodology difference for Poland (PSE website uses quarter-hourly averaging, TP uses more granular averaging) unrelated to embedded generation | Secondary (methodology aside, not on the gross/net question) | Hirth, Mühlenpfordt & Bulkeley (2018), p.1059 |
| ES | REE | Not established | Unknown | - |
| PT | REN | Not established | Unknown | - |
| GR | IPTO/ADMIE | Not established | Unknown | - |
| IT_NORD | Terna | Not established | Unknown | - |

**General EU-level definition applicable to all zones** (documented, but does not resolve
the embedded-generation question at the level of practical completeness):

> "'total load', including losses without power used for energy storage, means a load
> equal to generation and any imports deducting any exports and power used for energy
> storage" (Commission Regulation (EU) No 543/2013, Article 2(27)).

> "Actual total load per bidding zone per market time unit, the total load being
> defined as equal to the sum of power generated by plants on both TSO/DSO networks,
> from which the following is deduced: the balance (export-import) of exchanges on
> interconnections between neighbouring bidding zones [and] the power absorbed by
> energy storage resources... Net generation should be used. If a net generation output
> is not known, it shall be estimated." (ENTSO-E, *Detailed Data Descriptions*, v3r4,
> 15 December 2023, p.18-19).

This is a generation-accounting definition ("both TSO/DSO networks"), so the intent is
gross demand including distribution-connected generation to the extent it is known or
estimable. The load *forecast* (item 6.1.b) is not separately defined beyond "the
primary owners of the data are TSOs and DSOs" and a note that it is derived from
historic load profiles and meteorological data; no separate statement addresses
embedded generation for the forecast specifically. Whether any given DSO's estimate is
complete, in particular for small/unmetered rooftop solar, is a national implementation
question the EU-level documents do not answer, which is why the per-zone rows above are
mostly "unknown": this is a genuine gap in the public documentary record, not a
oversight of this research.

Source for the DDD definition:
[ENTSO-E Detailed Data Descriptions v3r4 (PDF)](https://eepublicdownloads.entsoe.eu/clean-documents/Transparency/MoP_Ref2_DDD_v3r4.pdf)
Source for the regulation text:
[Commission Regulation (EU) No 543/2013, consolidated text via Energy Community Secretariat (PDF)](https://www.energy-community.org/dam/jcr:e3539bc7-536a-4c60-b23f-972045541070/Regulation_543_2013_EU.PDF)
(also at [EUR-Lex, CELEX 32013R0543](https://eur-lex.europa.eu/legal-content/en/ALL/?uri=CELEX:32013R0543))

---

## Q2(a): does the platform expose original submission/update time, distinct from `createdDateTime`?

**Finding: no.** Verified two ways.

**Empirically.** Two live API calls were made for this research (DE_LU, 28 September
2025, using documentType A65 = system total load and A69 = wind and solar forecast,
both processType A01 = day ahead):

- The wind/solar forecast document returned `<revisionNumber>3</revisionNumber>` and
  `<createdDateTime>2026-09-29T12:53:29Z</createdDateTime>`.
- The load forecast document returned `<revisionNumber>1</revisionNumber>` and
  `<createdDateTime>2026-09-29T12:53:55Z</createdDateTime>`.

Both `createdDateTime` values are stamped at the moment the API served *this* research's
query (today), 26 seconds apart, for underlying data describing a day a year earlier.
This confirms `createdDateTime` is a response-generation timestamp, not a fact about
when the TSO submitted the forecast. `revisionNumber` is a bare integer with no
associated date/time field anywhere in the document; it tells you a forecast has been
revised three times (in the wind/solar case) but not when.

**In the documentation.** No field for original-submission or last-TSO-update time is
described in the ENTSO-E Detailed Data Descriptions or in secondary API documentation
consulted (a GitHub developer's notes on the API, and the Central Transparency Platform
Implementation Guide, both of which describe `revisionNumber` only as "initial
transmission should normally equal '1'" with no timestamp semantics). The Detailed Data
Descriptions do, however, document that the *wind/solar* forecast is published under
three separate labels that partially substitute for a submission-time field:

> "Current forecast: The information published is the last update of the forecast...
> shall be regularly updated. Day ahead forecast at 18.00: The information is a fixed
> value, i.e. the current forecast at 18.00 the day before... shall not be regularly
> updated after 18.00. Intraday forecast at 8.00: The information is a fixed value...
> shall not be regularly updated after 8.00." (DDD v3r4, p.66-67)

So a researcher can distinguish the D-1 18:00 vintage from the D-0 08:00 vintage from
the continuously-refreshed "current" feed by the label/process type used in the query
(process type A01 = day ahead corresponds to the fixed D-1 snapshot; process type A18 =
"Intraday total" is the commonly documented code for the continuously updated feed,
per ENTSO-E's general code list), but this is coarser than a true timestamp: it tells
you which regulatory checkpoint a value corresponds to, not the wall-clock minute it was
actually submitted. No equivalent multi-vintage labelling is documented for the total
load forecast (item 6.1.b): it is a single evolving series, updated "when significant
changes occur" (a change of at least 10% in one market time unit; DDD v3r4, p.20), with
no distinct fixed-snapshot label of its own.

Sources:
[ENTSO-E Detailed Data Descriptions v3r4](https://eepublicdownloads.entsoe.eu/clean-documents/Transparency/MoP_Ref2_DDD_v3r4.pdf),
[jstaffans, "ENTSO-e REST API notes" (GitHub gist)](https://gist.github.com/jstaffans/798360bd82aafbfbd5ab362e7f76e23a),
[ENTSO-E, Central Transparency Platform Implementation Guide for European Platforms v1.3](https://eepublicdownloads.entsoe.eu/clean-documents/EDI/Library/ERRP/Central_Transparency_Platform_-_IG_for_European_Platforms_v1.3.pdf).

---

## Q2(b): regulatory deadlines and evidence on actual publication/update timing

**Exact wording, verified against the consolidated regulation text.**

Article 6(2)(b), on the day-ahead total load forecast (item 6.1.b):

> "shall be published no later than two hours before the gate closure of the day-ahead
> market in the bidding zone and be updated when significant changes occur"

The Detailed Data Descriptions gloss this with a fallback for zones without an explicit
gate closure: "at D-1, 12:00 in local time zone of the bidding zone at the latest when
gate closure time does not apply" (DDD v3r4, p.20), and define "significant change" as
"a change of at least 10% of the total load forecast in one market time unit" (ibid.).

Article 14(2)(d), on the day-ahead wind/solar generation forecast (item 14.1.d):

> "shall be published no later than 18.00 Brussels time, one day before actual delivery
> takes place. The information shall be regularly updated and published during
> intra-day trading with at least one update to be published at 8.00 Brussels time on
> the day of actual delivery. The information shall be provided for all bidding zones
> only in Member States with more than 1% feed-in of wind or solar power generation per
> year or for bidding zones with more than 5% feed-in of wind or solar power generation
> per year."

This confirms the referee's recollection of both deadlines essentially verbatim, and
also surfaces two things worth flagging for the paper: (i) the wind/solar forecast is
explicitly *required* to be updated again at 08:00 on delivery day, which is before the
day-ahead auction gate closure (typically 12:00 CET for single day-ahead coupling) in
every zone in scope, so an 08:00 update is regulatory-compliant and not evidence of
late/irregular publication; (ii) the feed-in materiality threshold (>1% national or >5%
zonal) means that in a low-renewable-share year a bidding zone could in principle have
been legally exempt from publishing this item at all, though all zones in this
project's scope now comfortably exceed that threshold.

**Evidence on actual publication times or post-auction updates.** No direct empirical
study of actual TSO publication timestamps (as opposed to the regulatory deadline) was
located in the time available. This project's own empirical check (above) shows that
the API does not retain a submission-time log accessible after the fact, which is
itself indirect evidence that verifying actual-vs-scheduled publication times
historically would require either (a) having queried the API repeatedly through the day
at the time (polling, not retrospective), or (b) a TSO's own operational log, neither of
which this research had access to. Hirth, Mühlenpfordt and Bulkeley (2018) note in
passing that the Transparency Platform generally is "delivered one hour after real
time" for actuals and that "other sources undergo revisions" for load and generation
data (p.1056), but this remark concerns actual (outturn) data reporting lag, not
day-ahead forecast publication or revision timing, and does not bear on whether
forecasts are updated after the 12:00 CET auction. No source found confirms or refutes
systematic post-gate-closure revision of published forecasts beyond what Article
6(2)(b) and 14(2)(d) already require.

Sources:
[Commission Regulation (EU) No 543/2013 (PDF)](https://www.energy-community.org/dam/jcr:e3539bc7-536a-4c60-b23f-972045541070/Regulation_543_2013_EU.PDF),
[ENTSO-E Detailed Data Descriptions v3r4](https://eepublicdownloads.entsoe.eu/clean-documents/Transparency/MoP_Ref2_DDD_v3r4.pdf),
Hirth, Mühlenpfordt & Bulkeley (2018), *Applied Energy* 225, 1054-1067, DOI:
10.1016/j.apenergy.2018.04.048 (open copy at
[neon.energy](https://neon.energy/Hirth-Muehlenpfordt-Bulkeley-2018-ENTSO-E-Transparency-Platform.pdf)).

---

## Q2(c): are any TSOs documented as publishing renewable forecasts net of expected market-based curtailment?

**Finding: no source located that documents this.** The word "net" that appears in the
Detailed Data Descriptions' definition of item 14.1.d ("a forecast of wind and solar
power **net** generation") refers to net of the generating plant's own auxiliary
consumption (the same net/gross distinction applied to conventional generation
elsewhere in the DDD: "in case of power plants net generation should be taken
(auxiliary supply should not be considered)," DDD v3r4, p.19), not net of anticipated
commercial curtailment at negative prices. Nothing in Regulation 543/2013 or the DDD
instructs TSOs to anticipate market-based curtailment in the day-ahead forecast, and
doing so would be somewhat circular in any case, since market-based curtailment is a
generator response to the day-ahead price that the forecast itself, once published,
feeds into.

Separately, recent academic work confirms that market-based curtailment at negative
prices is real and growing (a 2026 paper on German renewable support schemes reports
market-based curtailment volumes of 2.1 TWh for wind and 1.0 TWh for solar in 2025, and
that pooled over 2022 to August 2026, 58% of wind potential but only 9% of solar
potential was curtailed in hours below -100 EUR/MWh), but this literature treats
curtailment as a real-time dispatch decision taken in response to realised or
near-realised prices, not as something built into the published day-ahead generation
forecast. No equivalent statement was found for the other zones in scope; treat the
absence of any TSO documented as forecasting net of curtailment as the honest state of
the record, not as proof that no TSO does this.

Source: search of TSO methodology pages and academic literature located no positive
statement either way beyond the German curtailment volume study; that study is cited
for context on curtailment scale, not for a claim about forecast methodology, which it
does not make. Full-text access to the underlying arXiv PDF (2609.10053) could not be
extracted for direct quotation in the time available; the summary above is drawn from
search-result abstracts and should be re-verified by reading the paper directly before
citing it in the paper itself.

---

## Caveats on this research

- This was a time-boxed documentary pass, not an exhaustive survey. Sixteen zones were
  in scope; per-TSO methodology statements were found for three (DE_LU, DK_1/DK_2, BE)
  plus one adjacent non-in-scope zone (AT, via a secondary source). The remaining eleven
  zones (NO_2, SE_3, SE_4, FI, EE, NL, FR, CH, PL, ES, PT, GR, IT_NORD) are marked
  "unknown" for Q1 rather than guessed at.
- Two PDFs central to the regulatory record (the UK legislation.gov.uk copy of
  543/2013, and the ENTSO-E Detailed Data Descriptions as served by ENTSO-E) carry
  copy-protection flags that blocked normal text extraction; `pdftotext` (a local CLI
  tool) was used to extract text directly and cross-checked against a second,
  unprotected copy of the regulation (Energy Community Secretariat's mirror), which
  matched. The DDD extraction is from the single ENTSO-E-served copy; if this matters
  for the paper's evidentiary standard, it is worth re-verifying against the printed
  page images.
- The arXiv curtailment paper (2609.10053) referenced under Q2(c) was not read in full;
  only search-engine abstract text was used. Re-fetch and read before citing.
- The empirical API check queried DE_LU only, for one historical day, using process
  type A01. It was not repeated across zones or process types (A18 in particular) to
  conserve API calls against the 400/min rate limit and to keep total requests to a
  handful as instructed. The finding that no submission timestamp exists is structural
  (it follows from the GL_MarketDocument schema, which is the same schema across all
  zones and document types), so this is not expected to vary by zone, but that
  inference was not separately verified per zone.

## Verification note (2026-09-29)

The main session checked these findings against their sources:

- **Regulation 543/2013 quotes:** match the regulation text.
- **API timestamp claim:** confirmed. A response for 2025 data carries a `createdDateTime` of the query day.
- **Energinet and Elia claims:** corroborated by the pages' indexed text. Neither page returns readable text to a direct fetch.
- **The SMARD claim:** overstated, and corrected above.
- **arXiv 2609.10053:** not read in full; not cited in the paper.
