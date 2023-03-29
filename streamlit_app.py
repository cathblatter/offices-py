# streamlit_app.py

import pandas as pd
import numpy as np
import datetime
import streamlit as st
from plotnine import *
from plotnine.data import mtcars


# Read in data from the Google Sheet.
# Uses st.cache_data to only rerun when the query changes or after 10 min.
@st.cache_data(ttl=60)

# functions
def load_data(sheets_url):
    csv_url = sheets_url.replace("/edit#gid=", "/export?format=csv&gid=")
    return pd.read_csv(csv_url, on_bad_lines='skip')

def plot_capacity(my_data):
    qq = (ggplot(my_data, aes('x', 
                             'y', 
                             fill = 'factor(capacity)')) 
                  + geom_tile(color = "white", size=3)
                  + geom_text(aes(label = 'roomno'))
                  + coord_equal()
                  + facet_wrap('floor', nrow=1)
                  + labs(x='Bernoullistrasse', 
                         y='Schönbeinstrasse')
                  + scale_fill_brewer(palette=4)
                  + guides(fill = guide_legend(title = 'Number of places', nrow=1))
                  + theme(panel_grid=element_blank(), 
                          panel_background=element_blank(),
                          legend_position='top',
                          axis_line=element_blank(),
                          axis_ticks=element_blank(),
                          axis_text=element_blank()))
    return(qq)

def plot_occ_capacity_cat(my_data):
    qq = (ggplot(my_data, aes('x', 
                             'y', 
                             fill = 'occ_capacity_fill')) 
                  + geom_tile(color = "white", size=3)
                  + geom_text(aes(label = 'roomno'))
                  + facet_wrap('floor', nrow=1)
                  + scale_fill_manual(values={'overbooked': '#9C0629',
                                               'booked': '#C9081F',
                                               'most places booked': '#EC7309',
                                               'some places booked': '#ECB309',
                                               'empty': '#63B71D'},
                                               drop=False)
                  + coord_equal()
                  + labs(x='Bernoullistrasse', 
                         y='Schönbeinstrasse')
                  + guides(fill = guide_legend(title = '', nrow=1))
                  + theme(panel_grid=element_blank(), 
                          panel_background=element_blank(),
                          legend_position='top',
                          axis_line=element_blank(),
                          axis_ticks=element_blank(),
                          axis_text=element_blank()))
    return(qq)

# import the dataframe where you sign up
df = load_data(st.secrets["public_gsheets_url"])

# import the dataframe for the room coordinates
room_coords = load_data(st.secrets["coord_gsheets_url"])

# room_coords_og = room_coords[room_coords['floor'] == 'OG']
# room_coords_ug = room_coords[room_coords['floor'] == 'UG']

link_to_sheet = st.secrets["public_gsheets_url"]

# Setup the user interface

# get me a title
st.title("""
Hello in the officeworld!
""")

# link to the google sheet
# st.write(link_to_sheet)

# Define the inputs to display
tab1, tab2 = st.tabs({'Overview by date', 'Base capacity'})


with tab1:
   
   # column display from here
   col1, col2 = st.columns(2)
   
   with col1: 
      st.header("By date")
      chosen_date = pd.to_datetime(st.date_input("Pick a date"))
      st.write('The following people signed up on:', chosen_date)

      # convert the date column
      df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')

      # filter the dataframe
      df_filter = df[df['date'] == chosen_date]

      # display the filtered dataframe
      st.dataframe(df_filter[['name', 'roomno', 'date']])


   with col2:

      # calculate how many people are per room on a given day
      n_per_room = pd.DataFrame(df_filter.groupby('roomno').size().reset_index(name='n'))

      # match this with the base room capacity
      match_data = pd.merge(room_coords, n_per_room, how='left', on='roomno')
      match_data['n'].fillna(0, inplace=True)
      match_data['occ_capacity'] = match_data['n']/match_data['capacity']
      match_data['occ_capacity'].fillna(1, inplace=True)

      # new overbooking colour
      # create a list of our conditions
          
      conditions = [
         (match_data['occ_capacity'] > 1),
         (match_data['occ_capacity'] == 1),
         (match_data['occ_capacity'] >= .5) & (match_data['occ_capacity'] < 1),
         (match_data['occ_capacity'] < 0.5) & (match_data['occ_capacity'] > 0),
         (match_data['occ_capacity'] == 0)
         ]

      # create a list of the values we want to assign for each condition
      values = ['overbooked', 'booked', 'most places booked', 'some places booked', 'empty']

      # create a new column and use np.select to assign values to it using our lists as arguments
      match_data['occ_capacity_fill'] = np.select(conditions, values)
      match_data['occ_capacity_fill'] = pd.Categorical(match_data['occ_capacity_fill'], 
                                                       categories=values)


      pp = plot_occ_capacity_cat(match_data)
      st.pyplot(ggplot.draw(pp))

      # also look at the dataframe
      # st.dataframe(match_data)



with tab2:
      
    # col21, col22 = st.columns(2)
    
    # with col21:
    #   st.write("OG")
    p = plot_capacity(room_coords)
    st.pyplot(ggplot.draw(p))

    # with col22:
    #   st.write("UG")
    #   p = plot_capacity(room_coords_ug)
    #   st.pyplot(ggplot.draw(p))