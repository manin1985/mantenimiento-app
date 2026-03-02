import os
import psycopg2
import pandas as pd
from flask import Flask, render_template, request, redirect, send_file, send_from_directory
from io import BytesIO
import time
from datetime import datetime
import pytz

app = Flask(__name__)

PIN_SEGURIDAD = "2026"
DATABASE_URL = os.environ.get('DATABASE_URL')
madrid_tz = pytz.timezone('Europe/Madrid')

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
    # Usamos un bloque try-except robusto para asegurar disponibilidad
    for i in range(5):
        try:
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
            cur = conn.cursor()
            cur.execute("SET TIME ZONE 'Europe/Madrid';")
            cur.close()
            return conn
        except Exception as e:
            print(f"Error de conexión ({i+1}/5): {e}")
            time.sleep(1)
    return psycopg2.connect(DATABASE_URL)

@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    # Seleccionamos solo las que no están terminadas
    cur.execute("""
        SELECT id, elemento, ubicacion, estado, fecha, operario, prioridad 
        FROM incidencias 
        WHERE estado IN ('Pendiente', 'En Proceso') 
        ORDER BY CASE prioridad WHEN 'Alta' THEN 1 WHEN 'Media' THEN 2 ELSE 3 END, fecha DESC
    """)
    pendientes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', pendientes=pendientes, recambios=LISTA_RECAMBIOS)

@app.route('/nuevo', methods=['POST'])
def nuevo():
    if request.form.get('pin') != PIN_SEGURIDAD: return "PIN Incorrecto", 403
    elemento = request.form.get('elemento')
    ubi = request.form.get('ubicacion')
    prio = request.form.get('prioridad', 'Media')
    ahora_madrid = datetime.now(madrid_tz)
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO incidencias (elemento, ubicacion, prioridad, fecha) VALUES (%s, %s, %s, %s)", 
               (elemento, ubi, prio, ahora_madrid))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')

@app.route('/asignar/<int:id>', methods=['POST'])
def asignar(id):
    nombre = request.form.get('operario')
    conn = get_db_connection()
    cur = conn.cursor()
    # Doble seguridad: solo asignar si sigue Pendiente
    cur.execute("UPDATE incidencias SET estado='En Proceso', operario=%s WHERE id=%s AND estado='Pendiente'", (nombre, id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')

@app.route('/completar/<int:id>', methods=['POST'])
def completar(id):
    rec_lista = request.form.get('recambio')
    rec_manual = request.form.get('recambio_otro')
    rec_final = f"OTROS: {rec_manual}" if rec_lista and "OTROS" in rec_lista else rec_lista
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE incidencias SET estado='Realizado', recambio=%s WHERE id=%s", (rec_final, id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')

@app.route('/historial')
def historial():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, elemento, ubicacion, estado, fecha, operario, prioridad, recambio FROM incidencias WHERE estado='Realizado' ORDER BY fecha DESC LIMIT 100")
    realizados = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('historial.html', realizados=realizados)

@app.route('/exportar')
def exportar():
    conn = get_db_connection()
    df = pd.read_sql("SELECT elemento, ubicacion, prioridad, estado, fecha, operario, recambio FROM incidencias ORDER BY fecha DESC", conn)
    if not df.empty and 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha']).dt.tz_convert('Europe/Madrid').dt.strftime('%d/%m/%Y %H:%M')
    conn.close()
    out = BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as writer: df.to_excel(writer, index=False)
    out.seek(0)
    return send_file(out, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', download_name="reporte_mantenimiento.xlsx", as_attachment=True)

@app.route('/crear')
def pagina_crear(): return render_template('crear.html')

@app.route('/manifest.json')
def manifest(): return send_from_directory(os.getcwd(), 'manifest.json')

if __name__ == '__main__': app.run()
