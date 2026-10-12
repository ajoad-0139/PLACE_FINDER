import psycopg

with psycopg.connect(
    host="localhost",
    port=5442,
    dbname="appdb",
    user="postgres",
    password="postgres",
) as conn:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        cur.execute("SELECT PostGIS_Full_Version();")
        print("PostGIS:", cur.fetchone()[0])

        cur.execute("""
            SELECT extversion
            FROM pg_extension
            WHERE extname = 'vector';
        """)
        print("pgvector:", cur.fetchone())

print("Database extension checks completed.")