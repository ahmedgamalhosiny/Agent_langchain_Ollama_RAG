from langchain_ollama.llms import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from vector import retriever
from order_tool import send_order_email, is_order_intent

model = OllamaLLM(model="llama3.2")

# Normal RAG template
rag_template = """
You are an expert in answering questions about a pizza restaurant

Here are some relevant reviews: {reviews}

Here is the question to answer: {question}
"""
rag_prompt = ChatPromptTemplate.from_template(rag_template)
rag_chain = rag_prompt | model

# Order collection template
order_template = """
You are a helpful restaurant order assistant. The user wants to order food.
Current conversation:
{conversation}

Guide them to provide:
1. What items they want (with quantities)
2. Their name
3. Phone number
4. Delivery address or "Pickup"

Be friendly and ask one question at a time. If you have all info, say "READY_TO_SEND".
"""
order_prompt = ChatPromptTemplate.from_template(order_template)
order_chain = order_prompt | model

def collect_order_details():
    """Interactive order collection"""
    conversation = []
    order_data = {}
    
    print("\n🍕 Starting Order Mode")
    print("I'll help you place an order. Type 'cancel' anytime to exit.\n")
    
    # Get items
    items = input("What would you like to order? (e.g., '2 Margherita, 1 Garlic Bread'): ")
    if items.lower() == 'cancel':
        return None
    order_data['items'] = items
    
    # Get name
    name = input("Your name: ")
    if name.lower() == 'cancel':
        return None
    order_data['name'] = name
    
    # Get phone
    phone = input("Phone number: ")
    if phone.lower() == 'cancel':
        return None
    order_data['phone'] = phone
    
    # Get address
    address = input("Delivery address (or type 'Pickup'): ")
    if address.lower() == 'cancel':
        return None
    order_data['address'] = address
    
    # Notes
    notes = input("Any special instructions? (allergies, extra cheese, etc.) [Press Enter if none]: ")
    order_data['notes'] = notes
    
    # Confirm
    print(f"\n--- Order Summary ---")
    print(f"Items: {order_data['items']}")
    print(f"Name: {order_data['name']}")
    print(f"Phone: {order_data['phone']}")
    print(f"Address: {order_data['address']}")
    print(f"Notes: {order_data['notes']}")
    
    confirm = input("\nSend this order? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Order cancelled.")
        return None
    
    return order_data

print("Restaurant Review & Order System")
print("Commands: 'q' to quit")
print("-" * 50)

while True:
    print("\n-------------------------------")
    question = input("Ask your question (q to quit): ")
    
    if question == "q":
        break
    
    # Check if it's an order intent
    if is_order_intent(question):
        order_data = collect_order_details()
        if order_data:
            result = send_order_email(
                customer_name=order_data['name'],
                phone=order_data['phone'],
                address=order_data['address'],
                items=order_data['items'],
                notes=order_data['notes']
            )
            print(result)
        continue
    
    # Normal RAG flow
    reviews = retriever.invoke(question)
    result = rag_chain.invoke({"reviews": reviews, "question": question})
    print(result)