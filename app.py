from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

# Configuración inicial de la base de datos
def init_db():
    with sqlite3.connect('mantenimiento.db') as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS incidencias 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, 
             elemento TEXT, 
             ubicacion TEXT, 
             estado TEXT DEFAULT 'Pendiente')''')

@app.route('/')
def index():
    # Mostramos lo pendiente en la "bolsa" y lo realizado para el reporte
    with sqlite3.connect('mantenimiento.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM incidencias WHERE estado='Pendiente'")
        pendientes = cursor.fetchall()
        cursor.execute("SELECT * FROM incidencias WHERE estado='Realizado'")
        realizados = cursor.fetchall()
    return render_template('index.html', pendientes=pendientes, realizados=realizados)

@app.route('/nuevo', methods=['POST'])
def nuevo():
    elemento = request.form['elemento']
    ubicacion = request.form['ubicacion']
    with sqlite3.connect('mantenimiento.db') as conn:
        conn.execute("INSERT INTO incidencias (elemento, ubicacion) VALUES (?,?)", (elemento, ubicacion))
    return redirect('/')

@app.route('/completar/<int:id>')
def completar(id):
    with sqlite3.connect('mantenimiento.db') as conn:
        conn.execute("UPDATE incidencias SET estado='Realizado' WHERE id=?", (id,))
    return redirect('/')

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0') # '0.0.0.0' permite acceso desde el móvil en la misma red
