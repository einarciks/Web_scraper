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
            min_cap = st.selectbox("Minimum Engine Capacity", options=[0.0, 0.1, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 3.0, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 4.0, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 5.0, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 6.0, 6.1, 6.2, 6.3, 6.4, 6.6, 6.8, 7.0, 7.3])
        with col8:
            max_cap = st.selectbox("Maximum Engine Capacity", options=[0.0, 0.1, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 3.0, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 4.0, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 5.0, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 6.0, 6.1, 6.2, 6.3, 6.4, 6.6, 6.8, 7.0, 7.3])

        col9, col10 = st.columns(2)
        with col9:
            min_mileage = st.number_input("Minimum Mileage", min_value=0, value=None, step=1000)
        with col10:
            max_mileage = st.number_input("Maximum Mileage", min_value=0, value=None, step=1000)

        col11, col12 = st.columns(2)
        with col11:
            gearbox = st.multiselect("Gearbox Type", options=["Automatic", "Manual"])
        with col12:
            body_type = st.multiselect("Body Type", options=["Sedan", "Hatchback", "Jeep", "Coupe", "Cabriolet", "Universal", "Minibus", "Miniven", "Pickup"])
        col13, _ = st.columns(2)
        with col13:
            color = st.multiselect("Color", options=["Black", "White", "Grey", "Blue", "Red", "Green", "Yellow", "Brown", "Dark red", "Ligh blue", "Orange", "Purple", "Silver"])
        submit = st.form_submit_button("Search listings")
    if submit:
        with st.spinner("Finding cars..."):
            database = get_cars(marka.strip().lower(), modelis.strip().lower(), min_year, max_year, min_price, max_price, min_cap, max_cap, min_mileage, max_mileage, gearbox, body_type, color)

        st.info(f"Found {len(database)} cars for {marka.upper()} {modelis.upper()}")

        if len(database) > 0:
            for car in database:
                st.subheader(car.get("title", "No Title"))
                st.write(f"**id:** {car.get('id', 'N/A')} | "
                        f"**Year:** {car.get('year', 'N/A')} | "
                        f"**Engine:** {car.get('engine', 'N/A')} | "
                        f"**Mileage:** {car.get('mileage', 'N/A')} | "
                        f"**Price:** {car.get('price', 'N/A')} | "
                        f" **Color:** {car.get('color', 'N/A')} | "
                        f" **Body Type:** {car.get('body_type', 'N/A')} | "
                        f" **Gearbox:** {car.get('gearbox', 'N/A')} | "
                        f" **Inspection:** {car.get('inspection', 'N/A')}")
                
                
                st.markdown(f"[View listing on SS.lv]({car.get('link', '#')})")
                images = car.get("images", [])
                img_url = car.get("image", "")
                if images:
                    cols = st.columns(min(len(images), 5))
                    for i, img_url in enumerate(images[:5]):
                        if img_url.startswith("http"):
                            cols[i].image(img_url, width=500)
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