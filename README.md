# stock-inventory-tools

Python scripts that use Selenium to scrape contributor portfolio metadata from Adobe Stock and Shutterstock, and to update asset titles in bulk on both platforms.

Because neither platform exposes a practical full-portfolio sync API for contributors, this project relies on browser automation and HTML parsing. That also means selectors and parsing patterns can break when the sites change.

## Features

- Logs into Adobe Stock and Shutterstock
- Scrapes portfolio pages and outputs CSV to stdout
- Supports file-based parsing mode for previously downloaded HTML
- Supports page limits for partial scraping
- Supports Adobe and Shutterstock title updates from a CSV file or a single asset/value pair
- Retries failed page loads

## Requirements

- Python 3.8+
- Google Chrome installed
- Compatible ChromeDriver installed and available in `PATH`
- Python package: `selenium`

Install dependencies:

```bash
pip install selenium
```

## Setup

Copy the template config and then update credentials as needed:

```bash
cp default-config.ini config.ini
```

Minimum required values in `config.ini`:

```ini
[shutterstock]
username = your_email
password = your_password

[adobe]
username = your_google_email
```

`default-config.ini` now contains the default runtime settings for:

- Selenium timeouts and browser options
- Scraping retry and delay values
- Adobe and Shutterstock portfolio URLs
- Adobe bulk-update timing values

Override any of those values in `config.ini` if you need different behavior locally.

## Usage

Launch the GUI:

```bash
python inventory-gui.py
```

The GUI exposes the get/set options as dropdowns and runs the selected command with one click. Get inventory jobs write CSV output to a timestamped file in `db/`, for example `db/adobe-inventory-20260703-143012.csv`.

Scrape Shutterstock:

```bash
python get-inventory.py --shutterstock
```

Scrape Adobe:

```bash
python get-inventory.py --adobe
```

Limit the number of scraped pages:

```bash
python get-inventory.py --shutterstock --page 3
```

Parse local HTML files without logging in:

```bash
python get-inventory.py --shutterstock --file index.html
python get-inventory.py --adobe --file *.html
```

Update one Adobe asset title:

```bash
python set-inventory.py --adobe --asset 123456789 --title "Updated title"
```

Update one Shutterstock asset title:

```bash
python set-inventory.py --shutterstock --asset 1234567890 --value "Updated title"
```

Update Adobe asset titles from CSV:

```bash
python set-inventory.py --adobe --file input.csv
```

Update Shutterstock asset titles from CSV:

```bash
python set-inventory.py --shutterstock --file input.csv
```

The CSV format for `set-inventory.py` is:

```text
asset_id,title
123456789,Updated title
```

`title`, `value`, and `inventory` are all accepted as the second-column header.

## Output

`get-inventory.py` prints CSV to stdout:

```text
platform,filename,asset_id,title
Shutterstock,image.jpg,1234567890,"Title"
Adobe,image.jpg,9876543210,"Title"
```

Example redirect:

```bash
python get-inventory.py --shutterstock > shutterstockdb.csv
```

## Notes

- Adobe login still requires manual completion of Google authentication and 2FA; the script waits for the portfolio page to appear automatically
- File mode skips browser login entirely
- The scripts depend on the current site HTML and Selenium selectors
- Use responsibly and respect platform terms
