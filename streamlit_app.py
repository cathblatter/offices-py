# streamlit_app.py

import streamlit as st
from supabase import create_client, Client
import pandas as pd
import json
import datetime as dt
import altair as alt
from plotnine import *

alt.themes.enable("streamlit")

### UI set page to wide
st.set_page_config(
    page_title="office-bingo",
    page_icon="🎲",
    layout="wide",
    menu_items={
        'Report a bug': "https://github.com/cathblatter/offices-py/issues",
        'About': """
        This is an *extremely* cool app! It's also a lot of work so please be patient if things 
        don't work out as planned. There's no guarantee given by the app for any fixed places - thanks
        for your understanding!
        """
    }
)


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
room_cap = pd.DataFrame({'roomno': ["U03", "115", "117", "U08", "201"],
                         'cap': [5, 3, 1, 1, 1]})

#### actual database #####


#### UI inputs #####
rooms_places = ["U03_1", "U03_2", "U03_3", "U03_4", "U03_5", 
                "115_1", "115_2", "115_3", 
                "117_1"]

zooms_places = ["U08_1",  "201_L"]

all_places = rooms_places+zooms_places

time_slots = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", 
              "14:00", "15:00", "16:00", "17:00", "18:00"]

##### functions for reformatting data #####

# get data
def get_data(query): 
   rows = run_query(query)
   df = pd.DataFrame(rows.data)
   df['date_start_utc'] = pd.to_datetime(df["date_start"])
   df['date_end_utc'] = pd.to_datetime(df["date_end"])
   df['date_start'] = df["date_start_utc"] - pd.Timedelta(hours=2)
   df['date_end'] = df["date_end_utc"] - pd.Timedelta(hours=2)
   df['roomno_place'] = pd.Categorical(df['roomno_place'], categories=all_places)
   df = df.drop(['created_at'], axis=1)
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

#### Get and prepare data ####

# get from database and add room_capacity information
df = get_data("bookings")
df = (df.merge(room_cap, how='left'))

# create a long dataframe to map the hourly occupancy
df_long = create_long_df(df)
hourly_df = create_hourly_df(df_long)
hourly_occ = create_hourly_occ(hourly_df)

#### Setup the user interface ####

# get me a title
st.title("""
Welcome to office-bingo!
""")

st.markdown("🛠️ :orange[this is a pre-release for testing - no guarantee given]")

# Define the inputs to display
tab1, tab2, tab3, tab4 = st.tabs([":bar_chart: Overview", ":calendar: Book a work place ", ":calendar: Book zoom room ", "❌ Cancel booking"])

with tab1:
   
    # time graph
    time_graph = (
                alt.Chart(df)
                .mark_bar()
                .encode(
                x=alt.X('date_start:T', 
                        title="Date and time of booking",
                        axis=alt.Axis(grid=True, gridWidth=2)),
                x2='date_end:T',
                y=alt.Y('roomno_place:O', 
                        title='Office and places', 
                        scale=alt.Scale(domain=all_places)),
                # color=alt.Color('name', legend=None),
                tooltip=[alt.Tooltip('name', title='Name'), 
                        alt.Tooltip('date_start', title='Date'), 
                        alt.Tooltip('hours(date_start)', title='from'), 
                        alt.Tooltip('hours(date_end)', title='to')]
                ).properties(height=400).interactive()
                )

    # today and other reference date value for the axis, 
    # the axis domains, the shading etc
    today = pd.to_datetime(dt.date.today())

    # for domain_pd to see only 1 week from today
    week = today + pd.DateOffset(weeks=1)
    domain_pd = pd.to_datetime([today, week]).astype(int) / 10 ** 6

    # shading one year front and back for today
    past = today - pd.DateOffset(years=1)
    future = today + pd.DateOffset(years=1)

    # create a dataframe with the information
    shading_start = pd.date_range(past, future)

    # the two hours offset are for matching the weird TZ difference
    shading_start = shading_start - pd.DateOffset(hours=2)
    shading_end = shading_start + pd.DateOffset(hours=24)

    shading = {'start': shading_start, 'end': shading_end}
    shading = pd.DataFrame(shading)
    shading['color'] = ['a', 'b'] * int((len(shading)/2))
    shading['weekday'] = shading['start'].dt.isocalendar().day

    # st.dataframe(shading)

    # add day shading
    # unsupported idea: add day gridline (mark_line()) then 
    # add time shading (22-06 (night), (day))
    day_shading = (
              alt.Chart(shading)
              .mark_rect(opacity=0.1)
              .encode(
                x=alt.X('start:T', 
                        scale = alt.Scale(domain=list(domain_pd))),
                x2='end:T', 
                fill=alt.Fill('color', 
                              scale = alt.Scale(domain=['a', 'b'], range=['white', 'grey']),
                              legend=None)
            )
    )

    # weekend_shading = (
    #           alt.Chart(shading)
    #           .mark_rect(opacity=0.5)
    #           .encode(
    #             x=alt.X('start:T', 
    #                     scale = alt.Scale(domain=list(domain_pd))),
    #             x2='end:T', 
    #             fill=alt.Fill('weekday',
    #                           legend=None)
    #         )
    # )

    st.header("Overview of all bookings by room/place")

    st.markdown("""
    - Default display is the current week - you can drag the chart horizontally
    - Hover over the coloured bars to see more information on the booking
    """)

    st.altair_chart((time_graph + 
                     day_shading).interactive(), 
                        theme='streamlit', 
                        use_container_width=True)

with tab2:
   
   st.header("Book a work place 👨‍💻 ")
   st.markdown("*You need a place to work for a fixed number of hours or a whole day while being at the INS, mostly doing quiet work.*")
   
   # column display from here
   col1, col2 = st.columns([1, 1])
   
   with col1: 

      with st.form("check_rooms"):
        chosen_date = st.date_input("Pick a date")
        t_start = st.time_input('From', dt.time(8, 00), step=3600)
        t_end = st.time_input('To', dt.time(17, 00), step=3600)

        check_rooms = st.form_submit_button("Check available rooms")

        if check_rooms: 
          
          # filtering the available spots to display for the room
          start = dt.datetime.combine(chosen_date, t_start).isoformat()
          end = dt.datetime.combine(chosen_date, t_end).isoformat()
          dat = df[df['roomno_place'].isin(rooms_places)]
          dat = dat[((dat['date_start_utc'] <= end) & 
                    (dat['date_end_utc'] >= start))]
          places = dat['roomno_place'].drop_duplicates().tolist()
          av_places = set(rooms_places)
          av_places = av_places.difference(places)
          av_places = list(av_places)
          av_places.sort()

          st.write("These places are available - select one with 'copy to clipboard':", av_places)

   with col2: 

      with st.form("book_rooms"):
    
        my_name = st.text_input("Name")
        roomno_place = st.text_input("Paste/enter your chosen place here:")

        # Every form must have a submit button.
        submitted = st.form_submit_button("Book place")
             
        if submitted:
                
            # modify and wrap data for storing in database
            roomno_place = roomno_place.replace('"', '')
            roomno = roomno_place.split("_")[0]
            place = roomno_place.split("_")[1]
            date_start = json.dumps(dt.datetime.combine(chosen_date, t_start).isoformat())
            date_end = json.dumps(dt.datetime.combine(chosen_date, t_end).isoformat())

            data = supabase.table("bookings").insert({"name":my_name,
                                                            "date_start":date_start,
                                                            "date_end":date_end,
                                                            "roomno_place": roomno_place,
                                                            "roomno": roomno,
                                                            "place": place,
                                                            }).execute()
            assert len(data.data) > 0

            # also write data into shadow-db
            data2 = supabase.table("bookings_shadow").insert({"name":my_name,
                                                            "date_start":date_start,
                                                            "date_end":date_end,
                                                            "roomno_place": roomno_place,
                                                            "roomno": roomno,
                                                            "place": place,
                                                            }).execute()
            assert len(data2.data) > 0

            st.write("Thanks for signing up!")
                
            # update the available database
            df = get_data('bookings')

with tab3: 
   
   st.header("Book a zoom room 🎥 ")
   
   st.markdown("*You need a room for a reduced number of time to zoom (while not disturbing your office-colleagues).*")
   
   # st.markdown("+Please don't book these rooms for whole days (if not in zooms) - thanks!")

   # st.write("🚧 under construction 🚧")

# column display from here
   col1, col2 = st.columns([1, 1])
   
   with col1: 

      with st.form("check_zoom_rooms"):
        chosen_date = st.date_input("Pick a date")
        t_start = st.time_input('From', dt.time(9, 00), step=3600)
        t_end = st.time_input('To', dt.time(10, 00), step=3600)

        check_rooms = st.form_submit_button("Check available rooms")

        if check_rooms: 
          
          # filtering the available spots to display for the room
          start = dt.datetime.combine(chosen_date, t_start).isoformat()
          end = dt.datetime.combine(chosen_date, t_end).isoformat()
          dat = df[df['roomno_place'].isin(zooms_places)]
          dat = dat[((dat['date_start_utc'] <= end) & 
                    (dat['date_end_utc'] >= start))]
          places = dat['roomno_place'].drop_duplicates().tolist()
          av_zoom_places = set(zooms_places)
          av_zoom_places = av_zoom_places.difference(places)
          av_zoom_places = list(zooms_places)
          av_zoom_places.sort()

          st.write("These places are available - select one with 'copy to clipboard':", av_zoom_places)

   with col2: 

      with st.form("book_zooms"):
    
        my_name = st.text_input("Name")
        roomno_place = st.text_input("Paste/enter your chosen place here:")

        # Every form must have a submit button.
        submitted = st.form_submit_button("Book place")
             
        if submitted:
                
            # modify and wrap data for storing in database
            roomno_place = roomno_place.replace('"', '')
            roomno = roomno_place.split("_")[0]
            place = roomno_place.split("_")[1]
            date_start = json.dumps(dt.datetime.combine(chosen_date, t_start).isoformat())
            date_end = json.dumps(dt.datetime.combine(chosen_date, t_end).isoformat())

            data = supabase.table("bookings").insert({"name":my_name,
                                                            "date_start":date_start,
                                                            "date_end":date_end,
                                                            "roomno_place": roomno_place,
                                                            "roomno": roomno,
                                                            "place": place,
                                                            }).execute()
            assert len(data.data) > 0

            # also write data into shadow-db
            data2 = supabase.table("bookings_shadow").insert({"name":my_name,
                                                            "date_start":date_start,
                                                            "date_end":date_end,
                                                            "roomno_place": roomno_place,
                                                            "roomno": roomno,
                                                            "place": place,
                                                            }).execute()
            assert len(data2.data) > 0

            st.write("Thanks for signing up!")
                
            # update the available database
            df = get_data('bookings')


with tab4: 
   
    st.header(""" Cancel your booking """)

    st.markdown("""
    If you want to cancel your booking: 
    
    1) Look up your entry in the table below on the bottom right :arrow_lower_right:  

    2) Submit the corresponding value from the **id** column to remove this entry from the database. 
    
    :warning: :red[This action **cannot** be undone! :warning:]

    """)
    
    
    # column display from here
    col1, col2 = st.columns([1,3])
   
    with col1: 
       
       with st.form("delete_rooms"):
          
          del_id = st.text_input("ID to delete")

          # Every form must have a submit button.
          del_submitted = st.form_submit_button("Delete record")

          if del_submitted:
            
            data = supabase.table("bookings").delete().eq("id", del_id).execute()
            
            assert len(data.data) > 0
            
            # update the available database
            df = get_data('bookings')

            st.write("Your booking was cancelled.")

    with col2:
       
       st.dataframe(df)

