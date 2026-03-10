from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import RetrievalQA
import utilities

chat_history_store = {}

def create_rag_qa(vectorstore, query, session_id , company_email = None):
    # Create retriever from vectorstore
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})
   
    # Initialize LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # Define a prompt
    prompt = ChatPromptTemplate.from_template("""
    You are a Website Support Assistant for this website.
    You must answer user questions only using the information provided in the given context, which comes from the website’s crawled and scraped content stored as PDFs.

    Rules:
    - If the user greets, greet them back.
    - If the question is unclear, politely ask for clarification.
    - If the question is outside the provided context, politely state that you can only answer questions related to this website.
    - Do NOT use external knowledge, assumptions, or prior training.
    - Do NOT guess, infer, or hallucinate.
    - If the answer is not present in the context, respond exactly with:
      “We don't have the information currently, admin will gate back to you with the answer shortly.”
    - Keep answers clear, concise, and helpful for a website visitor.
    - If the answer comes from a specific document section, include a reference at the end.
 
    Context:
    {context}

    Question:
    {question}    
    """)

    # Create RAG chain
    rag_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt}
    )

    # Get chat history from in-memory store
    if session_id not in chat_history_store:
        chat_history_store[session_id] = []
    
    # Format chat history for the prompt
    chat_history_str = "\n".join(
        chat_history_store[session_id]
    ) if chat_history_store[session_id] else ""
    
    # Include chat history in the question
    if chat_history_str:
        full_question = f"Previous conversation:\n{chat_history_str}\n\nCurrent question: {query}"
    else:
        full_question = query


    #######################Cost Estimation########################

    # docs = retriever.get_relevant_documents(query)
    # context_text = "\n\n".join([doc.page_content for doc in docs])

    # formatted_prompt = prompt.format(
    #     context = context_text,
    #     question = full_question
    # )
    
    # messages = [
    #     {"role": "system", "content": formatted_prompt}
    # ]

    # chat_token = estimate_cost.tokens_for_chat_messages(messages)
    # print(f"Estimated tokens for this query: {chat_token} tokens")

    # chat_cost = estimate_cost.estimate_cost_for_chat_messages(chat_token)
    # print(f"Estimated cost for this query: ${chat_cost:.6f}")

    # embedding_token = estimate_cost.tokens_for_embedding(query)
    # print(f"Estimated tokens for embedding this query: {embedding_token} tokens")

    # embedding_cost = estimate_cost.estimate_cost_for_embedding(embedding_token)
    # print(f"Estimated cost for embedding this query: ${embedding_cost:.6f}")

    #######################Cost Estimation########################

    # Invoke the chain with chat history embedded in question
    result = rag_chain.invoke({
        "query": full_question
    })


    #######################Cost Estimation########################

    # usage = result.get("usage_metadata", {})
    # input_tokens = usage.get("input_tokens", 0)
    # output_tokens = usage.get("output_tokens", 0)

    # print(f"Actual input tokens used: {input_tokens} tokens")
    # print(f"Actual output tokens used: {output_tokens} tokens")


    #######################Cost Estimation########################


    if "We don't have the information currently" in result["result"]:
        print("Unknown question asked, sending email to admin...")
        print("Company email to notify:", company_email)
        utilities.Utilities_class.send_email_ai_response(company_email,query)
    
    # Save the current exchange to chat history
    chat_history_store[session_id].append(f"User: {query}")
    chat_history_store[session_id].append(f"Assistant: {result['result']}")
    
    # Keep only last 10 exchanges to avoid memory bloat
    if len(chat_history_store[session_id]) > 20:
        chat_history_store[session_id] = chat_history_store[session_id][-20:]
    
    return {
        "answer": result["result"],
        # "token" : {
        #     "chat_token": chat_token,
        #     "embedding_token": embedding_token
        # },
        # "cost" : {
        #     "chat_cost": chat_cost,
        #     "embedding_cost": embedding_cost
        # }
    }