import pandas as pd
import nltk
from nltk.tokenize import word_tokenize
from groq import Groq
import streamlit as st

# Descargar los recursos necesarios de NLTK si no los tienes
nltk.download('punkt')

# Inicializar el cliente de Groq
client = Groq(api_key="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")

# Función para cargar datos de archivos .xlsx
def load_xlsx(file_path):
    return pd.read_excel(file_path)

st.set_page_config(
    page_title="Datos Quindío",
    layout="centered", # Forma de layout ancho o compacto
)

# Función para obtener la respuesta de la IA
def get_ai_response(messages):
    completion = client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=messages,
        temperature=0.2,
        max_tokens=512,
        stream=True,
    )
    response = "".join(chunk.choices[0].delta.content or "" for chunk in completion)
    return response

# Función para buscar en los datos cargados
def search_in_data(query, dataframe):
    result = []
    
    # Asegurarse de que el query no sea vacío
    if not query.strip():
        return result
    
    # Buscar el query en todas las columnas de la tabla
    for column in dataframe.columns:
        # Si la columna es de tipo string (objeto), usar str.contains
        if dataframe[column].dtype == 'object':
            # Filtramos las filas donde la columna no es NaN y aplicamos str.contains
            valid_rows = dataframe[column].dropna()
            result += dataframe[valid_rows.str.contains(query, case=False, na=False)].values.tolist()
        
        # Si la columna es de tipo numérico (int o float), buscar coincidencias numéricas
        elif pd.api.types.is_numeric_dtype(dataframe[column]):
            # Verificar si la consulta es un número y buscarlo en la columna
            try:
                numeric_query = float(query)  # Intentamos convertir el query a número
                matching_rows = dataframe[dataframe[column] == numeric_query]
                result += matching_rows.values.tolist()  # Añadimos los resultados encontrados
            except ValueError:
                # Si no se puede convertir el query a número, simplemente lo ignoramos
                pass
    
    return result

# Función para procesar el query (minúsculas y tokenización)
def process_query(query):
    query_lower = query.lower()  # Convertimos a minúsculas
    try:
        query_tokens = word_tokenize(query_lower)  # Tokenizamos el query
    except Exception as e:
        print(f"Error al tokenizar: {e}")
        query_tokens = query_lower.split()  # Si falla, dividimos en espacios
    return " ".join(query_tokens)  # Retornamos el query tokenizado

# Función para reiniciar el chat al cambiar de categoría
def reiniciar_chat():
    """Reinicia el historial del chat cuando se selecciona una nueva categoría."""
    st.session_state['messages'] = []  # Limpiar el historial de mensajes
    st.session_state['dataframe'] = None  # Limpiar el dataframe
    st.session_state['current_category'] = None  # Limpiar la categoría actual

# Función principal del chat
def chat():
    st.title("Información Departamento del Quindío")
    st.write("Bienvenido a tu asistente de información de tu departamento.")

    if 'messages' not in st.session_state:
        st.session_state['messages'] = []

    # Categorías y archivos
    categories = {
        "Cultivos": "EVAS_Quindio.xlsx",
        "Población Vulnerable": "IPM_Quindio.xlsx",
        "Datos socioeconómicos": "Socioeconomico_Quindio.xlsx",
        "Información general": "datos_quindio_generales.xlsx"
    }

    # Selector de categoría
    category = st.selectbox("Selecciona la categoría:", options=list(categories.keys()))

    # Revisar si se seleccionó una nueva categoría
    if 'current_category' not in st.session_state or st.session_state['current_category'] != category:
        # Reiniciar el chat y cargar los datos correspondientes a la nueva categoría
        reiniciar_chat()

        # Cargar el archivo correspondiente basado en la categoría seleccionada
        dataframe = load_xlsx(categories[category])
        st.session_state['dataframe'] = dataframe  # Guardar el dataframe en la sesión
        st.session_state['current_category'] = category  # Guardar la categoría seleccionada

        # Imprimir en consola el cambio de dataset
        print(f"Se ha cargado el dataset para la categoría '{category}' desde el archivo: {categories[category]}")

        # Mensaje de sistema (no se muestra en el chat, solo se usa para el modelo)
        promptSistema = f"""
        Eres un asistente de datos del departamento del Quindío, especializado en: {category}.
        Tu tarea es responder de manera directa y concisa, sin agregar información innecesaria o redundante.
        Si la pregunta puede ser respondida con los datos cargados en el archivo, responde con esos datos. Si no, puedes usar tu conocimiento general.
        """
        st.session_state['messages'].append({"role": "system", "content": promptSistema})

    # Obtener el dataframe desde la sesión
    dataframe = st.session_state.get('dataframe', None)

    # Función para enviar el mensaje
    def submit():
        user_input = st.session_state.user_input
        if user_input.lower() == 'salir':
            st.write("¡Gracias por chatear!")
            st.stop()

        # Procesar el query (convertir a minúsculas y tokenizar)
        processed_query = process_query(user_input)

        # Buscar en los datos del archivo seleccionado primero
        if dataframe is not None:
            search_results = search_in_data(processed_query, dataframe)

            if search_results:
                # Si se encuentra información relevante en los archivos, responder con los resultados
                response = f"Encontré estos resultados en los datos del archivo:\n{search_results}"
                st.session_state['messages'].append({"role": "assistant", "content": response})
            else:
                # Si no se encuentra en los datos, pasar la consulta al modelo LLM
                st.session_state['messages'].append({"role": "user", "content": user_input})
                with st.spinner("Buscando información..."):
                    ai_response = get_ai_response(st.session_state['messages'])
                    # Solo agregar la respuesta del modelo si no se encontró nada en los datos
                    response = ai_response
                    st.session_state['messages'].append({"role": "assistant", "content": ai_response})
        else:
            response = "No se ha cargado ningún archivo para la categoría seleccionada."
            st.session_state['messages'].append({"role": "assistant", "content": response})

        # Limpiar la entrada del usuario
        st.session_state.user_input = ""

    # Mostrar mensajes anteriores
    for message in st.session_state['messages']:
        if message["role"] != "system":  # No mostrar el mensaje del sistema
            role = "Tú" if message["role"] == "user" else "Bot"
            icon = "🤖" if message["role"] == "assistant" else "💬"
            st.write(f"**{role} {icon}:** {message['content']}")  # Mostrar íconos con el rol
    
    # Formulario de entrada de usuario
    with st.form(key='chat_form', clear_on_submit=True):
        st.text_input("Tú:", key="user_input")
        submit_button = st.form_submit_button(label='Enviar', on_click=submit)

# Ejecución principal
if __name__ == "__main__":
    chat()
