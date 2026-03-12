# AIF Isotherm Plotter

A web-based tool for plotting multiple adsorption isotherm AIF files.

## Features

- Drag and drop multiple .aif files
- Auto-detect and parse AIF file metadata
- Different colors for different datasets
- Solid circles for adsorption points, hollow circles for desorption points
- Customizable legend format: Sample ID, Material ID (if available), Adsorbate, Temperature
- Support for both relative pressure (p/p₀) and absolute pressure

## Usage

### Web Interface

Open http://localhost:5000 in your browser.

1. Drag and drop multiple .aif files or click to select
2. Choose plot type (relative or absolute pressure)
3. Click "Update Plot" to generate the isotherm plot

### Docker

```bash
# Build
docker build -t plot-aif .

# Run
docker run -d -p 5000:5000 --name plot-aif plot-aif

# Or use docker-compose
docker-compose up -d
```

## Plot Settings

- **Adsorption points**: Solid circles (size: 100)
- **Desorption points**: Hollow circles (size: 80)
- **Line width**: 2.5
- **Legend format**:
  - Without Material ID: `Sample ID, Adsorbate, TemperatureK, Ads/Des`
  - With Material ID: `Sample ID, Material ID, Adsorbate, TemperatureK, Ads/Des`

## Requirements

- Python 3.13+
- Flask
- Matplotlib
- NumPy
