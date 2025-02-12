import time
import google.generativeai as genai
import streamlit as st

genai.configure(api_key="AIzaSyDbKnf40fbGHTHDg14USNdzoNlGmxKfVe8")

def upload_to_gemini(path, mime_type=None):
  """Uploads the given file to Gemini.

  See https://ai.google.dev/gemini-api/docs/prompting_with_media
  """
  file = genai.upload_file(path, mime_type=mime_type)
  print(f"Uploaded file '{file.display_name}' as: {file.uri}")
  return file

def wait_for_files_active(files):
  """Waits for the given files to be active.

  Some files uploaded to the Gemini API need to be processed before they can be
  used as prompt inputs. The status can be seen by querying the file's "state"
  field.

  This implementation uses a simple blocking polling loop. Production code
  should probably employ a more sophisticated approach.
  """
  print("Waiting for file processing...")
  for name in (file.name for file in files):
    file = genai.get_file(name)
    while file.state.name == "PROCESSING":
      print(".", end="", flush=True)
      time.sleep(10)
      file = genai.get_file(name)
    if file.state.name != "ACTIVE":
      raise Exception(f"File {file.name} failed to process")
  print("...all files ready")
  print()


# Streamlit interface
st.title("VIT Faculty Query System")

# Use a static file path (no need for file upload)
file_path = "VIT_Faculty_Details.csv"  # Path to your *predefined* CSV file

# Upload the predefined file only *once* (outside the main loop)
try:
  files = [upload_to_gemini(file_path, mime_type="text/csv")]
  wait_for_files_active(files)
except FileNotFoundError:
  st.error(f"File '{file_path}' not found. Please make sure the file exists in the correct location.")
  st.stop()  # Stop execution if the file is not found
except Exception as e:
  st.error(f"An error occurred during file upload or processing: {e}")
  st.stop()


# Create the model
generation_config = {
  "temperature": 0.5,
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
  model_name="gemini-2.0-flash",
  generation_config=generation_config,
)

# TODO Make these files available on the local file system
# You may need to update the file paths
files = [
  upload_to_gemini("VIT_Faculty_Details.csv", mime_type="text/csv"),
]

# Some files have a processing delay. Wait for them to be ready.
wait_for_files_active(files)

chat_session = model.start_chat(
  history=[
    {
      "role": "user",
      "parts": [
        files[0],
        "You are given a file containing the details about the faculties working in Vellore Institute of Technology(VIT). Your job is to answer to the queries based on the details you have from the file on to the point. Do not create your own details by combining multiple rows. Each row is unique for a particular faculty and provide the responses onto the point in markdown format without any additional text.",
      ],
    },
    {
      "role": "model",
      "parts": [
        "Okay, I understand. I'm ready to analyze the faculty data and answer your questions to the best of my ability without hallucinating anything in markdown format.\n",
      ],
    },
  ]
)

initial_history = chat_session.history # Store the initial history

# Initialize chat history in Streamlit's session state
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if user_input := st.chat_input("Your query"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    current_history = initial_history + [
        {
            "role": "user",
            "parts": [user_input]
        }
    ]

    chat_session.history = current_history
    with st.spinner("Generating response..."):
        response = chat_session.send_message(user_input)
        st.session_state.messages.append({"role": "assistant", "content": response.text})  # Store in history
        with st.chat_message("assistant"):
            st.markdown(response.text)