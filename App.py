import streamlit as st
from webscaper import get_cars

def main():
    st.set_page_config(
            page_title="Car Search App",
            page_icon="🚗",
        )
    st.title("🚗 Car Search App – SS.lv meklētājs")

    with st.form("car_search_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            marka = st.text_input("Car Make (e.g. BMW, Audi)")
        with col2:
            modelis = st.text_input("Model (e.g. X5, A4)")
    
        submit = st.form_submit_button("🔍 Search listings")
    if submit:
        with st.spinner("Finding cars..."):
            database = get_cars(marka.strip().lower(), modelis.strip().lower())

        st.info(f"Found {len(database)} cars for {marka.upper()} {modelis.upper()}")

        if len(database) > 0:
            for car in database:
                st.subheader(car.get("title", "No Title"))
                st.write(f"**Year:** {car.get('year', 'N/A')} | "
                        f"**Engine:** {car.get('engine', 'N/A')} | "
                        f"**Mileage:** {car.get('mileage', 'N/A')} | "
                        f"**Price:** {car.get('price', 'N/A')} | "
                        f" **id:** {car.get('id', 'N/A')} | ")  
                
                st.markdown(f"[🔗 View listing on SS.lv]({car.get('link', '#')})")
                img_url = car.get("image", "")
                if img_url and img_url.startswith("http"):
                    st.image(car["image"], width=100)
                else:
                    st.caption("🚫 Image not available")
                st.divider()
        else:
            st.info("No cars found with the given parameters.")


        # Poga, lai notīrītu rezultātus un sāktu no jauna
        if st.button("🗑️ Delete results"):
            st.session_state.clear()
            st.cache_data.clear()
            st.rerun()
            



if __name__ == "__main__":
    main()