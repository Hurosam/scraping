import sqlite3
import pandas as pd
import os
import sys

DB_FILE = "noticias.db"

CSV_TO_TABLE_MAPPING = {
"noticias_tudiariohuanuco_completo.csv": "resumen_noticias",
"articulos_con_parrafo_y_ciudades.csv": "articulos_detallados"
}
def create_database_from_csvs():
    
    """
    Función principal que crea una base de datos SQLite e importa datos desde archivos CSV.
    Si la base de datos ya existe, se eliminará para empezar de cero.
    """
    print(f"\n[2/3] Preparando la base de datos '{DB_FILE}'...")

    # Eliminar la base de datos anterior si existe
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"      - La base de datos existente '{DB_FILE}' ha sido eliminada.")

    try:
        # Conectar a la base de datos (creará el archivo si no existe)
        conn = sqlite3.connect(DB_FILE)
        print(f"      - Base de datos '{DB_FILE}' creada y conexión establecida.")
    except sqlite3.Error as e:
        print(f"¡ERROR FATAL! No se pudo conectar a la base de datos: {e}")
        return # Sale de la función si no se puede conectar

    # --- Importar datos ---
    print("\n[3/3] Importando datos desde los archivos CSV a la base de datos...")

    for csv_file, table_name in CSV_TO_TABLE_MAPPING.items():
        try:
            print(f"      - Leyendo '{csv_file}'...")
            df = pd.read_csv(csv_file, encoding='utf-8-sig')

            print(f"      - Creando tabla '{table_name}' e insertando {len(df)} filas...")
            df.to_sql(name=table_name, con=conn, if_exists='replace', index=False)
            print(f"      - ¡Tabla '{table_name}' importada con éxito!")

        except Exception as e:
            print(f"¡ERROR! Ocurrió un problema al procesar el archivo '{csv_file}': {e}")
            conn.close() # Cierra la conexión antes de salir
            return # Sale de la función si hay un error en la importación
        
    # --- Finalizar ---
    conn.close()

print("-" * 50)
print("¡PROCESO COMPLETADO EXITOSAMENTE!")
print(f"La base de datos '{DB_FILE}' ha sido creada.")
print("\nPuedes abrir el archivo con 'DB Browser for SQLite' para ver los datos.")
print("-" * 50)

if __name__ == "__main__":
    
    print("--- Iniciando la creación de la base de datos SQLite ---")

    # --- PASO 1: VERIFICAR QUE LOS ARCHIVOS CSV EXISTEN ---
    # Esta lógica se ejecuta ANTES de llamar a la función principal.

    print("\n[1/3] Verificando la existencia de los archivos CSV requeridos...")

    required_files = list(CSV_TO_TABLE_MAPPING.keys())
    missing_files = [f for f in required_files if not os.path.exists(f)]

    if missing_files:
        print("\n¡ERROR! No se pueden encontrar los siguientes archivos CSV:")
        for file in missing_files:
            print(f"  - {file}")
        print("\nINSTRUCCIONES:")
        print("Asegúrate de haber ejecutado los siguientes scripts en orden para generar estos archivos:")
        print("  1. python scrap.py")
        print("  2. python link_pnl.py")
        print("\nEl programa se detendrá ahora.")
        sys.exit()  # Detiene la ejecución del script de forma segura.

    print("¡Éxito! Todos los archivos CSV requeridos fueron encontrados.")

    # Si todos los archivos existen, llamamos a la función para crear la base de datos.
    create_database_from_csvs()