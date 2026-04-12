import psycopg2
import json

conn_url = 'postgresql://kobo:DB%40mPower%40786@192.168.19.30:5432/mukit_edmate_frontend'

def dump_schema():
    conn = psycopg2.connect(conn_url)
    cur = conn.cursor()
    
    # Get all tables
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    tables = [r[0] for r in cur.fetchall()]
    
    schema = {}
    for table in tables:
        # Get columns
        cur.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, (table,))
        columns = cur.fetchall()
        
        # Get foreign keys
        cur.execute("""
            SELECT
                kcu.column_name, 
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name 
            FROM 
                information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name=%s;
        """, (table,))
        fks = cur.fetchall()
        
        schema[table] = {
            "columns": [{"name": c[0], "type": c[1], "nullable": c[2]} for c in columns],
            "fks": [{"column": f[0], "foreign_table": f[1], "foreign_column": f[2]} for f in fks]
        }
    
    print(json.dumps(schema, indent=2))
    cur.close()
    conn.close()

if __name__ == "__main__":
    dump_schema()
