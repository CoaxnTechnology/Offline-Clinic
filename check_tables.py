#!/usr/bin/env python3
"""
Simple script to check database tables and their structure.
Run with: uv run python3 check_tables.py
"""
from app import create_app
from app.extensions import db
from sqlalchemy import inspect

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    
    print("=" * 60)
    print("DATABASE TABLES")
    print("=" * 60)
    
    # Get all table names
    tables = inspector.get_table_names()
    print(f"\nFound {len(tables)} table(s):")
    for table in tables:
        print(f"  - {table}")
    
    # Show details for each table
    print("\n" + "=" * 60)
    print("TABLE DETAILS")
    print("=" * 60)
    
    for table_name in tables:
        print(f"\n📋 Table: {table_name}")
        print("-" * 60)
        
        # Get columns
        columns = inspector.get_columns(table_name)
        print("Columns:")
        for col in columns:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            default = f" DEFAULT {col['default']}" if col.get('default') else ""
            print(f"  • {col['name']:20} {str(col['type']):30} {nullable}{default}")
        
        # Get primary keys
        pk_constraint = inspector.get_pk_constraint(table_name)
        if pk_constraint['constrained_columns']:
            print(f"\nPrimary Key: {', '.join(pk_constraint['constrained_columns'])}")
        
        # Get foreign keys
        fks = inspector.get_foreign_keys(table_name)
        if fks:
            print("\nForeign Keys:")
            for fk in fks:
                print(f"  • {fk['constrained_columns']} → {fk['referred_table']}.{fk['referred_columns']}")
        
        # Get unique constraints
        unique_constraints = inspector.get_unique_constraints(table_name)
        if unique_constraints:
            print("\nUnique Constraints:")
            for uc in unique_constraints:
                print(f"  • {uc['name']}: {uc['column_names']}")
        
        # Get indexes
        indexes = inspector.get_indexes(table_name)
        if indexes:
            print("\nIndexes:")
            for idx in indexes:
                unique = "UNIQUE " if idx['unique'] else ""
                print(f"  • {unique}{idx['name']}: {idx['column_names']}")
    
    print("\n" + "=" * 60)
    print("Row Counts")
    print("=" * 60)
    
    # Count rows in each table
    for table_name in tables:
        if table_name != 'alembic_version':  # Skip alembic_version
            result = db.session.execute(db.text(f"SELECT COUNT(*) FROM {table_name}"))
            count = result.scalar()
            print(f"  {table_name:20} : {count} row(s)")
