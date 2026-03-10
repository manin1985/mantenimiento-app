import os
import psycopg2
import pandas as pd
from flask import Flask, render_template, request, redirect, send_file
from io import BytesIO
from datetime import datetime
import pytz

app = Flask(__name__)

PIN_SEGURIDAD = "2026"
DATABASE_URL = os.environ.get('DATABASE_URL')
madrid_tz = pytz.timezone('Europe/Madrid')

# Lista de recambios (abreviada para mejorar carga, puedes ampliarla)
LISTA_RECAMBIOS = ["ninguno/mano de obra", "PEDAL2400", "PEDAL3200", "cubierta lateral izda", "cubierta lateral dcha", "OTROS (especificar)"]

def get_db_connection():
    # Añadimos parámetros para evitar que la conexión se quede "colgada"
    return psycopg2.connect(DATABASE_URL, connect_timeout=5, options="-c statement_timeout=5000")

@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    # Orden optimizado según tu petición anterior
    query = """
        SELECT id, elemento, ubicacion, estado, fecha, operario, prioridad, tipo, fraccion 
        FROM incidencias 
        WHERE estado IN ('Pendiente', 'En Proceso') 
        ORDER BY 
            CASE 
                WHEN tipo = 'Contenedor' AND prioridad = 'Alta' THEN 1
                WHEN tipo = 'Papelera' THEN 2
                WHEN tipo = 'Contenedor' AND prioridad = 'Media' THEN 3
                ELSE 4 
            END ASC, 
            fecha DESC
    """
    cur.execute(query)
    pendientes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', pendientes=pendientes, recambios=LISTA_RECAMBIOS)

@app.route('/nuevo', methods=['POST'])
def nuevo():
    if request.form.get('pin') != PIN_SEGURIDAD: return "PIN Incorrecto", 403
    elemento, ubi, tipo = request.form.get('elemento'), request.form.get('ubicacion'), request.form.get('tipo')
    prio = request.form.get('prioridad', 'Baja') if tipo == 'Contenedor' else 'Baja'
    ahora = datetime.now(madrid_tz)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO incidencias (elemento, ubicacion, prioridad, fecha, tipo, estado) VALUES (%s, %s, %s, %s, %s, 'Pendiente')", (elemento, ubi, prio, ahora, tipo))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')

@app.route('/completar/<int:id>', methods=['POST'])
def completar(id):
    nombres, cantidades = request.form.getlist('nombres[]'), request.form.getlist('cantidades[]')
    fraccion, otro = request.form.get('fraccion', 'N/A'), request.form.get('recambio_otro')
    resumen = [f"{c}x {n}" for n, c in zip(nombres, cantidades) if n]
    if otro: resumen.append(f"OTROS: {otro}")
    final_txt = ", ".join(resumen) if resumen else "mano de obra"
    ahora = datetime.now(madrid_tz)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE incidencias SET estado='Realizado', recambio=%s, fecha=%s, fraccion=%s WHERE id=%s", (final_txt, ahora, fraccion, id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')

@app.route('/exportar')
def exportar():
    conn = get_db_connection()
    df = pd.read_sql("SELECT tipo, fraccion, elemento, ubicacion, prioridad, fecha, operario, recambio FROM incidencias WHERE estado='Realizado' ORDER BY fecha DESC", conn)
    conn.close()
    if df.empty: return "No hay datos", 404
    df['fecha'] = pd.to_datetime(df['fecha']).dt.strftime('%d/%m/%Y %H:%M')
    out = BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        df[df['tipo'] == 'Contenedor'].drop(columns=['tipo']).to_excel(writer, index=False, sheet_name='CONTENEDORES')
        df[df['tipo'] == 'Papelera'].drop(columns=['tipo', 'fraccion', 'prioridad']).to_excel(writer, index=False, sheet_name='PAPELERAS')
    out.seek(0)
    return send_file(out, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', download_name="Reporte.xlsx", as_attachment=True)

# Rutas básicas para evitar errores de carga
@app.route('/crear')
def pagina_crear(): return render_template('crear.html')

@app.route('/historial')
def historial():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, elemento, ubicacion, estado, fecha, operario, prioridad, recambio, tipo, fraccion FROM incidencias WHERE estado='Realizado' ORDER BY fecha DESC LIMIT 100")
    realizados = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('historial.html', realizados=realizados)

@app.route('/asignar/<int:id>', methods=['POST'])
def asignar(id):
    nombre = request.form.get('operario')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE incidencias SET estado='En Proceso', operario=%s WHERE id=%s", (nombre, id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
