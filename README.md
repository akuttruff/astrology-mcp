# Astrology MCP Tool

A Python-based astrology calculation tool using Swiss Ephemeris for use with MCP servers and local LLMs (via LM Studio).

## Features

- **Natal Chart Calculation**: Calculate complete birth charts with planetary positions, houses, and angles
- **Planetary Positions**: Get current positions of all planets including Mercury through Pluto
- **Aspect Calculations**: Calculate planetary aspects (conjunction, square, opposition, trine, sextile)
- **Transit Analysis**: Track transiting planets and their aspects to natal positions
- **Progressions**: Solar arc progressions for forecasting

## Installation

```bash
pip install -r requirements.txt
```

### Swiss Ephemeris Setup

Swiss Ephemeris requires ephemeris files for accurate calculations. Download the free ephemeris files:

1. Visit [https://www.astro.com/swisseph/](https://www.astro.com/swisseph/)
2. Download `sweph_01.zip` through `sweph_06.zip`
3. Extract to a directory (e.g., `~/ephe`)

The ephemeris files will be automatically detected or you can set the path explicitly.

## Usage

### Basic Example

```python
from astrology.charts.chart import calculate_natal_chart
from datetime import datetime

# Create a chart for July 20, 2024 at 14:30 in New York
chart = calculate_natal_chart(
    birth_datetime=datetime(2024, 7, 20, 14, 30),
    latitude=40.7128,
    longitude=-74.0060
)

# Access chart data
print(f"Sun: {chart.get_planet_sign('SUN')} {chart.get_planet_degree('SUN')}°")
print(f"Ascendant: {chart.ascendant.sign_name} {chart.ascendant.degree_in_sign}°")

# Get planetary positions
for planet, position in chart.planets.items():
    print(f"{planet.name}: {position.longitude.sign_name} {position.longitude.degree_in_sign}°")
```

### Using with LM Studio

The MCP server exposes tools that can be called via tool calling interface:

```bash
python -m mcp.server
```

Available tools:
- `calculate_natal_chart` - Calculate a complete birth chart
- `get_planet_positions` - Get current planetary positions
- `calculate_aspects` - Calculate planetary aspects
- `calculate_transits` - Get current transits

## Project Structure

```
astrology-mcp/
├── src/
│   ├── mcp/
│   │   └── server.py          # MCP server entry point
│   └── astrology/
│       ├── __init__.py
│       ├── core/
│       │   ├── calendar.py    # Date/time handling
│       │   ├── ephemeris.py   # Planet positions
│       │   └── aspects.py     # Aspect calculations
│       ├── charts/
│       │   └── chart.py       # Natal chart calculation
│       ├── transits/
│       │   └── transit.py     # Transit calculations
│       └── progressions/
│           └── solar_arc.py   # Progression calculations
└── tests/
```

## Development

```bash
# Run tests
python -m pytest tests/

# Install in development mode
pip install -e .
```

## License

MIT License
