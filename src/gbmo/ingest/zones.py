"""Which bidding zones the panel covers, and how ENTSO-E production types collapse.

The hand-curated modelling layer for the cross-country work, sitting alongside
`reference.py` as `weather_location` sits alongside `fuel`. Nothing here is observed;
it is all choice, and it is kept in one place so the choices are reviewable.

## Why bidding zones rather than countries

Price forms at bidding-zone level, not national level, and several countries are split.
Denmark is two zones on different synchronous areas: DK1 in the west runs with
Continental Europe, DK2 in the east with the Nordics, and they clear at different prices
on most days. Sweden has four, Norway five, Italy several. Averaging DK1 and DK2 into
"Denmark" would construct a price series no participant ever faced.

The zone carries its ISO country code so aggregating up stays available; going the other
way, from a national average back to zones, is not.
"""

# (code, country, name, timezone, currency, why it is in the panel)
#
# `currency` is the currency ENTSO-E publishes that zone's day-ahead price in. It is an
# assertion, not an observation, so `entsoe.verify_currencies` checks every one of these
# against the raw XML before the first load and fails loudly on a mismatch. Do not add a
# zone without running it.
ZONES = [
    # The bridge back to the existing study. GB appears in both pipelines, which makes
    # the Elexon build and this one checkable against each other for free.
    ("GB",      "GB", "Great Britain",        "Europe/London",     "GBP",
     "Cross-pipeline consistency check against the Elexon MID series"),

    # High renewable penetration: the treated end of the variation.
    ("DK_1",    "DK", "Denmark West",         "Europe/Copenhagen", "EUR",
     "Highest wind share in Europe; synchronous with Continental Europe"),
    ("DK_2",    "DK", "Denmark East",         "Europe/Copenhagen", "EUR",
     "High wind, but Nordic-synchronous: a near-matched comparison with DK1"),
    ("IE_SEM",  "IE", "Ireland (SEM)",        "Europe/Dublin",     "EUR",
     "Very high wind share on a small, weakly interconnected island system"),
    ("DE_LU",   "DE", "Germany-Luxembourg",   "Europe/Berlin",     "EUR",
     "Large, liquid, high VRE. Zone exists only from 2018-10-01 (see docs)"),
    ("ES",      "ES", "Spain",                "Europe/Madrid",     "EUR",
     "High solar and wind; also the 2022 Iberian gas cap, a discrete policy event"),
    ("PT",      "PT", "Portugal",             "Europe/Lisbon",     "EUR",
     "Shares the Iberian market and the gas cap with ES"),
    ("NL",      "NL", "Netherlands",          "Europe/Amsterdam",  "EUR",
     "Fast solar growth against a gas-marginal stack"),
    ("GR",      "GR", "Greece",               "Europe/Athens",     "EUR",
     "Rapid solar build-out from a low base"),

    # Low renewable penetration: the control end.
    ("FR",      "FR", "France",               "Europe/Paris",      "EUR",
     "Nuclear baseload, low VRE: the flat-mix control"),
    ("PL",      "PL", "Poland",               "Europe/Warsaw",     "PLN",
     "Coal-dominated, low VRE: the fossil control"),
    ("CZ",      "CZ", "Czech Republic",       "Europe/Prague",     "EUR",
     "Coal and nuclear, low VRE"),
    ("BE",      "BE", "Belgium",              "Europe/Brussels",   "EUR",
     "Nuclear with rising offshore wind: mid-range, and a phase-out to exploit"),

    # Hydro-rich zones. Storage-adjacent, and the point of contrast for a battery study:
    # somewhere the arbitrage these batteries do is already being done at scale.
    ("NO_2",    "NO", "Norway South-West",    "Europe/Oslo",       "EUR",
     "Reservoir hydro; interconnected to both GB and DE"),
    ("SE_3",    "SE", "Sweden South-Central", "Europe/Stockholm",  "EUR",
     "Hydro and nuclear; the Swedish demand centre"),
    ("SE_4",    "SE", "Sweden South",         "Europe/Stockholm",  "EUR",
     "Price-separated from SE3 and much windier: within-country variation"),
    ("AT",      "AT", "Austria",              "Europe/Vienna",     "EUR",
     "Alpine hydro, including large pumped storage"),
    ("CH",      "CH", "Switzerland",          "Europe/Zurich",     "EUR",
     "Hydro and nuclear, and Europe's deepest pumped-storage fleet"),
    ("IT_NORD", "IT", "Italy North",          "Europe/Rome",       "EUR",
     "Gas-marginal with growing solar; the Italian demand centre"),

    # Nordic and Baltic, for volatility range.
    ("FI",      "FI", "Finland",              "Europe/Helsinki",   "EUR",
     "Nuclear plus fast wind growth; extreme price spikes"),
    ("EE",      "EE", "Estonia",              "Europe/Tallinn",    "EUR",
     "Small, volatile, and desynchronised from Russia in Feb 2022"),
]

ZONE_CODES = [z[0] for z in ZONES]

# ENTSO-E reports ~20 production types per zone-hour. Storing all of them across the
# panel is ~46M rows; collapsing to these seven is ~3M. The full response is kept in the
# CSV cache, so changing this mapping is a reload, not a re-fetch. See docs/data-scaling.md.
#
# Keys are the column labels entsoe-py produces from PSRTYPE_MAPPINGS, not the B-codes.
CATEGORY_BY_PRODUCTION_TYPE = {
    "Wind Onshore":                  "wind",
    "Wind Offshore":                 "wind",
    "Solar":                         "solar",
    # Pumped storage is separated from the rest of hydro deliberately: it is the
    # incumbent doing the arbitrage this study models, so it is a variable of interest
    # rather than background hydro.
    "Hydro Pumped Storage":          "storage",
    "Energy storage":                "storage",
    "Hydro Run-of-river and pondage": "hydro",
    "Hydro Water Reservoir":         "hydro",
    "Marine":                        "hydro",
    "Nuclear":                       "nuclear",
    "Fossil Gas":                    "fossil",
    "Fossil Hard coal":              "fossil",
    "Fossil Brown coal/Lignite":     "fossil",
    "Fossil Oil":                    "fossil",
    "Fossil Oil shale":              "fossil",
    "Fossil Peat":                   "fossil",
    "Fossil Coal-derived gas":       "fossil",
    "Biomass":                       "other",
    "Waste":                         "other",
    "Geothermal":                    "other",
    "Other renewable":               "other",
    "Other":                         "other",
}

CATEGORIES = ("wind", "solar", "hydro", "nuclear", "fossil", "storage", "other")
