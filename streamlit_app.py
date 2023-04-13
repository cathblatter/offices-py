# streamlit_app.py

import streamlit as st
from supabase import create_client, Client
import pandas as pd
import json
import datetime as dt
# from plotnine import *

### UI set page to wide
st.set_page_config(layout="wide")

# Initialize connection.
# Uses st.cache_resource to only run once.
@st.cache_resource
def init_connection():
    url = st.secrets["supabase_url"]
    key = st.secrets["supabase_key"]
    return create_client(url, key)

supabase = init_connection()

# Perform query.
# Uses st.cache_data to only rerun when the query changes or after 10 min.
# @st.cache_data(ttl=60)
def run_query(tbl_name):
    return supabase.table(tbl_name).select("*").execute()

#### non-changing information #####
# import the dataframe for the room coordinates
room_coords_og = pd.DataFrame(run_query("room_coords_og").data)
room_coords_og['capacity'] = pd.Categorical(room_coords_og['capacity'], 
                                            categories=['0','1','2','3','4','5'])

room_coords_ug = pd.DataFrame(run_query("room_coords_ug").data)
room_coords_ug['capacity'] = pd.Categorical(room_coords_ug['capacity'], 
                                            categories=['0','1','2','3','4','5'])

# Define the available rooms, places and time slots
room_cap = pd.DataFrame({'roomno': ["113", "115", "117"],
                         'cap': [3, 3, 1]})

#### actual database #####


#### UI inputs #####
rooms = ["113", "115", "117"]
time_slots = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", 
              "14:00", "15:00", "16:00", "17:00", "18:00"]

##### functions for reformatting data #####

# get data
def get_data(query): 
   rows = run_query(query)
   df = pd.DataFrame(rows.data)
   return(df)

# long data format
def create_long_df(df):
    df = (df
         .melt(id_vars=['id', 'name', 'roomno'],
               value_vars=['date_start', 'date_end'], 
               var_name='what', 
               value_name='time')
          .groupby('id'))
    return(df)

# create date/time range for each group per hour // aka pad
def create_date_range(group):
    start = group['time'].min()
    end = group['time'].max()
    return pd.date_range(start=start, end=end, freq='H')

# create the hourly dataframe - inputs the result of create_long_df() and uses create_date_range()
def create_hourly_df(df_long): 
   hourly_df = pd.concat([pd.DataFrame({'id': id,
                                     'time': create_date_range(group)}) for id, group in df_long])
   hourly_df = pd.merge(hourly_df, 
                     df[["id", "name", "roomno"]],
                     on='id', how='left')   
   return(hourly_df)

# create hourly occupancy rate
def create_hourly_occ(hourly_df):
   hourly_occ = (hourly_df
             .groupby(['roomno', 'time'])
             .size()
             .reset_index(name='n')
             .merge(room_cap, on='roomno')
             .assign(occ_rate=lambda x: x['n'] / x['cap']))
   return(hourly_occ)

# ##### functions for plotting #####
# def plot_capacity(my_data):
#     qq = (ggplot(my_data, aes('x',
#                              'y', 
#                              fill = 'factor(capacity)')) 
#                   + geom_tile(color = "white", size=3)
#                   + geom_text(aes(label = 'roomno'))
#                   + coord_equal()
#                   + labs(x='Bernoullistrasse', 
#                          y='Schönbeinstrasse')
#                   + scale_fill_manual(values={'0': '#F1F3F5',
#                                               '1': '#B9E4BC',
#                                               '2': '#7BCCC4',
#                                               '3': '#42A2CA',
#                                               '4': '#0768AC',
#                                               '5': '#0CA678'},
#                                                drop=False)
#                   + guides(fill = guide_legend(title = 'Number of places', nrow=1))
#                   + theme(panel_grid=element_blank(), 
#                           panel_background=element_blank(),
#                           legend_position='top',
#                           axis_line=element_blank(),
#                           axis_ticks=element_blank(),
#                           axis_text=element_blank()))
#     return(qq)

# def plot_occ_capacity_cat(my_data):
#     qq = (ggplot(my_data, aes('x', 
#                              'y', 
#                              fill = 'occ_capacity_fill')) 
#                   + geom_tile(color = "white", size=3)
#                   + geom_text(aes(label = 'roomno'))
#                 #   + facet_wrap('floor', nrow=1)
#                   + scale_fill_manual(values={'overbooked': '#9C0629',
#                                                'booked': '#C9081F',
#                                                'most places booked': '#EC7309',
#                                                'some places booked': '#ECB309',
#                                                'empty': '#63B71D'},
#                                                drop=False)
#                   + coord_equal()
#                   + labs(x='Bernoullistrasse', 
#                          y='Schönbeinstrasse')
#                   + guides(fill = guide_legend(title = '', nrow=1))
#                   + theme(panel_grid=element_blank(), 
#                           panel_background=element_blank(),
#                           legend_position='top',
#                           axis_line=element_blank(),
#                           axis_ticks=element_blank(),
#                           axis_text=element_blank()))
#     return(qq)


#### Get and prepare data ####
df = get_data("bookings")
df_long = create_long_df(df)
hourly_df = create_hourly_df(df_long)
hourly_occ = create_hourly_occ(hourly_df)


#### Setup the user interface ####

# get me a title
st.title("""
Hello in the officeworld!
""")

# Define the inputs to display
tab1, tab2 = st.tabs({"Bookings", "Overview"})

with tab1:
   
   # column display from here
   col1, col2 = st.columns(2)
   
   with col1: 
      
      with st.form("my_form"):

        # st.write("Sign up for a room")
        my_name = st.text_input("Name")
        chosen_date = st.date_input("Pick a date")
        t_start = st.time_input('From', dt.time(8, 00), step=3600)
        t_end = st.time_input('To', dt.time(17, 00), step=3600)

        # wrap data for storing
        date_start = json.dumps(dt.datetime.combine(chosen_date, t_start).isoformat())
        date_end = json.dumps(dt.datetime.combine(chosen_date, t_end).isoformat())

        # here I could add an immediate filter for the available rooms for a timeslot...
        room_no = st.selectbox("Available rooms", 
                               rooms)

        # Every form must have a submit button.
        submitted = st.form_submit_button("Submit")
      
        if submitted:
          data = supabase.table("bookings").insert({"name":my_name,
                                                    "date_start":date_start,
                                                    "date_end":date_end,
                                                    "roomno": room_no,
                                                    }).execute()
          assert len(data.data) > 0

          st.write("thanks for signing up!")
          
   with col2:
      
      st.write("Mirror database")

      # get data and format as DF
      df = get_data("bookings")

      st.dataframe(df)

  #     pp = plot_occ_capacity_cat(match_data)
  #     st.pyplot(ggplot.draw(pp))

  #     # also look at the dataframe
  #     # st.dataframe(match_data)

with tab2: 
   
   st.write("test")