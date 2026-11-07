import asyncio
import asyncpg

# Replace with your Neon connection string
DATABASE_URL = "insert neon string here"

async def generate_schema_ddl():
    conn = await asyncpg.connect(DATABASE_URL)
    
    # Get all user tables in public schema
    tables = await conn.fetch("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    """)
    
    ddl_statements = []
    
    for table in tables:
        table_name = table['table_name']
        
        # Query columns for the table
        columns = await conn.fetch("""
            SELECT 
                column_name, 
                data_type, 
                character_maximum_length,
                is_nullable, 
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = $1
            ORDER BY ordinal_position;
        """, table_name)
        
        col_defs = []
        for col in columns:
            col_type = col['data_type'].upper()
            if col['character_maximum_length']:
                col_type += f"({col['character_maximum_length']})"
                
            nullability = "NOT NULL" if col['is_nullable'] == "NO" else ""
            default = f"DEFAULT {col['column_default']}" if col['column_default'] is not None else ""
            
            def_str = f"    {col['column_name']} {col_type} {nullability} {default}".strip()
            col_defs.append(def_str)
            
        create_stmt = f"CREATE TABLE IF NOT EXISTS public.{table_name} (\n" + ",\n".join(col_defs) + "\n);"
        ddl_statements.append(create_stmt)
        
    await conn.close()
    
    # Save to schema_dump.sql
    with open("schema_dump.sql", "w", encoding="utf-8") as f:
        f.write("\n\n".join(ddl_statements))
        
    print(f"Generated DDL for {len(tables)} tables into schema_dump.sql!")

if __name__ == "__main__":
    asyncio.run(generate_schema_ddl())