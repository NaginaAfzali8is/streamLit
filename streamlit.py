import streamlit as st
import requests
import sqlite3
import time

# 🔑 API Credentials
API_KEY = "28191ede-bcfa-4a3f-9cdd-524bb8821bb0"
ASSISTANT_ID = "52868961-1ca8-4dcb-a332-92883f3dc713"
PHONE_ID = "e2f56326-0e92-4c78-a4c2-1402d1fe27f5"

# 🔗 API Endpoints
CALL_URL = "https://api.vapi.ai/call/phone"
CALL_STATUS_URL = "https://api.vapi.ai/call/{call_id}"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 📊 Database Setup
def init_db():
    conn = sqlite3.connect("call_history.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    email TEXT,
                    phone TEXT,
                    status TEXT,
                    summary TEXT,
                    recording_url TEXT
                 )''')
    conn.commit()
    conn.close()

# 📞 Initiate Call Function
def initiate_call(name, email, customer_number):
    call_data = {
        "assistantId": ASSISTANT_ID,
        "phoneNumberId": PHONE_ID,
        "customer": {"number": customer_number}
    }

    call_response = requests.post(CALL_URL, headers=HEADERS, json=call_data)

    if call_response.status_code == 201:
        return call_response.json().get("id")
    else:
        st.error(f"❌ Error: {call_response.json()}")
        return None

# ⏳ Check Call Status Function (Wait Until Completion)
# ⏳ Improved Check Call Status Function (Real-time Updates)
def check_status(call_id):
    status_url = CALL_STATUS_URL.format(call_id=call_id)

    st.write("⏳ Waiting for call to complete... (Checking every 5s)")

    for attempt in range(30):  # Check every 5s for up to 2.5 minutes
        call_status_response = requests.get(status_url, headers=HEADERS)

        if call_status_response.status_code == 200:
            call_summary = call_status_response.json()

            # 🔹 Print API response for debugging
            print(f"API Response ({attempt+1}):", call_summary)

            status = call_summary.get("status", "unknown")  # Get call status
            ended_reason = call_summary.get("endedReason", "Not Available")  # Get reason if ended
            recording_url = call_summary.get("recordingUrl", "Not Available")  # Get call recording
            summary = call_summary.get("analysis", {}).get("summary", "Not Available")  # ✅ Get summary correctly

            # ✅ If the call is completed, failed, or ended, return immediately
            if status in ["completed", "failed", "ended"]:
                st.success(f"✅ Call {status.capitalize()}! Reason: {ended_reason}")
                return {"status": status, "summary": summary, "recording_url": recording_url}

        else:
            st.warning(f"⚠️ Failed to fetch call status (Attempt {attempt+1})")

        time.sleep(5)  # 🔄 Reduce wait time to 5 seconds

    # 🔴 If still pending after 30 attempts, return as pending
    return {"status": "pending"}


# 🔍 Analyze Call Summary Using GPT (If Needed)
import google.generativeai as genai

# 🔑 Set up Gemini API Key
GEMINI_API_KEY = "AIzaSyCxBBQvYXoJHcPbdbn9gREpM95BhhBZEus"
genai.configure(api_key=GEMINI_API_KEY)

# 🔍 Function to Analyze Call Summary using Gemini
def analyze_summary(summary):
    try:
        model = genai.GenerativeModel("gemini-pro")  # Use Gemini Pro model

        prompt = f"""
        Analyze the following call summary and categorize it as one of these:
        - Positive
        - Negative
        - Follow-up
        - Wrong Number

        Summary:
        "{summary}"

        Return only the category.
        """

        response = model.generate_content(prompt)
        category = response.text.strip()  # Extract the category from the response

        return category

    except Exception as e:
        st.error(f"Error in Gemini Analysis: {e}")
        return "Follow-up"  # Default category if the API fails


# 📜 Fetch Call History
def get_call_history():
    conn = sqlite3.connect("call_history.db")
    c = conn.cursor()
    c.execute("SELECT * FROM calls ORDER BY id DESC")
    calls = c.fetchall()
    conn.close()
    return calls

# 🏠 Streamlit UI
st.set_page_config(page_title="AI Cold Calling Assistant", layout="wide")

st.title("📞 AI Cold Calling Assistant")
st.subheader("Automate your sales calls and manage your leads efficiently.")

# 🎙 User Input Form
with st.form("call_form"):
    name = st.text_input("Customer Name")
    email = st.text_input("Customer Email")
    phone = st.text_input("Customer Phone Number (Include country code)")

    submitted = st.form_submit_button("📞 Start Call")

    if submitted:
        if name and email and phone:
            call_id = initiate_call(name, email, phone)
            if call_id:
                st.success(f"✅ Call started! Call ID: {call_id}")

                # 🕒 Wait for Call to Finish & Get Summary
                call_result = check_status(call_id)

                if call_result["status"] != "pending":
                    summary = call_result["summary"]
                    recording_url = call_result["recording_url"]

                    # 🧠 Use GPT for Call Analysis
                    deal_status = analyze_summary(summary)

                    # 📌 Save to Database
                    conn = sqlite3.connect("call_history.db")
                    c = conn.cursor()
                    c.execute("INSERT INTO calls (name, email, phone, status, summary, recording_url) VALUES (?, ?, ?, ?, ?, ?)",
                              (name, email, phone, deal_status, summary, recording_url))
                    conn.commit()
                    conn.close()

                    # 📝 Show Final Call Details
                    st.write(f"📄 **Call Summary:** {summary}")
                    st.write(f"🔗 **Recording:** [Listen here]({recording_url})")
                    st.write(f"💼 **Deal Status:** {deal_status}")

        else:
            st.warning("⚠️ Please fill all fields before starting a call.")

# 📊 Call History
st.subheader("📜 Call History")

history_data = get_call_history()
if history_data:
    import pandas as pd
    df = pd.DataFrame(history_data, columns=["ID", "Name", "Email", "Phone", "Status", "Summary", "Recording URL"])
    st.dataframe(df)
else:
    st.info("No call history found.")
