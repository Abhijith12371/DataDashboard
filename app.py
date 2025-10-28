import re
import io
import pandas as pd
import streamlit as st
import plotly.express as px
from textblob import TextBlob
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# ---------------------------------------------------------------
# 1️⃣ CONFIGURATION
# ---------------------------------------------------------------
st.set_page_config(page_title="WhatsApp Chat Dashboard", layout="wide")

st.title("💬 WhatsApp Chat Dashboard")
st.markdown("### 📊 Analyze group chats, messages, and trends — interactively!")

# ---------------------------------------------------------------
# 2️⃣ UPLOAD CHAT FILE
# ---------------------------------------------------------------
uploaded_file = st.sidebar.file_uploader("📁 Upload your WhatsApp chat (.txt)", type=["txt"])

if uploaded_file is not None:
    chat_data = uploaded_file.readlines()
else:
    st.info("⬆️ Please upload your exported WhatsApp chat file to start.")
    st.stop()

# ---------------------------------------------------------------
# 3️⃣ PARSE CHAT DATA
# ---------------------------------------------------------------
pattern = re.compile(r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}\s?[ap]m)\s*-\s*([^:]+):\s*(.*)$")

messages = []
for line in chat_data:
    try:
        line = line.decode("utf-8").strip()
    except:
        line = line.strip()
    match = pattern.match(line)
    if match:
        date, time, sender, message = match.groups()
        messages.append([date, time, sender, message])
    elif messages:
        messages[-1][3] += " " + line.strip()

df = pd.DataFrame(messages, columns=["date", "time", "sender", "message"])
df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)
df.dropna(subset=["date"], inplace=True)

# ---------------------------------------------------------------
# 4️⃣ SIDEBAR FILTERS
# ---------------------------------------------------------------
users = sorted(df["sender"].unique())
selected_user = st.sidebar.selectbox("👤 Select User (or 'Overall')", ["Overall"] + users)
start_date, end_date = st.sidebar.date_input(
    "📅 Select Date Range", [df["date"].min(), df["date"].max()]
)

# Word filter input
search_word = st.sidebar.text_input("🔍 Filter by Word/Phrase", "").strip()

analysis_choice = st.sidebar.selectbox(
    "🧩 Extra Analysis Feature", ["None", "Night Study / Stay", "Word Analysis"]
)

# ---------------------------------------------------------------
# 5️⃣ OVERALL DASHBOARD
# ---------------------------------------------------------------
if analysis_choice == "None":

    # Apply word filter if provided
    if search_word:
        filtered_df = df[
            (df["date"].dt.date >= start_date) & 
            (df["date"].dt.date <= end_date) &
            (df["message"].str.contains(search_word, case=False, na=False))
        ]
        st.sidebar.info(f"📊 Showing messages containing: '{search_word}'")
    else:
        filtered_df = df[(df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)]

    if selected_user == "Overall":
        st.subheader("🌍 Group Overview")

        total_messages = len(filtered_df)
        total_users = filtered_df["sender"].nunique()
        total_media = filtered_df["message"].str.contains("<Media omitted>", na=False).sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Messages", total_messages)
        c2.metric("Total Participants", total_users)
        c3.metric("Media Shared", total_media)

        # Messages per day
        daily = filtered_df.groupby("date").size().reset_index(name="count")
        if not daily.empty:
            fig1 = px.line(daily, x="date", y="count", title="Messages Per Day")
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("No data available for the selected filters.")

        # Top senders
        if not filtered_df.empty:
            top_senders = (
                filtered_df["sender"].value_counts().reset_index().rename(columns={"index": "sender", "sender": "count"})
            )
            top_senders.columns = ["sender", "message_count"]
            fig2 = px.bar(
                top_senders.head(10),
                x="sender",
                y="message_count",
                title="Top Senders",
                text="message_count"
            )
            fig2.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig2, use_container_width=True)

            # Word cloud
            all_text = " ".join(filtered_df["message"].dropna())
            if all_text.strip():
                wc = WordCloud(width=800, height=400, background_color="white").generate(all_text)
                st.subheader("☁️ Most Common Words")
                fig, ax = plt.subplots()
                ax.imshow(wc, interpolation="bilinear")
                ax.axis("off")
                st.pyplot(fig)
        else:
            st.info("No data available for the selected filters.")

    # ---------------------------------------------------------------
    # 6️⃣ USER-SPECIFIC DASHBOARD
    # ---------------------------------------------------------------
    else:
        st.subheader(f"👤 User Analysis: {selected_user}")

        user_df = filtered_df[filtered_df["sender"] == selected_user]
        msg_count = len(user_df)
        first_date = user_df["date"].min().strftime("%d %b %Y") if not user_df.empty else "-"
        last_date = user_df["date"].max().strftime("%d %b %Y") if not user_df.empty else "-"

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Messages", msg_count)
        c2.metric("First Message", first_date)
        c3.metric("Last Message", last_date)

        if not user_df.empty:
            # Message trend
            trend = user_df.groupby("date").size().reset_index(name="count")
            fig = px.area(trend, x="date", y="count", title="Messages Over Time")
            st.plotly_chart(fig, use_container_width=True)

            # Word cloud
            all_text = " ".join(user_df["message"].dropna())
            if all_text.strip():
                wc = WordCloud(width=800, height=400, background_color="white").generate(all_text)
                st.subheader("🗣️ Frequent Words Used")
                fig, ax = plt.subplots()
                ax.imshow(wc, interpolation="bilinear")
                ax.axis("off")
                st.pyplot(fig)

            # Sentiment
            user_df["sentiment"] = user_df["message"].apply(lambda x: TextBlob(x).sentiment.polarity)
            sentiment_counts = (
                user_df["sentiment"]
                .apply(lambda x: "Positive" if x > 0 else "Negative" if x < 0 else "Neutral")
                .value_counts()
                .reset_index()
            )
            sentiment_counts.columns = ["Sentiment", "Count"]
            fig_sent = px.pie(sentiment_counts, values="Count", names="Sentiment", title="Sentiment Distribution")
            st.plotly_chart(fig_sent, use_container_width=True)

            st.subheader("📜 Message Log")
            st.dataframe(user_df[["date", "time", "message"]], height=300)
        else:
            st.info(f"No messages found for {selected_user} with the current filters.")

# ---------------------------------------------------------------
# 7️⃣ EXTRA FEATURE: NIGHT STUDY / STAY
# ---------------------------------------------------------------
elif analysis_choice == "Night Study / Stay":
    st.subheader("🌙 Night Study / Night Stay Analysis")
    st.markdown(
        "This section identifies all messages mentioning **'night study'** or **'night stay'**, "
        "shows who said them, and when."
    )

    # Filter messages containing those phrases
    night_study_df = df[df["message"].str.contains(r"\bnight study\b", case=False, na=False)]
    night_stay_df = df[df["message"].str.contains(r"\bnight stay\b", case=False, na=False)]

    study_users = night_study_df["sender"].nunique()
    stay_users = night_stay_df["sender"].nunique()

    c1, c2 = st.columns(2)
    c1.metric("People who said 'night study'", study_users)
    c2.metric("People who said 'night stay'", stay_users)

    # Bar chart comparing mentions
    compare_df = pd.DataFrame({
        "Phrase": ["Night Study", "Night Stay"],
        "Mentions": [len(night_study_df), len(night_stay_df)]
    })
    fig_compare = px.bar(compare_df, x="Phrase", y="Mentions", color="Phrase", title="Comparison of Mentions")
    st.plotly_chart(fig_compare, use_container_width=True)

    st.markdown("### 📘 Messages containing 'night study'")
    if not night_study_df.empty:
        st.dataframe(night_study_df[["date", "time", "sender", "message"]].reset_index(drop=True), height=300)
    else:
        st.info("No messages found containing 'night study'.")

    st.markdown("### 📗 Messages containing 'night stay'")
    if not night_stay_df.empty:
        st.dataframe(night_stay_df[["date", "time", "sender", "message"]].reset_index(drop=True), height=300)
    else:
        st.info("No messages found containing 'night stay'.")

    # Downloadable Excel report
    output_excel = io.BytesIO()
    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
        night_study_df.to_excel(writer, index=False, sheet_name=f"Night Study ({study_users})")
        night_stay_df.to_excel(writer, index=False, sheet_name=f"Night Stay ({stay_users})")
    output_excel.seek(0)

    st.download_button(
        "⬇️ Download Night Study/Stay Excel Report",
        data=output_excel,
        file_name="Night_Study_Stay_Analysis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ---------------------------------------------------------------
# 8️⃣ EXTRA FEATURE: WORD ANALYSIS
# ---------------------------------------------------------------
elif analysis_choice == "Word Analysis":
    st.subheader("🔍 Word Analysis")
    st.markdown(
        "This section analyzes all messages containing your **specific word or phrase**, "
        "shows who said them, when, and provides detailed statistics."
    )
    
    if search_word:
        # Filter messages containing the word
        word_filtered_df = df[df["message"].str.contains(search_word, case=False, na=False)]
        
        # Apply date filter
        word_filtered_df = word_filtered_df[
            (word_filtered_df["date"].dt.date >= start_date) & 
            (word_filtered_df["date"].dt.date <= end_date)
        ]
        
        if selected_user != "Overall":
            word_filtered_df = word_filtered_df[word_filtered_df["sender"] == selected_user]
        
        if not word_filtered_df.empty:
            # Key Metrics
            total_mentions = len(word_filtered_df)
            unique_users = word_filtered_df["sender"].nunique()
            first_mention = word_filtered_df["date"].min().strftime("%d %b %Y")
            last_mention = word_filtered_df["date"].max().strftime("%d %b %Y")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Mentions", total_mentions)
            c2.metric("Unique Users", unique_users)
            c3.metric("First Mention", first_mention)
            c4.metric("Last Mention", last_mention)
            
            # Charts
            col1, col2 = st.columns(2)
            
            with col1:
                # Timeline of mentions
                timeline = word_filtered_df.groupby("date").size().reset_index(name="count")
                fig_timeline = px.line(timeline, x="date", y="count", 
                                     title=f"Timeline of '{search_word}' Mentions")
                st.plotly_chart(fig_timeline, use_container_width=True)
            
            with col2:
                # Top users mentioning the word
                top_mentions = word_filtered_df["sender"].value_counts().reset_index()
                top_mentions.columns = ["sender", "count"]
                fig_mentions = px.bar(top_mentions, x="sender", y="count", 
                                    title=f"Who mentioned '{search_word}' the most")
                st.plotly_chart(fig_mentions, use_container_width=True)
        else:
            st.info(f"No messages found containing '{search_word}' with the current filters.")
    
    else:
        st.info("💡 Please enter a word or phrase in the sidebar search box to see the analysis.")
    
    # Show actual messages - MOVED OUTSIDE THE if not word_filtered_df.empty CONDITION
    if search_word:
        st.markdown(f"### 📝 Messages containing '{search_word}'")
        
        if not word_filtered_df.empty:
            # Display the dataframe with all messages
            display_df = word_filtered_df[["date", "time", "sender", "message"]].reset_index(drop=True)
            st.dataframe(display_df, height=400, use_container_width=True)
            
            # Downloadable Excel report
            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
                word_filtered_df.to_excel(writer, index=False, sheet_name=f"Word Analysis ({unique_users})")
                
                # Add summary sheet
                summary_data = {
                    'Metric': ['Search Word', 'Total Mentions', 'Unique Users', 'Date Range', 
                             'First Mention', 'Last Mention'],
                    'Value': [search_word, total_mentions, unique_users, 
                             f"{start_date} to {end_date}", first_mention, last_mention]
                }
                pd.DataFrame(summary_data).to_excel(writer, index=False, sheet_name="Summary")
                
            output_excel.seek(0)

            st.download_button(
                f"⬇️ Download '{search_word}' Analysis Excel Report",
                data=output_excel,
                file_name=f"Word_Analysis_{search_word.replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info(f"No messages found containing '{search_word}' to display.")

# ---------------------------------------------------------------
# 9️⃣ FOOTER
# ---------------------------------------------------------------
st.markdown("---")
st.caption("📊 Built with ❤️ using Streamlit + Plotly + TextBlob")