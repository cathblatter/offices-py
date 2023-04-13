import streamlit as st
import pandas as pd
from supabase import create_client, Client
import json
import numpy as np
import datetime as dt
import streamlit as st
from plotnine import *

# Connect to Supabase
def init_connection():
    url = st.secrets["supabase_url"]
    key = st.secrets["supabase_key"]
    return create_client(url, key)

supabase = init_connection()

def run_query(tbl_name):
    return supabase.table(tbl_name).select("*").execute()


# Define the available rooms and time slots
rooms = ["Room A", "Room B", "Room C"]
time_slots = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"]

st.title("Room Booking System")
    
# Get the list of existing bookings
booking = run_query("room_bookings")
booking = pd.DataFrame(booking.data)
    
 # Define the form for booking a room
with st.form("book_room"):
    room = st.selectbox("Room", rooms)
    date = st.date_input("Date")
    start_time = st.selectbox("Start Time", time_slots)
    end_time = st.selectbox("End Time", time_slots)
    
    if start_time >= end_time:
        st.error("End time must be after start time.")
        
    if any([booking["room"] == room and booking["date"] == str(date) and 
            booking["start_time"] <= start_time and 
            booking["end_time"] > start_time for booking in booking]):
        st.error("This time slot is already booked.")
        st.stop()
        
    if any([booking["room"] == room and booking["date"] == str(date) and booking["start_time"] < end_time and booking["end_time"] >= end_time for booking in booking]):
        st.error("This time slot is already booked.")
        st.stop()
    
    else: 
        submitted = st.form_submit_button("Book Room")
    
    if submitted:
        data = supabase.table("room_bookings").insert({"room":room,
                                                    "date":date,
                                                    "start_time":start_time,
                                                    "end_time":end_time,
                                                    }).execute()
    assert len(data.data) > 0
    st.write("thanks for signing up!")
