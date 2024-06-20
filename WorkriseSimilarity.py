import streamlit as st
import openai
import fitz  # PyMuPDF
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

openai.api_key = st.secrets["OPENAI_API_KEY"]["api_key"]

# Define the function to get similarity score from the API
def get_similarity_score(human_summary, ai_summary):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Compare the following summaries and provide reasons why they are similar or not similar."},
            {"role": "user", "content": f"Human Summary: {human_summary}\nAI Summary: {ai_summary}"}
        ]
    )
    return response["choices"][0]["message"]["content"]

# Define the function to get accuracy score from the API
def get_accuracy_score(pdf_text, company_name, role_description, ai_summary):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Review the following resume content, company name, and role description, and provide an accuracy score for the AI summary from 1-100 with reasons Base the score off of how well the summary matches the resume and the skills needed for the specific company and role description."},
            {"role": "user", "content": f"Resume Content: {pdf_text}\nCompany Name: {company_name}\nRole Description: {role_description}\nAI Summary: {ai_summary}"}
        ]
    )
    return response["choices"][0]["message"]["content"]

# Extract text from the uploaded PDF
def extract_text_from_pdf(pdf_file):
    pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = ""
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        text += page.get_text()
    return text

# Calculate similarity score using vectorization
def calculate_vector_similarity(human_summary, ai_summary):
    vectorizer = TfidfVectorizer().fit_transform([human_summary, ai_summary])
    vectors = vectorizer.toarray()
    cosine_sim = cosine_similarity(vectors)
    return cosine_sim[0, 1] * 100  # Convert to percentage

st.title("Summary Comparison and Accuracy Checker")

# Inputs for company name and role description
company_name = st.text_input("Company Name")
role_description = st.text_input("Role Description")

# Upload PDF resumes
uploaded_file = st.file_uploader("Upload PDF Resume", type=["pdf"])

# Text inputs for human-made and AI-made summaries
st.write("### Human-made Summary and AI-made Summary")
col1, col2 = st.columns(2)

with col1:
    human_summary = st.text_area("Human-made Summary")

with col2:
    ai_summary = st.text_area("AI-made Summary")

if st.button("Compare Summaries"):
    if human_summary and ai_summary:
        similarity_score = calculate_vector_similarity(human_summary, ai_summary)
        reasons = get_similarity_score(human_summary, ai_summary)
        st.write("### Similarity Score")
        st.write(f"{similarity_score:.2f}%")
        st.write("### Reasons for Similarity/Dissimilarity")
        st.write(reasons)

if st.button("Check Accuracy"):
    if uploaded_file and company_name and role_description and ai_summary:
        pdf_text = extract_text_from_pdf(uploaded_file)
        response_text = get_accuracy_score(pdf_text, company_name, role_description, ai_summary)
        st.write("### Accuracy Score Response")
        st.write(response_text)