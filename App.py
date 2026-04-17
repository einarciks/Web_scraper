import streamlit as st
from webscaper import get_cars

def main():
    st.set_page_config(
            page_title="Car Search App",
            page_icon="🚗",
        )
    st.title("Car Search App – SS.lv meklētājs")

    with st.form("car_search_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            marka = st.text_input("Car Make (e.g. BMW, Audi)", key="make_input")
        with col2:
            modelis = st.text_input("Model (e.g. X5, A4)", key="model_input")
        
        st.write("Optional Filters:")
        
        col3, col4 = st.columns(2)
        with col3:
            min_year = st.number_input("Minimum Year", min_value=1900, max_value=2026, value=None, step=1)
        with col4:
            max_year = st.number_input("Maximum Year", min_value=1900, max_value=2026, value=None, step=1)
        
        col5, col6 = st.columns(2)

        with col5:
            min_price = st.number_input("Minimum Price", min_value=0, value=None, step=100)
        with col6:
            max_price = st.number_input("Maximum Price", min_value=0, value=None, step=100)

        col7, col8 = st.columns(2)
        with col7:
            min_cap = st.number_input("Minimum Engine Capacity", min_value=0.0, value=None, step=0.1)
        with col8:
            max_cap = st.number_input("Maximum Engine Capacity", min_value=0.0, value=None, step=0.1)

        col9, col10 = st.columns(2)
        with col9:
            min_mileage = st.number_input("Minimum Mileage", min_value=0, value=None, step=1000)
        with col10:
            max_mileage = st.number_input("Maximum Mileage", min_value=0, value=None, step=1000)
        submit = st.form_submit_button("Search listings")
    if submit:
        with st.spinner("Finding cars..."):
            database = get_cars(marka.strip().lower(), modelis.strip().lower(), min_year, max_year, min_price, max_price, min_cap, max_cap, min_mileage, max_mileage)

        st.info(f"Found {len(database)} cars for {marka.upper()} {modelis.upper()}")

        if len(database) > 0:
            for car in database:
                st.subheader(car.get("title", "No Title"))
                st.write(f"**Year:** {car.get('year', 'N/A')} | "
                        f"**Engine:** {car.get('engine', 'N/A')} | "
                        f"**Mileage:** {car.get('mileage', 'N/A')} | "
                        f"**Price:** {car.get('price', 'N/A')} | "
                        f" **id:** {car.get('id', 'N/A')} | ")  
                
                st.markdown(f"[View listing on SS.lv]({car.get('link', '#')})")
                img_url = car.get("image", "")
                if img_url and img_url.startswith("http"):
                    st.image(car["image"], width=100)
                else:
                    st.caption("Image not available")
                st.divider()
        else:
            st.info("No cars found with the given parameters.")


        if st.button("Delete results"):
            st.session_state.clear()
            st.cache_data.clear()
            st.rerun()
            



if __name__ == "__main__":
    main()