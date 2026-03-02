import os
import psycopg2
import pandas as pd
from flask import Flask, render_template, request, redirect, send_file, send_from_directory
from io import BytesIO
import time
from datetime import datetime
import pytz # <-- Nueva librería para la hora

app = Flask(__name__)

# Configuramos la zona horaria de Madrid
madrid_tz = pytz.timezone('Europe/Madrid')

# ... (resto de variables igual)

def get_db_connection():
    for i in range(5):
        try:
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=15)
            # FORZAMOS A LA BASE DE DATOS A USAR HORA DE MADRID
            cur = conn.cursor()
            cur.execute("SET TIME ZONE 'Europe/Madrid';")
            return conn
        except:
            time.sleep(3)
    return psycopg2.connect(DATABASE_URL)

# Modificamos la función de GUARDAR NUEVO para que use la hora de Madrid exacta
@app.route('/nuevo', methods=['POST'])
def nuevo():
    if request.form.get('pin') != PIN_SEGURIDAD: return "PIN Incorrecto", 403
    elemento, ubi, prio = request.form.get('elemento'), request.form.get('ubicacion'), request.form.get('prioridad', 'Media')
    
    # Generamos la hora actual de Madrid manualmente para el INSERT
    ahora_madrid = datetime.now(madrid_tz)
    
    if elemento and ubi:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO incidencias (elemento, ubicacion, prioridad, fecha) 
            VALUES (%s, %s, %s, %s)
        """, (elemento, ubi, prio, ahora_madrid))
        conn.commit()
        cur.close()
        conn.close()
    return redirect('/')
