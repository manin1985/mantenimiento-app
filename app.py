# Define aquí tu clave secreta (puedes cambiar '1234' por lo que quieras)
CLAVE_ENCARGADO = "1234"

@app.route('/nuevo', methods=['POST'])
def nuevo():
    # Leemos la clave que escribieron en el formulario
    pin_introducido = request.form.get('pin')
    
    if pin_introducido == CLAVE_ENCARGADO:
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
    else:
        # Si la clave es mal, podrías mandar un mensaje de error
        return "Clave incorrecta. No tienes permiso para crear avisos.", 403
