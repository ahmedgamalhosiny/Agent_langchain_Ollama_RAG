import streamlit as st
import pandas as pd
from langchain_ollama.llms import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from vector import retriever, df
from order_tool import send_order_email, is_order_intent
import altair as alt
from datetime import datetime
import base64
import os

# Page configuration
st.set_page_config(
    page_title="🍕 Pizza Restaurant Assistant",
    page_icon="🍕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load and encode background image
@st.cache_data
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

bg_image = get_base64_image("image.jpg")

# Build CSS with background image
css_content = "<style>"

# Add background image if available
if bg_image:
    css_content += f"""
    .stApp {{
        background-image: linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)), url("data:image/jpeg;base64,{bg_image}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    """

# Add rest of the styles
css_content += """
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.98);
        backdrop-filter: blur(10px);
    }
    
    /* Message styling */
    .user-message {
        background-color: rgba(227, 242, 253, 1);
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #2196f3;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }
    
    .assistant-message {
        background-color: rgba(255, 255, 255, 1);
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #4caf50;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }
    
    /* Order summary box */
    .order-summary {
        background-color: rgba(255, 243, 205, 1);
        border: 2px solid #ffc107;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }
    
    /* Success message */
    .success-box {
        background-color: rgba(212, 237, 218, 1);
        border: 2px solid #28a745;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }
    
    /* Make content more readable */
    .stMarkdown, .stText {
        color: #1a1a1a;
    }
    
    /* Main titles and headers */
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8);
    }
    
    /* Captions */
    .css-16huue1, [data-testid="stCaptionContainer"] {
        color: #ffffff !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8);
    }
    
    /* Card backgrounds */
    [data-testid="stMetricValue"] {
        background-color: rgba(255, 255, 255, 0.95);
        padding: 0.5rem;
        border-radius: 0.3rem;
    }
    
    /* Input form styling */
    [data-testid="stForm"] {
        background-color: rgba(255, 255, 255, 0.95);
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }
    
    /* Make dividers visible */
    hr {
        border-color: rgba(255, 255, 255, 0.3) !important;
    }
</style>
"""

st.markdown(css_content, unsafe_allow_html=True)

# Initialize the model
@st.cache_resource
def get_model():
    return OllamaLLM(model="llama3.2")

model = get_model()

# Prompt templates
rag_template = """
You are a friendly pizza restaurant assistant. You can answer questions about the restaurant based on customer reviews.

Here are some relevant reviews: {reviews}

Here is the customer's question: {question}

Provide a helpful, friendly answer based on the reviews. Keep it conversational and concise.
"""
rag_prompt = ChatPromptTemplate.from_template(rag_template)
rag_chain = rag_prompt | model

order_collection_template = """
You are a friendly restaurant order assistant. You're helping collect order details.

Conversation so far:
{conversation}

Current order status:
- Items ordered: {items}
- Customer name: {name}
- Phone number: {phone}
- Delivery address: {address}

Customer's latest message: {user_message}

If the customer is providing order items (food items), acknowledge them warmly and ask what else they'd like to add, or if that's all.
If the customer confirms the order is complete, ask for their name (if not provided).
If you have items and name, ask for phone number.
If you have items, name, and phone, ask for delivery address or if they want pickup.
If you have all information, say "COMPLETE" and summarize the order.

Be natural and friendly. Don't repeat information you already have.
"""
order_collection_prompt = ChatPromptTemplate.from_template(order_collection_template)
order_collection_chain = order_collection_prompt | model

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "ordering_mode" not in st.session_state:
    st.session_state.ordering_mode = False  # True when collecting order
    
if "order_data" not in st.session_state:
    st.session_state.order_data = {
        "items": "",
        "name": "",
        "phone": "",
        "address": "",
        "notes": ""
    }
    
if "order_confirmed" not in st.session_state:
    st.session_state.order_confirmed = False

if "show_confirmation" not in st.session_state:
    st.session_state.show_confirmation = False

# Sidebar - Analytics & Info
with st.sidebar:
    st.title("📊 Restaurant Analytics")
    
    # Overall statistics
    st.subheader("Overall Stats")
    avg_rating = df["Rating"].mean()
    total_reviews = len(df)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Average Rating", f"{avg_rating:.1f} ⭐")
    with col2:
        st.metric("Total Reviews", total_reviews)
    
    # Rating distribution chart
    st.subheader("Rating Distribution")
    rating_counts = df["Rating"].value_counts().sort_index()
    rating_df = pd.DataFrame({
        "Rating": rating_counts.index,
        "Count": rating_counts.values
    })
    
    chart = alt.Chart(rating_df).mark_bar(color="#ff6b6b").encode(
        x=alt.X("Rating:O", title="Rating"),
        y=alt.Y("Count:Q", title="Number of Reviews"),
        tooltip=["Rating", "Count"]
    ).properties(height=200)
    
    st.altair_chart(chart, use_container_width=True)
    
    # Recent reviews
    st.subheader("Recent Reviews")
    df_sorted = df.copy()
    df_sorted["Date"] = pd.to_datetime(df_sorted["Date"])
    recent = df_sorted.nlargest(3, "Date")[["Title", "Rating", "Date"]]
    for _, row in recent.iterrows():
        stars = "⭐" * int(row["Rating"])
        st.markdown(f"**{row['Title']}** {stars}")
        st.caption(f"{row['Date'].strftime('%Y-%m-%d')}")
        st.markdown("---")
    
    # Clear chat button
    if st.button("🗑️ Start New Chat", key="clear_btn"):
        st.session_state.messages = []
        st.session_state.ordering_mode = False
        st.session_state.order_data = {
            "items": "",
            "name": "",
            "phone": "",
            "address": "",
            "notes": ""
        }
        st.session_state.order_confirmed = False
        st.session_state.show_confirmation = False
        st.experimental_rerun()

# Main header
st.title("🍕 Pizza Restaurant Assistant")
if st.session_state.ordering_mode:
    st.caption("🛒 Taking your order...")
    
    # Show progress indicator
    st.markdown("### Order Progress:")
    progress_items = {
        "📦 Items": st.session_state.order_data["items"],
        "👤 Name": st.session_state.order_data["name"],
        "📞 Phone": st.session_state.order_data["phone"],
        "📍 Address": st.session_state.order_data["address"]
    }
    
    cols = st.columns(4)
    for idx, (label, value) in enumerate(progress_items.items()):
        with cols[idx]:
            if value:
                st.success(f"✅ {label}")
            else:
                st.info(f"⏳ {label}")
    st.markdown("---")
else:
    st.caption("Ask me anything about our restaurant or place an order!")

# Welcome message
if len(st.session_state.messages) == 0:
    welcome = """
👋 ***Welcome to our Pizza Restaurant!***

I'm your virtual assistant. I can help you with:

- 💬 **Answer questions** about our restaurant, menu, and customer reviews
- 🛒 **Take your order** - just tell me what you'd like!

**Popular questions:**
- "What do customers say about your pizza?"
- "Do you have gluten-free options?"
- "What are your most popular items?"

**To order, just say:**
- "I'd like to order..."
- "I want to place an order"
- "Can I order 2 Margherita pizzas?"

How can I help you today?
    """
    
    st.markdown(f'<div class="assistant-message">{welcome}</div>', unsafe_allow_html=True)
    st.session_state.messages.append({"role": "assistant", "content": welcome})

# Display chat messages
for message in st.session_state.messages[1:]:  # Skip welcome message
    if message["role"] == "user":
        st.markdown(f'<div class="user-message"><b>You:</b><br>{message["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="assistant-message"><b>Assistant:</b><br>{message["content"]}</div>', unsafe_allow_html=True)

# Show order summary if ready for confirmation
if st.session_state.show_confirmation and not st.session_state.order_confirmed:
    st.markdown("---")
    st.markdown("### 📋 Order Summary")
    st.markdown(f"""
    <div class="order-summary">
    <b>Items:</b> {st.session_state.order_data['items']}<br>
    <b>Name:</b> {st.session_state.order_data['name']}<br>
    <b>Phone:</b> {st.session_state.order_data['phone']}<br>
    <b>Address:</b> {st.session_state.order_data['address']}<br>
    <b>Notes:</b> {st.session_state.order_data['notes'] or 'None'}
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Confirm & Send Order", key="confirm_order"):
            # Send the order
            result = send_order_email(
                customer_name=st.session_state.order_data['name'],
                phone=st.session_state.order_data['phone'],
                address=st.session_state.order_data['address'],
                items=st.session_state.order_data['items'],
                notes=st.session_state.order_data['notes']
            )
            
            st.session_state.order_confirmed = True
            st.session_state.show_confirmation = False
            st.session_state.ordering_mode = False
            
            response = f"🎉 **Order Confirmed!**\n\n{result}\n\nThank you for your order! We'll contact you shortly."
            st.markdown(f'<div class="success-box">{response}</div>', unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            # Reset order data
            st.session_state.order_data = {
                "items": "",
                "name": "",
                "phone": "",
                "address": "",
                "notes": ""
            }
            
    with col2:
        if st.button("❌ Cancel Order", key="cancel_order"):
            st.session_state.ordering_mode = False
            st.session_state.show_confirmation = False
            st.session_state.order_data = {
                "items": "",
                "name": "",
                "phone": "",
                "address": "",
                "notes": ""
            }
            response = "Order cancelled. Feel free to ask me anything or start a new order!"
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.experimental_rerun()

# Input form
st.markdown("---")
with st.form(key="chat_form", clear_on_submit=True):
    user_input = st.text_input("Type your message here:", key="input_field")
    submit_button = st.form_submit_button("Send 📤")

if submit_button and user_input:
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Generate response
    with st.spinner("Thinking..."):
        if not st.session_state.ordering_mode:
            # Check if this is an order request
            if is_order_intent(user_input):
                # Start ordering mode
                st.session_state.ordering_mode = True
                
                # Try to extract items from the message
                user_msg_lower = user_input.lower()
                if any(word in user_msg_lower for word in ["pizza", "margherita", "pepperoni", "cheese", "garlic", "bread"]):
                    st.session_state.order_data["items"] = user_input
                    response = f"Great! I've noted: **{user_input}**\n\nWould you like to add anything else, or is that all?"
                else:
                    response = "Perfect! I'd be happy to take your order. What would you like to order?"
                
                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                # Regular Q&A mode
                # Retrieve relevant reviews
                reviews = retriever.invoke(user_input)
                reviews_text = "\n\n".join([
                    f"Review {i+1} (Rating: {doc.metadata['rating']}/5):\n{doc.page_content}"
                    for i, doc in enumerate(reviews)
                ])
                
                # Generate response
                response = rag_chain.invoke({
                    "reviews": reviews_text,
                    "question": user_input
                })
                
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        else:
            # We're in ordering mode - collect details
            user_msg_lower = user_input.lower()
            
            # Build conversation history for context
            conversation = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in st.session_state.messages[-6:]  # Last 6 messages for context
            ])
            
            # Smart extraction based on what we're missing
            if not st.session_state.order_data["items"]:
                # Looking for items
                st.session_state.order_data["items"] = user_input
                response = f"Got it! **{user_input}**\n\nAnything else you'd like to add?"
                
            elif "no" in user_msg_lower or "that's all" in user_msg_lower or "that's it" in user_msg_lower or "nothing else" in user_msg_lower:
                # Customer is done adding items, ask for name
                if not st.session_state.order_data["name"]:
                    response = "Perfect! May I have your name please?"
                elif not st.session_state.order_data["phone"]:
                    response = "Great! What's your phone number?"
                elif not st.session_state.order_data["address"]:
                    response = "And where would you like this delivered? (Or type 'Pickup' if you'll collect it)"
                else:
                    # All info collected!
                    st.session_state.show_confirmation = True
                    response = "Perfect! I have all the information. Please review your order above and confirm."
                    
            elif st.session_state.order_data["items"] and not st.session_state.order_data["name"]:
                # Check if they're adding more items or providing name
                if any(word in user_msg_lower for word in ["pizza", "margherita", "pepperoni", "cheese", "garlic", "bread", "add", "also"]):
                    # Adding more items
                    st.session_state.order_data["items"] += f", {user_input}"
                    response = f"Added **{user_input}**! Anything else?"
                else:
                    # This is likely their name
                    st.session_state.order_data["name"] = user_input
                    response = f"Thank you, {user_input}! What's your phone number?"
                    
            elif not st.session_state.order_data["phone"]:
                # Looking for phone number
                st.session_state.order_data["phone"] = user_input
                response = "Got it! Where would you like this delivered? (Or type 'Pickup')"
                
            elif not st.session_state.order_data["address"]:
                # Looking for address
                st.session_state.order_data["address"] = user_input
                
                # Ask if they have any special notes
                response = "Perfect! Any special instructions or notes? (allergies, extra cheese, etc.) You can type 'No' if none."
                
            else:
                # Collecting notes or finishing up
                if "no" not in user_msg_lower:
                    st.session_state.order_data["notes"] = user_input
                
                # All info collected!
                st.session_state.show_confirmation = True
                response = "Excellent! I have all the details. Please review your order above and confirm when ready."
            
            st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Rerun to update the display
    st.experimental_rerun()
