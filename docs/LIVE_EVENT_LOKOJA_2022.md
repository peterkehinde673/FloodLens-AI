# Live Event Candidate — Lokoja, Nigeria, 2022

FloodLens will use the October 2022 Lokoja flood as its first real-data integration target.

## Why this event

Published sources document Sentinel-1 observations of the 2022 Nigeria floods and specifically describe flooding in Lokoja, Kogi State. A later evaluation study identifies Sentinel-1 acquisitions on **7 September, 19 September, and 13 October 2022** for the Lokoja event.

The GloFAS/Copernicus reporting also provides Sentinel-1 flood observations for Nigeria in late September 2022 and identifies Lokoja among the Kogi LGAs affected by flooding.

## Initial AOI

Approximate city-centered bounding box:

- West: 6.70
- South: 7.75
- East: 6.79
- North: 7.85

Lokoja center is approximately 7.8023 N, 6.743 E.

## Initial temporal plan

- Pre-event candidate: **2022-09-07**
- Additional pre-event candidate: **2022-09-19**
- Flood-event candidate: **2022-10-13**

FloodLens should query the Copernicus Data Space catalog rather than hard-code a product ID. The pair-selection code will choose compatible Sentinel-1 acquisitions around the configured event time.

## Important evidence rule

These dates identify a documented flood-analysis scenario. They do not by themselves prove that every pixel, road, bridge, or community in the AOI was flooded or isolated.

FloodLens must derive those claims from the actual Sentinel-1 processing result and OSM analysis.

## First live request

Use:

- bbox: [6.70, 7.75, 6.79, 7.85]
- start: 2022-09-01T00:00:00Z
- end: 2022-10-20T23:59:59Z
- event_time: 2022-10-13T00:00:00Z

Start with 512x512 processing.

## Sources

- Global Flood Awareness System: Sentinel-1 observations of the 2022 Nigeria floods and Lokoja.
- Sentinel-1 flood-event evaluation literature: September 7, September 19, and October 13, 2022 acquisitions for Lokoja.
- Copernicus Data Space: Sentinel-1 GRD archive and processing access.
