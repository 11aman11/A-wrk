import pyodbc

try:
        
        #Connection string for Windows Authentication
        connection_string = (
            "DRIVER={SQL Server};"
            "SERVER=MTLSQLCS051;"
            "DATABASE=CSIPED_PRD;"
            "TRUSTED_CONNECTION=yes;"
        )

        cnxn = pyodbc.connect(connection_string)
        cursor = cnxn.cursor()
        print("Successfully connected to the database!")

        # new table INTERN.Aman_hashing
       
        create_table_query = """
        IF NOT EXISTS (SELECT * FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id 
                      WHERE s.name = 'INTERN' AND t.name = 'Aman_hashing')
        BEGIN
            CREATE TABLE INTERN.Aman_hashing (
                script_name VARCHAR(50) PRIMARY KEY,
                hash_value VARCHAR(32) NOT NULL
            )
        END
        """
        cursor.execute(create_table_query)
        
        # Insert data into the newly created table
        insert_data_query = """
        IF EXISTS (SELECT * FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id 
                  WHERE s.name = 'INTERN' AND t.name = 'Aman_hashing')
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM INTERN.Aman_hashing WHERE script_name = 'A')
                INSERT INTO INTERN.Aman_hashing (script_name, hash_value) 
                VALUES ('A', '6c8c069a22d96be8a18c21722cdac82d')
                
            IF NOT EXISTS (SELECT 1 FROM INTERN.Aman_hashing WHERE script_name = 'B')
                INSERT INTO INTERN.Aman_hashing (script_name, hash_value) 
                VALUES ('B', 'f91d4068c0e460a54b4bf322fe36805f')
        END
        """
        cursor.execute(insert_data_query)
        
        # Commit the changes
        cnxn.commit()
        
        print("Table INTERN.Aman_hashing created successfully and data inserted!")
        
        # Verify the table was created and data was inserted
        verify_query = "SELECT script_name, hash_value FROM INTERN.Aman_hashing"
        cursor.execute(verify_query)
        rows = cursor.fetchall()
        
        print("\nTable contents:")
        for row in rows:
            print(f"Script Name: {row[0]}, Hash Value: {row[1]}")

        cursor.close() #important to always close
        cnxn.close() #important to always close

except pyodbc.Error as ex:
        
    print(ex)
    exit()