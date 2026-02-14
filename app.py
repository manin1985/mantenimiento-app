import os
import psycopg2
import pandas as pd
from flask import Flask, render_template, request, redirect, send_file
from io import BytesIO

app = Flask(__name__)

# --- CONFIGURACIÓN SEGURA ---
PIN_SEGURIDAD = "2026"
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS incidencias 
        (id SERIAL PRIMARY KEY, 
         elemento TEXT NOT NULL, 
         ubicacion TEXT NOT NULL, 
         estado TEXT DEFAULT 'Pendiente',
         fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
         operario TEXT)''')
    conn.commit()
    cur.close()
    conn.close()

@app.route('/')
def index():
    init_db()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM incidencias WHERE estado='Pendiente' ORDER BY fecha DESC")
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
    # Esta consulta saca TODO para tu informe mensual
    query = "SELECT elemento, ubicacion, estado, fecha, operario FROM incidencias ORDER BY fecha DESC"
    df = pd.read_sql(query, conn)
    conn.close()
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte_Mantenimiento')
    output.seek(0)
    
    return send_file(output, 
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     attachment_filename="resumen_mensual.xlsx", 
                     as_attachment=True)

@app.route('/nuevo', methods=['POST'])
def nuevo():
    pin_introducido = request.form.get('pin')
    if pin_introducido != PIN_SEGURIDAD:
        return "<h3 style='color:red;'>PIN Incorrecto</h3><a href='/crear'>Volver</a>", 403

    elemento = request.form.get('elemento')
    ubicacion = request.form.get('ubicacion')
    if elemento and ubicacion:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO incidencias (elemento, ubicacion) VALUES (%s, %s)", (elemento, ubicacion))
        conn.commit()
        cur.close()
        conn.close()
    return redirect('/')

@app.route('/completar/<int:id>', methods=['POST'])
def completar(id):
    nombre_operario = request.form.get('operario')
    if nombre_operario:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE incidencias SET estado='Realizado', operario=%s WHERE id=%s", (nombre_operario, id))
        conn.commit()
        cur.close()
        conn.close()
    return redirect('/')

if __name__ == '__main__':
    app.run()
