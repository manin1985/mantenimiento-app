import os
import psycopg2
import pandas as pd
from flask import Flask, render_template, request, redirect, send_file, send_from_directory
from io import BytesIO

app = Flask(__name__)

PIN_SEGURIDAD = "2026"
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Creamos la tabla base
    cur.execute('''CREATE TABLE IF NOT EXISTS incidencias 
        (id SERIAL PRIMARY KEY, 
         elemento TEXT NOT NULL, 
         ubicacion TEXT NOT NULL, 
         estado TEXT DEFAULT 'Pendiente',
         fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
         operario TEXT,
         prioridad TEXT DEFAULT 'Media')''')
    
    # Truco de emergencia para añadir columnas si la tabla ya existía
    try:
        cur.execute("ALTER TABLE incidencias ADD COLUMN operario TEXT")
    except: conn.rollback()
    try:
        cur.execute("ALTER TABLE incidencias ADD COLUMN prioridad TEXT DEFAULT 'Media'")
    except: conn.rollback()
    
    conn.commit()
    cur.close()
    conn.close()

@app.route('/manifest.json')
def manifest():
    return send_from_directory(os.getcwd(), 'manifest.json')

@app.route('/')
def index():
    init_db()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM incidencias WHERE estado='Pendiente' ORDER BY CASE WHEN prioridad='Alta' THEN 1 WHEN prioridad='Media' THEN 2 ELSE 3 END, fecha DESC")
    pendientes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', pendientes=pendientes)

@app.route('/crear')
def pagina_crear():
    return render_template('crear.html')

@app.route('/historial')
def historial():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM incidencias WHERE estado='Realizado' ORDER BY fecha DESC")
    realizados = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('historial.html', realizados=realizados)

@app.route('/exportar')
def exportar():
    conn = get_db_connection()
    query = "SELECT elemento, ubicacion, prioridad, estado, fecha, operario FROM incidencias ORDER BY fecha DESC"
    df = pd.read_sql(query, conn)
    conn.close()
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte')
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', download_name="resumen_mantenimiento.xlsx", as_attachment=True)

@app.route('/nuevo', methods=['POST'])
def nuevo():
    if request.form.get('pin') != PIN_SEGURIDAD:
        return "PIN Incorrecto", 403
    elemento = request.form.get('elemento')
    ubicacion = request.form.get('ubicacion')
    prioridad = request.form.get('prioridad')
    if elemento and ubicacion:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO incidencias (elemento, ubicacion, prioridad) VALUES (%s, %s, %s)", (elemento, ubicacion, prioridad))
        conn.commit()
        cur.close()
        conn.close()
    return redirect('/')

@app.route('/completar/<int:id>', methods=['POST'])
def completar(id):
    nombre = request.form.get('operario')
    if nombre:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE incidencias SET estado='Realizado', operario=%s WHERE id=%s", (nombre, id))
        conn.commit()
        cur.close()
        conn.close()
    return redirect('/')

if __name__ == '__main__':
    app.run()
