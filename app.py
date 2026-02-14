import os
import sqlite3
from flask import Flask, render_template, request, redirect

app = Flask(__name__)

# Definimos dónde se guarda el archivo de datos
DB_PATH = os.path.join(os.path.dirname(__file__), 'mantenimiento.db')

def init_db():
    """Esta función crea la tabla si no existe"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS incidencias 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, 
             elemento TEXT, 
             ubicacion TEXT, 
             estado TEXT DEFAULT 'Pendiente')''')
        conn.commit()

@app.route('/')
def index():
    # EJECUTAMOS LA CREACIÓN SIEMPRE PARA ASEGURARNOS
    init_db()
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Ahora sí encontrará la tabla
        cursor.execute("SELECT * FROM incidencias WHERE estado='Pendiente'")
        pendientes = cursor.fetchall()
        cursor.execute("SELECT * FROM incidencias WHERE estado='Realizado'")
        realizados = cursor.fetchall()
    
    return render_template('index.html', pendientes=pendientes, realizados=realizados)

@app.route('/nuevo', methods=['POST'])
def nuevo():
    elemento = request.form.get('elemento')
    ubicacion = request.form.get('ubicacion')
    if elemento and ubicacion:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO incidencias (elemento, ubicacion) VALUES (?,?)", (elemento, ubicacion))
            conn.commit()
    return redirect('/')

@app.route('/completar/<int:id>')
def completar(id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE incidencias SET estado='Realizado' WHERE id=?", (id,))
        conn.commit()
    return redirect('/')

if __name__ == '__main__':
    # Esto es para que funcione en Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
