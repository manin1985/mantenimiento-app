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
    "conjunto espada izda3200", "conjunto espada dcha3200", "OTROS (especificar)"
]

def get_db_connection():
    for i in range(5):
        try:
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
            cur = conn.cursor()
            cur.execute("SET TIME ZONE 'Europe/Madrid';")
            cur.close()
            return conn
        except:
            time.sleep(1)
    return psycopg2.connect(DATABASE_URL)

@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, elemento, ubicacion, estado, fecha, operario, prioridad FROM incidencias WHERE estado IN ('Pendiente', 'En Proceso') ORDER BY CASE prioridad WHEN 'Alta' THEN 1 WHEN 'Media' THEN 2 ELSE 3 END, fecha DESC")
    pendientes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', pendientes=pendientes, recambios=LISTA_RECAMBIOS)

@app.route('/nuevo', methods=['POST'])
def nuevo():
    if request.form.get('pin') != PIN_SEGURIDAD: return "PIN Incorrecto", 403
    elemento, ubi, prio = request.form.get('elemento'), request.form.get('ubicacion'), request.form.get('prioridad', 'Media')
    ahora = datetime.now(madrid_tz)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO incidencias (elemento, ubicacion, prioridad, fecha) VALUES (%s, %s, %s, %s)", (elemento, ubi, prio, ahora))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')

@app.route('/completar/<int:id>', methods=['POST'])
def completar(id):
    nombres = request.form.getlist('nombres[]')
    cantidades = request.form.getlist('cantidades[]')
    otro = request.form.get('recambio_otro')
    resumen = [f"{c}x {n}" for n, c in zip(nombres, cantidades) if n]
    if otro: resumen.append(f"OTROS: {otro}")
    final_txt = ", ".join(resumen) if resumen else "mano de obra"
    ahora = datetime.now(madrid_tz) # Actualizamos la fecha al momento de terminar
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE incidencias SET estado='Realizado', recambio=%s, fecha=%s WHERE id=%s", (final_txt, ahora, id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')

@app.route('/historial')
def historial():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, elemento, ubicacion, estado, fecha, operario, prioridad, recambio FROM incidencias WHERE estado='Realizado' ORDER BY fecha DESC LIMIT 150")
    realizados = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('historial.html', realizados=realizados)

@app.route('/exportar')
def exportar():
    try:
        conn = get_db_connection()
        # Seleccionamos las columnas con nombres claros para el Excel
        query = "SELECT elemento, ubicacion, prioridad, estado, fecha as fecha_reparacion, operario, recambio FROM incidencias WHERE estado='Realizado' ORDER BY fecha DESC"
        df = pd.read_sql(query, conn)
        conn.close()

        if df.empty:
            return "No hay datos para exportar", 404

        # Formatear la fecha para que sea legible en Excel
        df['fecha_reparacion'] = pd.to_datetime(df['fecha_reparacion']).dt.strftime('%d/%m/%Y %H:%M')
        
        out = BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Historial')
        
        out.seek(0)
        return send_file(
            out, 
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
            download_name=f"Reporte_{datetime.now().strftime('%Y%m%d')}.xlsx", 
            as_attachment=True
        )
    except Exception as e:
        return f"Error al generar Excel: {str(e)}", 500

# ... (Rutas de editar, borrar, reactivar y crear se mantienen igual que la versión anterior)
