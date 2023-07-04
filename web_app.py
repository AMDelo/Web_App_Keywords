import streamlit as st
st.set_page_config(page_title = 'Text Mining',  layout="wide")
from io import StringIO
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
import pandas as pd
import plotly.express as px
import time

st.title('Text Mining - Sustainable Finance Disclosure')

col1,col2 = st.columns(2)

with col1:
    st.write("#### Upload one or more PDF files")
    uploaded_pdfs = st.file_uploader('s', accept_multiple_files = True, label_visibility='collapsed')

with col2:
    st.write("#### Write one or more keywords separated by a comma")
    keywords = st.text_input('s', help = 'Split keywords by comma', label_visibility='collapsed')

#remove spaces if they exist
keywords = keywords.replace(" ", "")

# Replace ';' with ','
keywords = keywords.replace(";", ",")

keywords = keywords.split(',')


if len(uploaded_pdfs) == 0:
    st.write("#### Please upload one or more PDF files so the analysis can begin.")
if len(keywords[0]) == 0:
    st.write("#### Please upload one or more keywords.")

elif (len(uploaded_pdfs) !=0) and (len(keywords[0]) != 0):
    with st.spinner("Analyzing PDFs..."):
        st.info("For bigger PDFs, the analysis might take a few minutes")

        @st.cache_data
        def pdf_to_text(pdf):
            manager = PDFResourceManager()
            layout = LAParams(all_texts=False, detect_vertical=True)
            retstr = StringIO()
            converter = TextConverter(manager, retstr, laparams=layout)
            interpreter = PDFPageInterpreter(manager, converter)
            page_texts = []

            for page in PDFPage.get_pages(pdf, check_extractable=False):
                
                interpreter.process_page(page)
                page_texts.append(retstr.getvalue())
                
                retstr.truncate(0)
                retstr.seek(0)
            converter.close()
            retstr.close()
            return page_texts
            
    
        #retrieving the paragraph (if it >= 3 words) from a given keyword
        @st.cache_data
        def find_keywords_in_text(text, keywords, page_num, filename):
            paragraphs = text.split('\n\n')
            matches = []
            keyword_counts = {keyword: 0 for keyword in keywords}
            for i, paragraph in enumerate(paragraphs):
                found_keywords = [keyword for keyword in keywords if keyword.lower() in paragraph.lower()]
                if found_keywords and len(paragraph.split()) >= 3:   #paragraph word length must be higher or equal to 3
                    matches.append({
                        'filename': filename,
                        'page_num': page_num,
                        'paragraph_num': i,
                        'keywords': ', '.join(found_keywords),
                        'paragraph': paragraph
                    })
                    for keyword in found_keywords:
                        keyword_counts[keyword] += paragraph.lower().count(keyword.lower())
            return matches, keyword_counts
        @st.cache_data
        def process_file(pdf, keywords):
            page_texts = pdf_to_text(pdf)
            filename = pdf.name

            matches = []
            keyword_counts_all_pages = {keyword: 0 for keyword in keywords}
            for i, page_text in enumerate(page_texts):
                matches_page, keyword_counts = find_keywords_in_text(page_text, keywords, i + 1, filename)
                matches.extend(matches_page)
                for keyword in keywords:
                    keyword_counts_all_pages[keyword] += keyword_counts[keyword]

            return matches, keyword_counts_all_pages
        
        @st.cache_data
        def process_all_files(pdf_list, keywords):

            pdf_files = [file for file in pdf_list]

            all_matches = []
            all_keyword_counts = []
            for pdf_file in pdf_files:
                start_time = time.time()
                matches, keyword_counts = process_file(pdf_file, keywords)
                all_matches.extend(matches)
                all_keyword_counts.append({**{'filename': pdf_file.name}, **keyword_counts})
                end_time = time.time()
                execution_time = end_time - start_time
                st.write(f"{pdf_file.name} analyzed successfully in {round(execution_time,1)} seconds")
            return all_matches, all_keyword_counts
        

        #keywords = ['ESG', 'Sustainability','Environmental', 'CSRD', 'Climate', 'Green']

        all_matches, all_keyword_counts = process_all_files(uploaded_pdfs, keywords)

        # Convert to a DataFrame
        df_matches = pd.DataFrame(all_matches)
        all_keyword_counts = pd.DataFrame(all_keyword_counts)

        @st.cache_data
        def convert_df(df):
            return df.to_csv(index=False).encode('utf-8')

        st.write('### Paragraphs by keyword matches. View and download data.')

        tab1,tab2 = st.tabs(['Explore Dataset', 'Download'])
        with tab1:
            st.write(df_matches)
        with tab2:
            st.download_button(
                "Press to Download as csv",
                convert_df(df_matches),
                "Keyword_Matches.csv",
                "text/csv",
                key='download-csv-matches'
                )
            

        st.write('### Keyword statistics')

        tab1,tab2 = st.tabs(['Explore Dataset', 'Download'])
        with tab1:
            st.write(all_keyword_counts)
        with tab2:
            st.download_button(
                "Press to Download as csv",
                convert_df(all_keyword_counts),
                "Keyword_Matches.csv",
                "text/csv",
                key='download-csv-keywords'
                )
        fig = px.bar(all_keyword_counts, x=keywords, y= 'filename', title='Term Count')
        st.plotly_chart(fig, theme = 'streamlit')
