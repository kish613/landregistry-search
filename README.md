# Property Lookup by Company Number

A local web application for searching property ownership data by company registration number. The application loads CSV data into a SQLite database and provides an elegant web interface for searching and viewing results.

## Features

- **Fast Search**: Query properties by company registration number with instant results
- **Elegant UI**: Modern, responsive web interface with clean design
- **Data Export**: Export search results as CSV or JSON
- **Data Reload**: Refresh database from CSV file when data updates

## Prerequisites

- Python 3.8 or higher
- The CSV file (`CCOD_FULL_2025_10.csv`) should be in the project root directory

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Setup

1. **Load the data into the database** (first time setup):
```bash
python scripts/load_data.py
```

This will:
- Create the SQLite database (`property_data.db`)
- Parse and import all data from `CCOD_FULL_2025_10.csv`
- Create indexes for fast lookups
- Display progress and statistics

**Note**: The initial data load may take several minutes depending on the CSV file size.

## Usage

1. **Start the web server**:
```bash
python app/main.py
```

2. **Open your browser** and navigate to:
```
http://127.0.0.1:5000
```

3. **Search for properties**:
   - Enter a company registration number (e.g., `00563409`)
   - Click "Search" or press Enter
   - View the list of properties owned by that company

4. **Export results**:
   - Click "Export CSV" or "Export JSON" to download search results

5. **Reload data** (if CSV file is updated):
   - Click "Reload Data from CSV" at the bottom of the page
   - Wait for the reload process to complete

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # Flask application
│   ├── templates/
│   │   └── index.html       # Main search page
│   └── static/
│       ├── css/
│       │   └── style.css    # Stylesheet
│       └── js/
│           └── app.js       # Frontend JavaScript
├── scripts/
│   └── load_data.py         # CSV to database loader
├── schema.sql               # Database schema definition
├── property_data.db         # SQLite database (created after loading)
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Database Schema

The application uses two main tables:

- **properties**: Stores property information (address, postcode, tenure, etc.)
- **proprietors**: Stores company/proprietor information linked to properties

Indexes are created on `company_registration_no` for fast lookups.

## Troubleshooting

### Database not found
If you see "Database not found" when starting the app:
- Run `python scripts/load_data.py` first to create and populate the database

### Data reload fails
- Ensure the CSV file path is correct
- Check that you have write permissions in the project directory
- The reload process may take several minutes for large files

### No results found
- Verify the company number is correct (case-insensitive)
- Check that the company has properties in the database
- Ensure data was loaded successfully

## Notes

- The database file (`property_data.db`) is created in the project root directory
- Company numbers are normalized (uppercase, trimmed) for consistent searching
- The application runs locally on `http://127.0.0.1:5000` by default


