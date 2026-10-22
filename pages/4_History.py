import streamlit as st
from agent.scraper import TravelSiteScraper

st.set_page_config(page_title="Booking History", layout="wide")
st.title("Travel Site Booking History")

scraper = TravelSiteScraper()
history = scraper.check_booking_history()

if history:
    st.caption(f"{len(history)} confirmed booking(s)")
    header = st.columns([2, 2, 1, 1, 1, 1])
    for column, label in zip(
        header, ["PNR", "Route", "Type", "Departure", "Arrival", "Status"]
    ):
        column.markdown(f"**{label}**")
    for booking in history:
        row = st.columns([2, 2, 1, 1, 1, 1])
        row[0].write(booking["pnr"])
        row[1].write(booking["route"])
        row[2].write(booking["type"].title())
        row[3].write(booking["departure"])
        row[4].write(booking["arrival"])
        row[5].write(booking["status"])
else:
    st.info("No bookings found on the mock site.")