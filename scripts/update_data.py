"""
Automated Land Registry Data Updater

Downloads the latest CCOD and OCOD full CSV snapshots from the HM Land Registry
Use Land and Property Data service, loads them into PostgreSQL staging tables,
then atomically swaps them with the production tables for zero-downtime updates.

Usage:
    python scripts/update_data.py

Required environment variables:
    DATABASE_URL           - PostgreSQL (Neon) connection string
    LAND_REGISTRY_API_KEY  - API key from use-land-property-data.service.gov.uk
"""

import csv
import io
import os
import sys
import time
import tempfile
import requests
import psycopg2

# Force unbuffered output for CI logs
sys.stdout.reconfigure(line_buffering=True)

DATABASE_URL = os.environ.get('DATABASE_URL')
API_KEY = os.environ.get('LAND_REGISTRY_API_KEY')
API_BASE = 'https://use-land-property-data.service.gov.uk/api/v1'

# Datasets to download
DATASETS = [
    {'name': 'CCOD', 'slug': 'ccod', 'has_country': False},
    {'name': 'OCOD', 'slug': 'ocod', 'has_country': True},
]

# Safety: refuse to swap if new data has fewer than this fraction of old rows
MIN_ROW_RATIO = 0.5


def log(msg):
    print(f"[update_data] {msg}")
    sys.stdout.flush()


def download_dataset(slug, dest_path):
    """Download the latest full CSV for a dataset via the Land Registry API."""
    url = f"{API_BASE}/datasets/{slug}"
    headers = {'Authorization': API_KEY}

    log(f"Fetching dataset metadata from {url} ...")
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    metadata = resp.json()

    # Find the latest full file resource
    resources = metadata.get('resources', [])
    full_file = None
    for r in resources:
        if 'full' in r.get('name', '').lower() or 'full' in r.get('description', '').lower():
            full_file = r
            break
    if not full_file and resources:
        full_file = resources[0]
    if not full_file:
        raise RuntimeError(f"No downloadable resource found for dataset '{slug}'")

    download_url = full_file.get('url') or full_file.get('download_url')
    if not download_url:
        raise RuntimeError(f"No download URL in resource for '{slug}': {full_file}")

    file_name = full_file.get('name', slug)
    log(f"Downloading {file_name} from {download_url} ...")

    with requests.get(download_url, headers=headers, stream=True, timeout=600) as r:
        r.raise_for_status()
        total = 0
        with open(dest_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
                total += len(chunk)
        log(f"  Downloaded {total / (1024*1024):.1f} MB -> {dest_path}")


def normalize_company_reg(value):
    if not value:
        return ''
    return value.strip().upper().replace('(', '').replace(')', '').replace(' ', '').replace('-', '')


def normalize_upper(value):
    if not value:
        return ''
    return value.strip().upper()


def create_staging_tables(conn):
    """Create staging tables with the full schema including normalized columns."""
    cur = conn.cursor()

    log("Dropping old staging tables if they exist ...")
    cur.execute("DROP TABLE IF EXISTS proprietors_staging CASCADE")
    cur.execute("DROP TABLE IF EXISTS properties_staging CASCADE")

    log("Creating properties_staging ...")
    cur.execute("""
        CREATE TABLE properties_staging (
            id SERIAL PRIMARY KEY,
            title_number TEXT,
            tenure TEXT,
            property_address TEXT,
            district TEXT,
            county TEXT,
            region TEXT,
            postcode TEXT,
            multiple_address_indicator TEXT,
            price_paid TEXT,
            date_proprietor_added TEXT,
            additional_proprietor_indicator TEXT,
            data_source TEXT NOT NULL DEFAULT 'CCOD',
            property_address_upper TEXT NOT NULL DEFAULT '',
            postcode_upper TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    log("Creating proprietors_staging ...")
    cur.execute("""
        CREATE TABLE proprietors_staging (
            id SERIAL PRIMARY KEY,
            property_id INTEGER NOT NULL,
            proprietor_number INTEGER NOT NULL,
            proprietor_name TEXT,
            company_registration_no TEXT,
            proprietorship_category TEXT,
            country_incorporated TEXT,
            address_line_1 TEXT,
            address_line_2 TEXT,
            address_line_3 TEXT,
            company_reg_normalized TEXT NOT NULL DEFAULT '',
            proprietor_name_upper TEXT NOT NULL DEFAULT ''
        )
    """)

    conn.commit()


def load_csv_into_staging(conn, csv_path, dataset):
    """Load a CCOD or OCOD CSV into the staging tables using COPY."""
    data_source = dataset['name']
    has_country = dataset['has_country']

    log(f"Loading {data_source} from {csv_path} ...")

    # Read CSV and prepare property + proprietor buffers
    prop_buf = io.StringIO()
    propr_buf = io.StringIO()
    prop_writer = csv.writer(prop_buf, quoting=csv.QUOTE_MINIMAL)
    propr_writer = csv.writer(propr_buf, quoting=csv.QUOTE_MINIMAL)

    properties_count = 0
    proprietors_count = 0
    skipped = 0

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            title_number = row.get('Title Number', '').strip()
            if not title_number:
                continue

            property_address = row.get('Property Address', '').strip()
            postcode = row.get('Postcode', '').strip()

            # We'll use a placeholder for property_id — we insert properties first,
            # then get the assigned IDs. Instead, batch-insert then link.
            # For efficiency, we use a two-pass approach:
            # Pass 1: COPY properties, get back IDs
            # Pass 2: COPY proprietors with the IDs

            # For now, accumulate in memory. We'll flush in batches.
            properties_count += 1

            # Collect proprietors for this row
            row_proprietors = []
            for prop_num in range(1, 5):
                company_no = row.get(f'Company Registration No. ({prop_num})', '').strip()
                proprietor_name = row.get(f'Proprietor Name ({prop_num})', '').strip()

                if not company_no and not proprietor_name:
                    continue
                if not company_no:
                    skipped += 1
                    continue

                country = ''
                if has_country:
                    country = row.get(f'Country Incorporated ({prop_num})', '').strip()

                row_proprietors.append({
                    'proprietor_number': prop_num,
                    'proprietor_name': proprietor_name,
                    'company_registration_no': company_no,
                    'proprietorship_category': row.get(f'Proprietorship Category ({prop_num})', '').strip(),
                    'country_incorporated': country,
                    'address_line_1': row.get(f'Proprietor ({prop_num}) Address (1)', '').strip(),
                    'address_line_2': row.get(f'Proprietor ({prop_num}) Address (2)', '').strip(),
                    'address_line_3': row.get(f'Proprietor ({prop_num}) Address (3)', '').strip(),
                })

            # Write property row
            prop_writer.writerow([
                title_number,
                row.get('Tenure', '').strip(),
                property_address,
                row.get('District', '').strip(),
                row.get('County', '').strip(),
                row.get('Region', '').strip(),
                postcode,
                row.get('Multiple Address Indicator', '').strip(),
                row.get('Price Paid', '').strip(),
                row.get('Date Proprietor Added', '').strip(),
                row.get('Additional Proprietor Indicator', '').strip(),
                data_source,
                normalize_upper(property_address),
                normalize_upper(postcode),
            ])

            # Write proprietor rows (property_id placeholder = properties_count, will fix later)
            for p in row_proprietors:
                proprietors_count += 1
                propr_writer.writerow([
                    0,  # placeholder property_id — will be updated
                    p['proprietor_number'],
                    p['proprietor_name'],
                    p['company_registration_no'],
                    p['proprietorship_category'],
                    p['country_incorporated'],
                    p['address_line_1'],
                    p['address_line_2'],
                    p['address_line_3'],
                    normalize_company_reg(p['company_registration_no']),
                    normalize_upper(p['proprietor_name']),
                ])

            if properties_count % 100000 == 0:
                log(f"  Parsed {properties_count:,} rows ...")

    log(f"  Parsed {data_source}: {properties_count:,} properties, {proprietors_count:,} proprietors, {skipped:,} skipped (no company no.)")

    # --- Insert properties via COPY and retrieve IDs ---
    log(f"  COPYing properties into staging ...")
    prop_buf.seek(0)
    cur = conn.cursor()

    prop_columns = (
        'title_number, tenure, property_address, district, county, region, '
        'postcode, multiple_address_indicator, price_paid, date_proprietor_added, '
        'additional_proprietor_indicator, data_source, property_address_upper, postcode_upper'
    )
    cur.copy_expert(
        f"COPY properties_staging ({prop_columns}) FROM STDIN WITH CSV",
        prop_buf
    )
    conn.commit()

    # Get the ID range for the properties we just inserted
    cur.execute("SELECT MIN(id), MAX(id) FROM properties_staging WHERE data_source = %s", (data_source,))
    min_id, max_id = cur.fetchone()

    if min_id is None:
        log(f"  WARNING: No properties inserted for {data_source}")
        return properties_count, proprietors_count

    log(f"  Property IDs: {min_id} - {max_id}")

    # Now we need to assign correct property_id to proprietors.
    # Since properties were inserted in CSV order and got sequential IDs,
    # we can map row_number -> id.
    # Re-read the CSV to build proprietor rows with correct IDs.

    log(f"  Building proprietor data with correct property IDs ...")
    propr_buf2 = io.StringIO()
    propr_writer2 = csv.writer(propr_buf2, quoting=csv.QUOTE_MINIMAL)

    # Get ordered property IDs for this data source
    cur.execute(
        "SELECT id FROM properties_staging WHERE data_source = %s ORDER BY id",
        (data_source,)
    )
    property_ids = [row[0] for row in cur.fetchall()]

    prop_idx = 0
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            title_number = row.get('Title Number', '').strip()
            if not title_number:
                continue

            if prop_idx >= len(property_ids):
                break
            property_id = property_ids[prop_idx]
            prop_idx += 1

            for prop_num in range(1, 5):
                company_no = row.get(f'Company Registration No. ({prop_num})', '').strip()
                proprietor_name = row.get(f'Proprietor Name ({prop_num})', '').strip()

                if not company_no and not proprietor_name:
                    continue
                if not company_no:
                    continue

                country = ''
                if has_country:
                    country = row.get(f'Country Incorporated ({prop_num})', '').strip()

                propr_writer2.writerow([
                    property_id,
                    prop_num,
                    proprietor_name,
                    company_no,
                    row.get(f'Proprietorship Category ({prop_num})', '').strip(),
                    country,
                    row.get(f'Proprietor ({prop_num}) Address (1)', '').strip(),
                    row.get(f'Proprietor ({prop_num}) Address (2)', '').strip(),
                    row.get(f'Proprietor ({prop_num}) Address (3)', '').strip(),
                    normalize_company_reg(company_no),
                    normalize_upper(proprietor_name),
                ])

    log(f"  COPYing proprietors into staging ...")
    propr_buf2.seek(0)
    propr_columns = (
        'property_id, proprietor_number, proprietor_name, company_registration_no, '
        'proprietorship_category, country_incorporated, '
        'address_line_1, address_line_2, address_line_3, '
        'company_reg_normalized, proprietor_name_upper'
    )
    cur.copy_expert(
        f"COPY proprietors_staging ({propr_columns}) FROM STDIN WITH CSV",
        propr_buf2
    )
    conn.commit()

    return properties_count, proprietors_count


def build_indexes(conn):
    """Build all indexes on staging tables."""
    cur = conn.cursor()

    log("Enabling pg_trgm extension ...")
    cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    conn.commit()

    indexes = [
        ("idx_stg_property_id", "CREATE INDEX idx_stg_property_id ON proprietors_staging(property_id)"),
        ("idx_stg_title_number", "CREATE INDEX idx_stg_title_number ON properties_staging(title_number)"),
        ("idx_stg_postcode", "CREATE INDEX idx_stg_postcode ON properties_staging(postcode)"),
        ("idx_stg_data_source", "CREATE INDEX idx_stg_data_source ON properties_staging(data_source)"),
        ("idx_stg_company_reg_normalized", "CREATE INDEX idx_stg_company_reg_normalized ON proprietors_staging(company_reg_normalized)"),
        ("idx_stg_company_registration_no", "CREATE INDEX idx_stg_company_registration_no ON proprietors_staging(company_registration_no)"),
        ("idx_stg_proprietor_name", "CREATE INDEX idx_stg_proprietor_name ON proprietors_staging(proprietor_name)"),
        ("idx_stg_proprietor_name_trgm", "CREATE INDEX idx_stg_proprietor_name_trgm ON proprietors_staging USING GIN (proprietor_name_upper gin_trgm_ops)"),
        ("idx_stg_property_address_trgm", "CREATE INDEX idx_stg_property_address_trgm ON properties_staging USING GIN (property_address_upper gin_trgm_ops)"),
        ("idx_stg_postcode_trgm", "CREATE INDEX idx_stg_postcode_trgm ON properties_staging USING GIN (postcode_upper gin_trgm_ops)"),
    ]

    for name, sql in indexes:
        t0 = time.time()
        cur.execute(sql)
        conn.commit()
        log(f"  Created {name} ({time.time() - t0:.1f}s)")


def validate_counts(conn):
    """Compare staging row counts against production. Abort if too low."""
    cur = conn.cursor()

    # Check if production tables exist
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'properties'
        )
    """)
    prod_exists = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM properties_staging")
    staging_props = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM proprietors_staging")
    staging_proprs = cur.fetchone()[0]

    log(f"Staging counts: {staging_props:,} properties, {staging_proprs:,} proprietors")

    if staging_props == 0:
        raise RuntimeError("Staging properties table is empty — aborting swap")

    if prod_exists:
        cur.execute("SELECT COUNT(*) FROM properties")
        prod_props = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM proprietors")
        prod_proprs = cur.fetchone()[0]
        log(f"Production counts: {prod_props:,} properties, {prod_proprs:,} proprietors")

        if prod_props > 0 and staging_props < prod_props * MIN_ROW_RATIO:
            raise RuntimeError(
                f"Staging has only {staging_props:,} properties vs {prod_props:,} in production "
                f"({staging_props/prod_props:.0%}). Minimum ratio is {MIN_ROW_RATIO:.0%}. Aborting."
            )
    else:
        log("No existing production tables — this is a fresh load")

    return staging_props, staging_proprs


def atomic_swap(conn):
    """Atomically swap staging tables with production tables."""
    cur = conn.cursor()

    log("Performing atomic table swap ...")

    # Check if old tables exist from a previous failed swap
    cur.execute("DROP TABLE IF EXISTS proprietors_old CASCADE")
    cur.execute("DROP TABLE IF EXISTS properties_old CASCADE")
    conn.commit()

    # Do the swap in a single transaction
    cur.execute("BEGIN")
    try:
        # Check if production tables exist
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'properties'
            )
        """)
        prod_exists = cur.fetchone()[0]

        if prod_exists:
            cur.execute("ALTER TABLE proprietors RENAME TO proprietors_old")
            cur.execute("ALTER TABLE properties RENAME TO properties_old")

        cur.execute("ALTER TABLE properties_staging RENAME TO properties")
        cur.execute("ALTER TABLE proprietors_staging RENAME TO proprietors")
        conn.commit()
        log("  Swap committed successfully!")
    except Exception:
        conn.rollback()
        raise

    # Drop old tables outside the swap transaction
    if prod_exists:
        log("Dropping old tables ...")
        cur.execute("DROP TABLE IF EXISTS proprietors_old CASCADE")
        cur.execute("DROP TABLE IF EXISTS properties_old CASCADE")
        conn.commit()


def main():
    if not DATABASE_URL:
        log("ERROR: DATABASE_URL not set")
        sys.exit(1)
    if not API_KEY:
        log("ERROR: LAND_REGISTRY_API_KEY not set")
        sys.exit(1)

    t_start = time.time()
    log("=" * 60)
    log("LAND REGISTRY DATA UPDATE")
    log("=" * 60)

    conn = psycopg2.connect(DATABASE_URL, connect_timeout=30)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Step 1: Download CSVs
            csv_paths = {}
            for ds in DATASETS:
                dest = os.path.join(tmpdir, f"{ds['name']}_FULL.csv")
                download_dataset(ds['slug'], dest)
                csv_paths[ds['name']] = dest

            # Step 2: Create staging tables
            create_staging_tables(conn)

            # Step 3: Load data into staging
            total_props = 0
            total_proprs = 0
            for ds in DATASETS:
                p, pr = load_csv_into_staging(conn, csv_paths[ds['name']], ds)
                total_props += p
                total_proprs += pr

            # Step 4: Build indexes on staging
            build_indexes(conn)

            # Step 5: Validate
            staging_props, staging_proprs = validate_counts(conn)

            # Step 6: Atomic swap
            atomic_swap(conn)

        elapsed = time.time() - t_start
        log("=" * 60)
        log("UPDATE COMPLETE!")
        log(f"  Properties: {staging_props:,}")
        log(f"  Proprietors: {staging_proprs:,}")
        log(f"  Duration: {elapsed/60:.1f} minutes")
        log("=" * 60)

    except Exception as e:
        log(f"FATAL ERROR: {e}")
        conn.rollback()
        # Clean up staging tables on failure
        try:
            cur = conn.cursor()
            cur.execute("DROP TABLE IF EXISTS proprietors_staging CASCADE")
            cur.execute("DROP TABLE IF EXISTS properties_staging CASCADE")
            conn.commit()
        except Exception:
            pass
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
