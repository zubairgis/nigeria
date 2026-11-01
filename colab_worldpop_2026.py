# Google Colab: run this cell from a clone of the repository or upload the repository ZIP.
# Aggregates WorldPop 2026 1 km age/sex estimates to the supplied 360 House constituencies.
!pip -q install rasterio shapely
!python scripts/aggregate_worldpop_2026.py
