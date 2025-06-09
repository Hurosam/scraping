from flask import Flask
app = Flask(__name__)
@app.route('/')
def hello():
    return "<h1>¡El servidor de prueba funciona!</h1><p>Si ves esto, tu instalación de Flask está correcta.</p>"
if __name__ == '__main__':
    print(">>> Iniciando servidor de PRUEBA en http://127.0.0.1:5000")
    print(">>> Si esto funciona, el problema está en app.py o en la base de datos.")
    app.run(debug=True)