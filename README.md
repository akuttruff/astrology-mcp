# Astrology MCP Tool

A Python-based astrology calculation tool using Swiss Ephemeris for use with MCP servers and local LLMs (via LM Studio).

## Features

- **Natal Chart Calculation**: Calculate complete birth charts with planetary positions, houses, and angles
- **Planetary Positions**: Get current positions of all planets including Mercury through Pluto
- **Aspect Calculations**: Calculate planetary aspects (conjunction, square, opposition, trine, sextile)
- **Transit Analysis**: Track transiting planets and their aspects to natal positions
- **Progressions**: Solar arc progressions for forecasting

### Supported House Systems

- **Whole Sign** (default) - Each house corresponds to a full zodiac sign
- Placidus, Equal House, Koch, Porphyry, and Regiomontanus available

## Installation

### Using a Virtual Environment (Recommended)

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### System-wide Installation (Not Recommended)

```bash
# Install dependencies globally
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
from datetime import datetime, timezone

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

# Get house positions
for planet, house in chart.house_positions.items():
    print(f"{planet.name} is in House {house}")
```

### With Timezone Support

The library handles timezone-aware datetimes automatically. For accurate results, **include timezone information** in your datetime strings:

```python
from datetime import datetime, timezone, timedelta

# PDT (UTC-7) - California daylight saving time
birth_dt = datetime(1984, 5, 10, 20, 44, tzinfo=timezone(timedelta(hours=-7)))
chart = calculate_natal_chart(
    birth_datetime=birth_dt,
    latitude=34.0211,
    longitude=-118.3965
)

# Or use ISO format with timezone offset
chart = calculate_natal_chart(
    birth_datetime=datetime.fromisoformat("1984-05-10T20:44:00-07:00"),
    latitude=34.0211,
    longitude=-118.3965
)
```

**Note**: Without timezone info, the library assumes input is in local time and converts it to UTC. For the most accurate results, always include timezone information.

### Using with LM Studio

The MCP server exposes tools that can be called via tool calling interface.

**Setup:**
1. Copy `mcp.json` from this project to your LM Studio MCP config directory (typically `~/.lmstudio/mcp.json`)
2. Restart LM Studio

**Example configuration:**
```json
{
  "mcpServers": {
    "astrology": {
      "command": "/path/to/astrology-mcp/.venv/bin/python",
      "args": [
        "-c",
        "import sys; sys.path.insert(0, '/path/to/astrology-mcp/src'); import astrology_mcp_server.main; astrology_mcp_server.main.main()"
      ]
    }
  }
}
```

**Available tools:**
- `calculate_natal_chart` - Calculate a complete birth chart (birth_datetime with timezone recommended)
- `get_planet_positions` - Get current planetary positions
- `calculate_aspects` - Calculate planetary aspects between chart objects
- `calculate_transits` - Get current transits to a natal chart
- `get_houses` - Get house positions for planets

**Important**: For accurate natal charts, provide birth datetime with timezone:
```json
{
  "birth_datetime": "1984-05-10T20:44:00-07:00",
  "latitude": 34.0211,
  "longitude": -118.3965
}
```

## Project Structure

```
astrology-mcp/
├── src/
│   ├── astrology_mcp_server/
│   │   └── main.py            # MCP server entry point
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
# Ensure virtual environment is activated
source .venv/bin/activate

# Run tests
python -m pytest tests/

# Install in development mode
pip install -e .

# Run example natal chart (with your birth data)
python my_natal_chart.py
```

## Troubleshooting

### Incorrect Chart Results

If your chart shows incorrect planet signs or house positions:

1. **Check timezone handling**: Ensure your datetime has proper timezone info
   ```python
   from datetime import datetime, timezone, timedelta
   
   # Include timezone offset for accurate conversion to UTC
   dt = datetime.fromisoformat("1984-05-10T20:44:00-07:00")  # PDT
   
   chart = calculate_natal_chart(
       birth_datetime=dt,
       latitude=34.0211,
       longitude=-118.3965
   )
   ```

2. **Verify ephemeris files**: Make sure Swiss Ephemeris files are downloaded and accessible

3. **Check house system**: Verify you're using the correct house system (default is Whole Sign)

## License

MIT License
