import os
import psycopg2
from flask import Flask, render_template, request, redirect

app = Flask(__name__)

# --- TU NUEVA CLAVE DE ACCESO ---
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
         fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    cur.close()
    conn.close()

# 1. RUTA PARA LOS TRABAJADORES (Solo ven la lista)
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

# 2. RUTA PARA EL ENCARGADO (Solo ve el formulario)
@app.route('/crear')
def pagina_crear():
    return render_template('crear.html')

# 3. RUTA DEL HISTORIAL
@app.route('/historial')
def historial():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM incidencias WHERE estado='Realizado' ORDER BY fecha DESC")
    realizados = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('historial.html', realizados=realizados)

@app.route('/nuevo', methods=['POST'])
def nuevo():
    pin_introducido = request.form.get('pin')
    if pin_introducido != PIN_SEGURIDAD:
        return "<h3>PIN Incorrecto</h3><a href='/crear'>Volver a intentarlo</a>", 403

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

@app.route('/completar/<int:id>')
def completar(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE incidencias SET estado='Realizado' WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')

if __name__ == '__main__':
    app.run()
