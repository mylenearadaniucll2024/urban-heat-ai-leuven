# Belgian Urban Heat Monitor

Predicts urban heat anomalies across Leuven using Sentinel-2 satellite imagery and citizen science weather sensors.

## What it does

Trains three ML models (Random Forest, XGBoost, CNN) to predict how much hotter or cooler a location is compared to the city daily mean. Produces interactive heat anomaly maps and a 2026+ forecast.

## Data sources

| Source | What | Access |
|---|---|---|
| [Leuven.cool](https://zenodo.org/records/14893734) | ~155 weather stations · Q3 2023–2025 | Free (Zenodo) |
| [Sentinel-2 L2A](https://browser.dataspace.copernicus.eu) | 7 satellite scenes · B04/B08/B11 · Leuven only | Free (ESA Copernicus) |
| [RMI AWS](https://opendata.meteo.be/geonetwork/srv/eng/catalog.search#/metadata/RMI_DATASET_AWS_10MIN) | 5 Belgian cities · official daily temperature | Free (CC BY 4.0) |
| [ESA WorldCover](https://viewer.terrascope.be) | 10 m land cover map · Belgium 2021 | Free (CC BY 4.0) |

## Project structure

```
data/
  raw/
    rmi/            aws_10min.xls
    leuven/          RAWDATA2023Q3.csv, RAWDATA2024Q3.csv, RAWDATA2025Q3.csv, STATIONS.csv
    sentinel2/       YYYY-MM-DD/B04.jp2, B08.jp2, B11.jp2
notebooks/
  belgium_heat_monitoring_tool_v3.ipynb   main pipeline
dashboard/
  belgian_urban_heat_dashboard_v4.html   interactive web dashboard
```

## Setup

```bash
pip install -r requirements.txt
```

For faster CNN training:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

## How to run

1. Download Sentinel-2 scenes from [Copernicus Browser](https://browser.dataspace.copernicus.eu) — tile 31UES, cloud cover ≤ 10%, Q3 summer dates — and save as `data/raw/sentinel2/YYYY-MM-DD/BXX.jp2`
2. Place Leuven.cool CSV files in `data/raw/leuven/`
3. Run `belgium_heat_monitoring_tool_v3.ipynb` top to bottom
4. Open `belgian_urban_heat_dashboard_v4.html` in a browser

## Results

| Model | RMSE (°C) | R² |
|---|---|---|
| Random Forest | 0.453 | 0.526 |
| XGBoost | 0.445 | 0.541 |
| XGBoost (tuned) | **0.440** | **0.552** |
| CNN (20 epochs) | 0.545 | 0.327 |

Best model: XGBoost (tuned). Spatial maps cover Leuven only. Non-Leuven city maps in the dashboard are simulated from land-use profiles, not real satellite data.

## Known limitations

- Sentinel-2 data is Leuven only — no real satellite maps for Brussels, Ghent, Antwerp, or Liège
- 2024 has only one satellite scene, which causes higher prediction error for that year
- CNN results are based on 20 CPU epochs and have not converged — GPU training recommended
- Grid prediction range is narrow (−1 to +0.3°C) because weather features are fixed at medians

## License

Data sources retain their own licences (see table above). Code: MIT.