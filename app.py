import os
import psycopg2
import pandas as pd
from flask import Flask, render_template, request, redirect, send_file
from io import BytesIO
import time
from datetime import datetime
import pytz

app = Flask(__name__)

PIN_SEGURIDAD = "2026"
DATABASE_URL = os.environ.get('DATABASE_URL')
madrid_tz = pytz.timezone('Europe/Madrid')

LISTA_RECAMBIOS = ["ninguno/mano de obra", "PEDAL2400", "PEDAL3200", "cubierta lateral izda", "cubierta lateral dcha", "estructural izda", "estructural dcha", "CONJUNTO EJE PEDAL", "SIRGA", "CABLE 2400", "CABLE 3200", "CHAPA ESPADA", "espada 2400", "espada 3200", "SUBCONJUNTO EMPUJADOR", "TAPA SUPERIOR BRAZO", "ENLACE PEDAL2400", "ENLACE PEDAL 3200", "ENV t.calle3200", "ENV t.calle2200", "ENV t.usuario3200", "ENV t.usuario2200", "ENV conjunto tapa3200", "ENV conjunto tapa2400", "PYC t.calle3200", "PYC t.calle2200", "PYC t.usuario3200", "PYC t.usuario2200", "PYC conjunto tapa3200", "PYC conjunto tapa2400", "RSU t.calle2200", "RSU t.calle3200", "RSU t.usuario3200", "RSU t.usuario2200", "RSU esquina dcha", "RSU esquina izda", "conjunto espada izda2400", "conjunto espada dcha2400", "conjunto espada izda3200", "conjunto espada dcha3200", "OTROS (especificar)"]

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# Función especial para usuarios "Free" de Render: Crea las columnas si no existen
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Crear columnas nuevas si no existen
    cur.execute("ALTER TABLE incidencias ADD COLUMN IF NOT EXISTS tipo VARCHAR(50) DEFAULT 'Contenedor';")
    cur.execute("ALTER TABLE incidencias ADD COLUMN IF NOT EXISTS fraccion VARCHAR(50) DEFAULT 'N/A';")
    conn.commit()
    cur.close()
    conn.close()

# Ejecutamos la actualización al arrancar la app
init_db()

@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    # Ordenamos: primero papeleras, luego contenedores por prioridad
    cur.execute("SELECT id, elemento, ubicacion, estado, fecha, operario, prioridad, tipo, fraccion FROM incidencias WHERE estado IN ('Pendiente', 'En Proceso') ORDER BY tipo ASC, CASE prioridad WHEN 'Alta' THEN 1 WHEN 'Media' THEN 2 ELSE 3 END, fecha DESC")
    pendientes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', pendientes=pendientes, recambios=LISTA_RECAMBIOS)

@app.route('/crear')
def pagina_crear():
    return render_template('crear.html')

@app.route('/nuevo', methods=['POST'])
def nuevo():
    if request.form.get('pin') != PIN_SEGURIDAD: return "PIN Incorrecto", 403
    elemento = request.form.get('elemento')
    ubi = request.form.get('ubicacion')
    tipo = request.form.get('tipo')
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
    nombres = request.form.getlist('nombres[]')
    cantidades = request.form.getlist('cantidades[]')
    fraccion = request.form.get('fraccion', 'N/A')
    otro = request.form.get('recambio_otro')
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
    # Extraemos todos los realizados
    query = "SELECT tipo, fraccion, elemento, ubicacion, prioridad, fecha, operario, recambio FROM incidencias WHERE estado='Realizado' ORDER BY fecha DESC"
    df = pd.read_sql(query, conn)
    conn.close()
    
    if df.empty: return "No hay datos", 404
    
    df['fecha'] = pd.to_datetime(df['fecha']).dt.strftime('%d/%m/%Y %H:%M')
    
    # Separamos en dos DataFrames
    df_cont = df[df['tipo'] == 'Contenedor']
    df_pap = df[df['tipo'] == 'Papelera']

    out = BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        if not df_cont.empty:
            df_cont.drop(columns=['tipo']).to_excel(writer, index=False, sheet_name='CONTENEDORES')
        if not df_pap.empty:
            df_pap.drop(columns=['tipo', 'fraccion', 'prioridad']).to_excel(writer, index=False, sheet_name='PAPELERAS')
    
    out.seek(0)
    return send_file(out, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', download_name="Reporte_Mantenimiento.xlsx", as_attachment=True)

# ... (Las rutas de editar, borrar y historial siguen igual)
@app.route('/editar/<int:id>', methods=['POST'])
def editar(id):
    if request.form.get('pin') != PIN_SEGURIDAD: return "PIN Incorrecto", 403
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE incidencias SET elemento=%s, ubicacion=%s WHERE id=%s", (request.form.get('elemento'), request.form.get('ubicacion'), id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')

@app.route('/borrar/<int:id>', methods=['POST'])
def borrar(id):
    if request.form.get('pin') != PIN_SEGURIDAD: return "PIN Incorrecto", 403
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM incidencias WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')

@app.route('/historial')
def historial():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, elemento, ubicacion, estado, fecha, operario, prioridad, recambio, tipo, fraccion FROM incidencias WHERE estado='Realizado' ORDER BY fecha DESC LIMIT 150")
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
    app.run()
