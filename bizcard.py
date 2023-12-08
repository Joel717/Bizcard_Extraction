#importing necessary packages 
import streamlit as st
from streamlit_option_menu import option_menu
from pkg_resources import parse_version
from PIL import Image
if parse_version(Image.__version__) >= parse_version('10.0.0'):
    Image.ANTIALIAS = Image.LANCZOS
import easyocr
import os
import re
import pandas as pd
import psycopg2
import io
import numpy as np

#connecting to postgres database
mydb= psycopg2.connect(host="localhost",
            user="postgres",
            password="postgres",
            database= "bizcard",
            port = "5432"
            )
my_cursor = mydb.cursor()

#creating page title
st.title('_BIZCARD EXTRACTION_')

#creating topbar with options
selected = option_menu(None, [ "Upload", "Delete","About the App"],
                        icons=[ "cloud-upload", "trash","person-circle"],
                        default_index=0,
                        orientation="horizontal",
                        styles={"nav-link": {"font-size": "15px", "text-align": "centre", "margin": "5px",
                                                "--hover-color": "#010101"},
                                "icon": {"font-size": "18px"},
                                "container": {"max-width": "2000px"},
                                "nav-link-selected": {"background-color": "#FFD700"}})


#creating function to save extracted data
def ext(pic):
    ext_data={'Name': [], 'Designation': [], 'Company name': [], 'Contact': [], 'Email': [], 'Website': [],
               'Address': [], 'Pincode': []}
    ext_data['Name'].append(result[0])
    ext_data['Designation'].append(result[1])

    for i in range(2, len(result)):
        if (result[i].startswith('+')) or (result[i].replace('-', '').isdigit() and '-' in result[i]):
            ext_data['Contact'].append(result[i])
        elif '@' in result[i] and '.com' in result[i]:
            small = result[i].lower()
            ext_data['Email'].append(small)
        elif 'www' in result[i] or 'WWW' in result[i] or 'wwW' in result[i]:
            small = result[i].lower()
            ext_data['Website'].append(small)
        elif 'TamilNadu' in result[i] or 'Tamil Nadu' in result[i] or result[i].isdigit():
            ext_data['Pincode'].append(result[i])
        elif re.match(r'^[A-Za-z]', result[i]):
            ext_data['Company name'].append(result[i])
        else:
            removed_colon = re.sub(r'[,;]', '', result[i])
            ext_data['Address'].append(removed_colon)
    
    for key, value in ext_data.items():
        if len(value) > 0:
            concatenated_string = ' '.join(value)
            ext_data[key] = [concatenated_string]
        else:
            value = 'NA'
            ext_data[key] = [value]
    return ext_data

#configuring upload
if selected =='Upload':
   st.divider()
   image=st.file_uploader(label="upload image",type=['png', 'jpg', 'jpeg'], label_visibility="hidden")
   @st.cache_data
   #creating function to read image
   def load_image():
    reader=easyocr.Reader(['en'],model_storage_directory='.')
    return reader
    #loading image in the frontend
   reader1=load_image()
   if image is not None:
      input_image=Image.open(image)
      st.image(input_image,width=350,caption="your image")
      result=reader1.readtext(np.array(input_image),detail=0)
      ext_text = ext(result)
      df = pd.DataFrame(ext_text)#adding the extracted data to a df
      st.dataframe(df)
      image_bytes = io.BytesIO()
      input_image.save(image_bytes, format='PNG')
      image_data = image_bytes.getvalue()
      data = {"Image": [image_data]}
      df_1 = pd.DataFrame(data)#adding the image data to df
      concat_df = pd.concat([df, df_1], axis=1)
      col1, col2, col3 = st.columns([1, 6, 1])
      with col2:
            selected = option_menu(
                menu_title=None,
                options=["Preview & Update"],
                icons=['file-earmark'],
                default_index=0,
                orientation="horizontal"
            )

            ext_text = ext(result)
            df = pd.DataFrame(ext_text)
      #configuring a edit menu for the data      
      if selected == "Preview & Update":
            col_1, col_2 = st.columns([4, 4])
            with col_1:
                modified_n = st.text_input('Name', ext_text["Name"][0])
                modified_d = st.text_input('Designation', ext_text["Designation"][0])
                modified_c = st.text_input('Company name', ext_text["Company name"][0])
                modified_con = st.text_input('Mobile', ext_text["Contact"][0])
                concat_df["Name"], concat_df["Designation"], concat_df["Company name"], concat_df[
                    "Contact"] = modified_n, modified_d, modified_c, modified_con
            with col_2:
                modified_m = st.text_input('Email', ext_text["Email"][0])
                modified_w = st.text_input('Website', ext_text["Website"][0])
                modified_a = st.text_input('Address', ext_text["Address"][0][1])
                modified_p = st.text_input('Pincode', ext_text["Pincode"][0])
                concat_df["Email"], concat_df["Website"], concat_df["Address"], concat_df[
                    "Pincode"] = modified_m, modified_w, modified_a, modified_p
            col3, col4 = st.columns([4, 4])
            with col3:
                Preview = st.button("Preview modified text")
            with col4:
                Upload = st.button("Upload")
            if Preview:
                filtered_df = concat_df[
                    ['Name', 'Designation', 'Company name', 'Contact', 'Email', 'Website', 'Address', 'Pincode']]
                st.dataframe(filtered_df)
            else:
                pass
            #uploading the data to sql
            if Upload:
                with st.spinner("In progress"):
                    my_cursor.execute(
                        "CREATE TABLE IF NOT EXISTS BIZCARD(NAME VARCHAR(50), DESIGNATION VARCHAR(100), "
                        "COMPANY_NAME VARCHAR(100), CONTACT VARCHAR(35), EMAIL VARCHAR(100), WEBSITE VARCHAR("
                        "100), ADDRESS TEXT, PINCODE VARCHAR(100))")
                    mydb.commit()
                    A = "INSERT INTO BIZCARD(NAME, DESIGNATION, COMPANY_NAME, CONTACT, EMAIL, WEBSITE, ADDRESS, " \
                        "PINCODE) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                    for index, i in concat_df.iterrows():
                        result_table = (i[0], i[1], i[2], i[3], i[4], i[5], i[6], i[7])
                        my_cursor.execute(A, result_table)
                        mydb.commit()
                        st.success('SUCCESSFULLY UPLOADED', icon="✅")
   else:
        st.write("Upload an image")



# configuring the delete option
if selected=="Delete":
    st.divider()
    col1, col2 = st.columns([4, 4])
    with col1:
        my_cursor.execute("SELECT NAME FROM BIZCARD")
        Y = my_cursor.fetchall()
        names = ["Select"]
        for i in Y:
            names.append(i[0])
        name_selected = st.selectbox("Select the name to delete", options=names)
    with col2:
        my_cursor.execute(f"SELECT DESIGNATION FROM BIZCARD WHERE NAME = '{name_selected}'")
        Z = my_cursor.fetchall()
        designation = ["Select"]
        for j in Z:
            designation.append(j[0])
        designation_selected = st.selectbox("Select the designation of the chosen name", options=designation)
    st.markdown(" ")
    col_a, col_b, col_c = st.columns([5, 3, 3])
    with col_b:
        remove = st.button("Clik here to delete")
    if name_selected and designation_selected and remove:
        my_cursor.execute(
            f"DELETE FROM BIZCARD WHERE NAME = '{name_selected}' AND DESIGNATION = '{designation_selected}'")
        mydb.commit()
        if remove:
            st.warning('DELETED', icon="⚠️")


#configuring the about section
if selected=='About the App':
      
            st.subheader('About the creator:')
            st.markdown('The app is created by: Joel Gracelin ')
            st.markdown('This app is created as a part of Guvi Master Data Science course')
            st.markdown('This Streamlit app is designed to extract information from business cards using EasyOCR (Optical Character Recognition) and allows users to upload, preview, update, and delete extracted data.')
            st.markdown("[Ghithub](https://github.com/Joel717)")
