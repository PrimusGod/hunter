import streamlit as st
import pandas as pd
import requests
from ratelimit import limits, sleep_and_retry

# --- Configuration & Rate Limiting ---
CALLS = 50
PERIOD = 60

@sleep_and_retry
@limits(calls=CALLS, period=PERIOD)
def fetch_google_data(query, api_key, cse_id):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {'q': query, 'key': api_key, 'cx': cse_id}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        items = resp.json().get('items', [])
        return [{'Source': 'Google', 'Title': i['title'], 'URL': i['link'], 'Snippet': i['snippet']} for i in items]
    except Exception as e:
        st.error(f"Search failed: {e}")
        return []

# --- Streamlit UI ---
st.set_page_config(page_title="OpenSource Intel Tool", layout="wide")
st.title("🔍 Modular OSINT Searcher")
st.markdown("Enter a keyword to query public APIs safely and legally.")

# Sidebar for API Keys (Or use Streamlit Secrets in deployment)
with st.sidebar:
    st.header("Settings")
    google_key = st.text_input("Google API Key", type="password")
    google_cx = st.text_input("Search Engine ID (CX)")

query = st.text_input("Search Query", placeholder="e.g. 'username' or 'company name'")

if st.button("Run Search"):
    if not google_key or not google_cx:
        st.warning("Please provide API credentials in the sidebar.")
    elif query:
        with st.spinner('Searching...'):
            results = fetch_google_data(query, google_key, google_cx)
            
            if results:
                df = pd.DataFrame(results)
                st.success(f"Found {len(results)} results!")
                
                # Display Results
                st.dataframe(df, use_container_width=True)
                
                # Export Options
                json_data = df.to_json(orient='records')
                st.download_button(
                    label="Download Report (JSON)",
                    data=json_data,
                    file_name=f"osint_{query}.json",
                    mime="application/json"
                )
            else:
                st.info("No public data found for that query.")

