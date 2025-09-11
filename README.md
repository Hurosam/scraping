Recordar que para descargar las librerias es el siguiente comando:
pip install -r requirements.txt
También, crear un entorno virtual para las librerias:
python -m venv env

$env:GEMINI_API_KEY="TU_API_KEY_AQUI"

# Observatorio Digital de Noticias de Huánuco

Este es un proyecto que utiliza Python, Flask y la API de Gemini de Google para:
1.  **Recolectar** noticias de la web de fuentes locales.
2.  **Analizar** cada noticia usando Inteligencia Artificial para extraer información clave (categoría, veracidad, relevancia, etc.).
3.  **Visualizar** los resultados en una aplicación web local, permitiendo a los usuarios filtrar y buscar noticias importantes para la región.

### Requisitos

Para que este proyecto funcione, necesitas tener instaladas las siguientes librerías de Python. Puedes instalarlas con el siguiente comando:

```bash
pip install -r requirements.txt
