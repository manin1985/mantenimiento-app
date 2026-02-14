import os
import psycopg2
from flask import Flask, render_template, request, redirect

app = Flask(__name__)

# PEGA AQUÍ la "Internal Database URL" que copiaste de Render
# Si no la tienes a mano, el código intentará buscarla automáticamente
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

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
