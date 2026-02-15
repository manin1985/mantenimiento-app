import os
import psycopg2
import pandas as pd
from flask import Flask, render_template, request, redirect, send_file, send_from_directory
from io import BytesIO
import time

app = Flask(__name__)

PIN_SEGURIDAD = "2026"
DATABASE_URL = os.environ.get('DATABASE_URL')

# --- LISTA TÉCNICA DE RECAMBIOS ---
LISTA_RECAMBIOS = [
    "ninguno/mano de obra", "PEDAL2400", "PEDAL3200", "cubierta lateral izda", 
    "cubierta lateral dcha", "estructural izda", "estructural dcha", 
    "CONJUNTO EJE PEDAL", "SIRGA", "CABLE 2400", "CABLE 3200", "CHAPA ESPADA", 
    "espada 2400", "espada 3200", "SUBCONJUNTO EMPUJADOR", "TAPA SUPERIOR BRAZO", 
    "ENLACE PEDAL2400", "ENLACE PEDAL 3200", "ENV t.calle3200", "ENV t.calle2200", 
    "ENV t.usuario3200", "ENV t.usuario2200", "ENV conjunto tapa3200", 
    "ENV conjunto tapa2400", "PYC t.calle3200", "PYC t.calle2200", 
    "PYC t.usuario3200", "PYC t.usuario2200", "PYC conjunto tapa3200", 
    "PYC conjunto tapa2400", "RSU t.calle2200", "RSU t.calle3200", 
    "RSU t.usuario3200", "RSU t.usuario2200", "RSU esquina dcha", 
    "RSU esquina izda", "conjunto espada izda2400", "conjunto espada dcha2400", 
    "conjunto espada izda3200", "conjunto espada dcha3200", "OTROS (especificar en notas)"
]

def get_db_connection():
    for i in range(5):
        try:
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=15)
            return conn
        except:
            time.sleep(3)
    return psycopg2.connect(DATABASE_URL)

def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS incidencias 
            (id SERIAL PRIMARY KEY, 
             elemento TEXT NOT NULL, 
             ubicacion TEXT NOT NULL, 
             estado TEXT DEFAULT 'Pendiente',
             fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
             operario TEXT,
             prioridad TEXT DEFAULT 'Media',
             recambio TEXT)''')
        try: cur.execute("ALTER TABLE incidencias ADD COLUMN operario TEXT")
        except: conn.rollback()
        try: cur.execute("ALTER TABLE incidencias ADD COLUMN prioridad TEXT DEFAULT 'Media'")
        except: conn.rollback()
        try: cur.execute("ALTER TABLE incidencias ADD COLUMN recambio TEXT")
        except: conn.rollback()
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e: print(f"Error DB: {e}")

@app.route('/manifest.json')
def manifest():
    return send_from_directory(os.getcwd(), 'manifest.json')

@app.route('/')
def index():
    init_db()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM incidencias 
        WHERE estado IN ('Pendiente', 'En Proceso') 
        ORDER BY CASE prioridad WHEN 'Alta' THEN 1 WHEN 'Media' THEN 2 ELSE 3 END, fecha DESC
    """)
    pendientes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', pendientes=pendientes, recambios=LISTA_RECAMBIOS)

@app.route('/asignar/<int:id>', methods=['POST'])
def asignar(id):
    nombre = request.form.get('operario')
    if nombre:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE incidencias SET estado='En Proceso', operario=%s WHERE id=%s", (nombre, id))
        conn.commit()
        cur.close()
        conn.close()
    return redirect('/')

@app.route('/completar/<int:id>', methods=['POST'])
def completar(id):
    recambio = request.form.get('recambio')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE incidencias SET estado='Realizado', recambio=%s WHERE id=%s", (recambio, id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')

@app.route('/nuevo', methods=['POST'])
def nuevo():
    if request.form.get('pin') != PIN_SEGURIDAD: return "PIN Incorrecto", 403
    elemento, ubi, prio = request.form.get('elemento'), request.form.get('ubicacion'), request.form.get('prioridad', 'Media')
    if elemento and ubi:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO incidencias (elemento, ubicacion, prioridad) VALUES (%s, %s, %s)", (elemento, ubi, prio))
        conn.commit()
        cur.close()
        conn.close()
    return redirect('/')

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
    df = pd.read_sql("SELECT elemento, ubicacion, prioridad, estado, fecha, operario, recambio FROM incidencias ORDER BY fecha DESC", conn)
    conn.close()
    out = BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as writer: df.to_excel(writer, index=False)
    out.seek(0)
    return send_file(out, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', download_name="reporte_mantenimiento.xlsx", as_attachment=True)

@app.route('/crear')
def pagina_crear(): return render_template('crear.html')

if __name__ == '__main__':
    app.run()
