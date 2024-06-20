import fitz  # PyMuPDF
import streamlit as st
import openai
from datetime import datetime, timedelta

st.title("Workrise Resume Builder")

# Initialize OpenAI client
openai.api_key = st.secrets["OPENAI_API_KEY"]["api_key"]

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "summaries_generated" not in st.session_state:
    st.session_state.summaries_generated = False

if "final_message_displayed" not in st.session_state:
    st.session_state.final_message_displayed = False

if "success_message" not in st.session_state:
    st.session_state.success_message = ""

if "success_message_time" not in st.session_state:
    st.session_state.success_message_time = None

if "last_input" not in st.session_state:
    st.session_state.last_input = ""

if "clarification_message" not in st.session_state:
    st.session_state.clarification_message = ""

if "original_summary" not in st.session_state:
    st.session_state.original_summary = ""

if "new_summary" not in st.session_state:
    st.session_state.new_summary = ""

if "candidate_info" not in st.session_state:
    st.session_state.candidate_info = []

if "inputs_collected" not in st.session_state:
    st.session_state.inputs_collected = False

if "summaries" not in st.session_state:
    st.session_state.summaries = []

if "candidate_names" not in st.session_state:
    st.session_state.candidate_names = []

# Initialize text variable
texts = []

# Upload multiple PDF files
uploaded_files = st.file_uploader("Upload PDF files", type="pdf", accept_multiple_files=True)

# Extract text from the uploaded PDFs
def extract_text_from_pdfs(files):
    texts = []
    for file in files:
        pdf_document = fitz.open(stream=file.read(), filetype="pdf")
        text = ""
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            text += page.get_text()
        texts.append(text)
    return texts

if uploaded_files:
    texts = extract_text_from_pdfs(uploaded_files)

# Extract the candidate's name (assuming the name is always the first line)
def extract_name(text):
    return text.split('\n')[0]

# Prompt the user for a company name, role description, and recipient of the summary
col1, col2 = st.columns(2)
with col1:
    company_name = st.text_input("Enter the company name:")
with col2:
    role_description = st.text_input("Enter the role description:")

st.write("----------------------------------------------------------------------------------------------------------------------------------------")
recipient_name = st.text_input("Enter the recipient of the summary:")

# Store the inputs in the session state
if company_name:
    st.session_state.company_name = company_name

if role_description:
    st.session_state.role_description = role_description

if recipient_name:
    st.session_state.recipient_name = recipient_name

# Collect expected pay and availability before processing
if texts and not st.session_state.inputs_collected:
    st.session_state.candidate_info.clear()
    st.session_state.candidate_names.clear()
    for i, text in enumerate(texts):
        candidate_name = extract_name(text)
        st.session_state.candidate_names.append(candidate_name.lower().replace(" ", ""))
        st.write("----------------------------------------------------------------------------------------------------------------------------------------")
        col1, col2 = st.columns(2)
        with col1:
            expected_pay = st.text_input(f"Expected pay of {candidate_name}", key=f"pay_{i}")
        with col2:
            availability = st.text_input(f"Availability of {candidate_name}", key=f"availability_{i}")

        st.session_state.candidate_info.append({
            "name": candidate_name,
            "pay": expected_pay,
            "availability": availability,
            "resume_text": text,
            "summary": ""  # Initialize the summary field
        })

    if st.button("Confirm Details and Process"):
        st.session_state.inputs_collected = True

# Function to process and generate summaries
def generate_summaries():
    summaries = []
    for candidate in st.session_state.candidate_info:
        st.session_state.messages.append({
            "role": "user",
            "content": f"Company Name: {st.session_state.company_name}\nRole Description: {st.session_state.role_description}\n\nResume Text: {candidate['resume_text']}\n\nIdentify key skills and experience relevant to the role description and company name. Include six to seven bullet points with no more than twenty words each. The first bullet point should include years of experience in relevant areas, the next few bullet points should include more key skills relevant to the company name and role description, and the last bullet point should include specific technologies or tools the candidate is familiar with (for example Microsoft Office Suite (Word, Excel, Outlook, etc))."
        })

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
            stream=False,
        )

        response_text = response["choices"][0]["message"]["content"]

        st.session_state.messages.append({"role": "assistant", "content": response_text})
        candidate['summary'] = response_text  # Update the candidate's summary
        summaries.append(candidate)
    return summaries

# Generate summaries immediately after confirming details
if st.session_state.inputs_collected and not st.session_state.summaries_generated:
    summaries = generate_summaries()
    st.session_state.summaries = summaries
    st.session_state.summaries_generated = True

# Function to handle chat input for editing summaries
def handle_chat_input():
    user_input = st.text_input("Please include the name of the candidate you would like to edit:", key="chat_input")
    if user_input and user_input != st.session_state.last_input:
        st.session_state.last_input = user_input
        candidate_found = False
        normalized_user_input = user_input.lower().replace(" ", "")
        for candidate in st.session_state.candidate_info:
            normalized_candidate_name = candidate['name'].lower().replace(" ", "")
            if normalized_candidate_name in normalized_user_input or normalized_user_input in normalized_candidate_name:
                candidate_found = True
                st.session_state.original_summary = candidate['summary']
                st.session_state.messages.append({
                    "role": "user",
                    "content": f"Please ensure that the output is a summary in bullet point format.\n\n{user_input}"
                })

                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages
                    ],
                    stream=False,
                )
                
                response_text = response["choices"][0]["message"]["content"]

                st.session_state.messages.append({"role": "assistant", "content": response_text})

                # Check if the API response is in bullet point format
                if response_text.strip().startswith("•") or response_text.strip().startswith("-"):
                    # Update the new summary with the changes
                    st.session_state.new_summary = response_text
                else:
                    st.session_state.new_summary = f"Clarification needed for {candidate['name']}: {response_text}"

                st.experimental_rerun()
                break

        if not candidate_found:
            st.session_state.new_summary = "Please specify which candidate you would like to edit the summary of."
            st.experimental_rerun()

# Function to handle the summary comparison and user decision
def handle_summary_decision():
    if st.session_state.new_summary:
        st.write("### Keep the new summary?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes"):
                for candidate in st.session_state.candidate_info:
                    if candidate['summary'] == st.session_state.original_summary:
                        candidate['summary'] = st.session_state.new_summary
                st.session_state.new_summary = ""
                st.session_state.original_summary = ""
                st.experimental_rerun()
        with col2:
            if st.button("No"):
                st.session_state.messages.append({
                    "role": "user",
                    "content": "Don't use this new summary, revert to the last version of the summary for future changes."
                })
                st.session_state.new_summary = ""
                st.session_state.original_summary = ""
                st.experimental_rerun()

# Display the summaries and chat bar for editing
if st.session_state.summaries_generated:
    for candidate in st.session_state.summaries:
        st.write(f"### Key Skills and Experience for {candidate['name']}")
        st.markdown(candidate['summary'])
        st.write(f"**Expected Pay:** {candidate['pay']}")
        st.write(f"**Availability:** {candidate['availability']}")

    handle_chat_input()

    # Done button to finalize and display all summaries
    if st.button("Done"):
        st.session_state.final_message_displayed = True
        st.write(f"Hello {st.session_state.recipient_name},")
        st.write(f"Please see the attached resumes for these {len(st.session_state.summaries)} candidates interested in the {st.session_state.role_description} position with {st.session_state.company_name}.")

        for summary in st.session_state.summaries:
            st.write(f"### Key Skills and Experience for {summary['name']}")
            st.markdown(summary['summary'])
            st.write(f"**Expected Pay:** {summary['pay']}")
            st.write(f"**Availability:** {summary['availability']}")

        # Clear summaries after displaying
        st.session_state.summaries = []
        st.session_state.summaries_generated = False
        st.session_state.final_message_displayed = False

        st.stop()

# Display the original and new summary for comparison if a valid edit was submitted
if st.session_state.new_summary:
    st.write("### Compare Summaries")
    col1, col2 = st.columns(2)
    with col1:
        st.write("#### Original Summary")
        st.markdown(st.session_state.original_summary)
    with col2:
        st.write("#### New Summary")
        st.markdown(st.session_state.new_summary)

    handle_summary_decision()