import os
import psycopg2
from flask import Flask

app = Flask(__name__)

@app.route('/')
def reparador_directo():
    try:
        # Conexión directa
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cur = conn.cursor()
        # Ejecutamos las dos actualizaciones
        cur.execute("ALTER TABLE incidencias ADD COLUMN IF NOT EXISTS tipo VARCHAR(50) DEFAULT 'Contenedor';")
        cur.execute("ALTER TABLE incidencias ADD COLUMN IF NOT EXISTS fraccion VARCHAR(50) DEFAULT 'N/A';")
        conn.commit()
        cur.close()
        conn.close()
        return "ESTADO: BASE DE DATOS ACTUALIZADA. YA PUEDES VOLVER AL CODIGO ANTERIOR."
    except Exception as e:
        return f"ERROR CRITICO: {str(e)}"

if __name__ == '__main__':
    # Usamos el puerto por defecto de Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
