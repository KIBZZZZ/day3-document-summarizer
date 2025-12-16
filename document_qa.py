import os
from openai import OpenAI
from dotenv import load_dotenv
from text_extraction import read_document

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Store loaded document globally
current_document = {
    "text": "",
    "filename": "",
    "word_count": 0
}

session_stats = {
    "questions_asked": 0,
    "total_cost": 0.0
}

def load_document_for_qa(file_path):
    """Load a document into memory for Q&A"""
    global current_document
    
    print(f"\n📖 Loading document for Q&A...")
    
    result = read_document(file_path)
    
    if not result['success']:
        print(f"❌ Failed to load: {result['error']}")
        return False
    
    current_document['text'] = result['text']
    current_document['filename'] = os.path.basename(file_path)
    current_document['word_count'] = result['word_count']
    
    print(f"✅ Loaded: {current_document['filename']}")
    print(f"   {current_document['word_count']:,} words")
    
    return True

def answer_question(question):
    """Answer a question about the loaded document"""
    global session_stats
    
    if not current_document['text']:
        return {
            "success": False,
            "error": "No document loaded! Please load a document first."
        }
    
    # Truncate if too long (keep within token limits)
    text = current_document['text'][:30000]  # Roughly 7500 tokens
    
    prompt = f"""Based on the document below, answer this question:

Question: {question}

Document:
{text}

Instructions:
- Answer based ONLY on information in the document
- If the answer isn't in the document, say "This information is not in the document"
- Be specific and cite relevant parts when possible
- Keep answer concise but complete"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You answer questions based on provided documents. Be accurate and cite the document."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Low for accuracy
            max_tokens=400
        )
        
        answer = response.choices[0].message.content
        tokens = response.usage.total_tokens
        cost = (response.usage.prompt_tokens / 1000) * 0.00015 + \
               (response.usage.completion_tokens / 1000) * 0.0006
        
        session_stats['questions_asked'] += 1
        session_stats['total_cost'] += cost
        
        return {
            "success": True,
            "answer": answer,
            "tokens": tokens,
            "cost": cost
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def display_qa(question, result):
    """Display Q&A in a nice format"""
    print("\n" + "┏" + "━"*68 + "┓")
    print(f"┃ ❓ QUESTION" + " "*56 + "┃")
    print("┣" + "━"*68 + "┫")
    
    # Wrap question
    words = question.split()
    current_line = ""
    for word in words:
        if len(current_line) + len(word) + 1 <= 66:
            current_line += word + " "
        else:
            print(f"┃ {current_line.rstrip():<66} ┃")
            current_line = word + " "
    if current_line:
        print(f"┃ {current_line.rstrip():<66} ┃")
    
    print("┣" + "━"*68 + "┫")
    print(f"┃ 💡 ANSWER" + " "*58 + "┃")
    print("┣" + "━"*68 + "┫")
    
    if result['success']:
        # Wrap answer
        lines = result['answer'].split('\n')
        for line in lines:
            if not line.strip():
                print("┃" + " "*68 + "┃")
                continue
            
            if len(line) <= 66:
                print(f"┃ {line:<66} ┃")
            else:
                words = line.split()
                current_line = ""
                for word in words:
                    if len(current_line) + len(word) + 1 <= 66:
                        current_line += word + " "
                    else:
                        print(f"┃ {current_line.rstrip():<66} ┃")
                        current_line = word + " "
                if current_line:
                    print(f"┃ {current_line.rstrip():<66} ┃")
        
        print("┣" + "━"*68 + "┫")
        print(f"┃ 📊 Tokens: {result['tokens']:<10} | 💰 Cost: ${result['cost']:.6f}" + " "*25 + "┃")
    else:
        print(f"┃ ❌ Error: {result['error']:<57} ┃")
    
    print("┗" + "━"*68 + "┛")

def show_session_stats():
    """Display session statistics"""
    print("\n" + "┏" + "━"*68 + "┓")
    print("┃ 📊 SESSION STATISTICS" + " "*46 + "┃")
    print("┣" + "━"*68 + "┫")
    print(f"┃ Document: {current_document['filename']:<56} ┃")
    print(f"┃ Questions asked: {session_stats['questions_asked']:<50} ┃")
    print(f"┃ Total cost: ${session_stats['total_cost']:.6f}" + " "*47 + "┃")
    if session_stats['questions_asked'] > 0:
        avg_cost = session_stats['total_cost'] / session_stats['questions_asked']
        print(f"┃ Average cost/question: ${avg_cost:.6f}" + " "*38 + "┃")
    print("┗" + "━"*68 + "┛")

def main():
    """Main function"""
    print("\n" + "="*70)
    print("          ❓ DOCUMENT Q&A SYSTEM ❓")
    print("          Ask Questions About Your Documents")
    print("="*70)
    
    test_folder = "test_documents"
    
    if not os.path.exists(test_folder):
        print(f"\n❌ Folder not found: {test_folder}")
        return
    
    files = [f for f in os.listdir(test_folder) if os.path.isfile(os.path.join(test_folder, f))]
    
    if not files:
        print(f"\n❌ No files found in {test_folder}/")
        return
    
    print(f"\n📚 Available documents:")
    for i, file in enumerate(files, 1):
        print(f"   {i}. {file}")
    
    choice = input(f"\nSelect document (1-{len(files)}): ").strip()
    
    try:
        file_index = int(choice) - 1
        if file_index < 0 or file_index >= len(files):
            print("❌ Invalid choice!")
            return
        
        selected_file = files[file_index]
        file_path = os.path.join(test_folder, selected_file)
        
    except ValueError:
        print("❌ Please enter a number!")
        return
    
    # Load document
    if not load_document_for_qa(file_path):
        return
    
    print("\n" + "="*70)
    print("🎯 Document loaded! You can now ask questions.")
    print("="*70)
    print("\nCommands:")
    print("  • Type your question and press Enter")
    print("  • Type 'stats' to see session statistics")
    print("  • Type 'quit' or 'exit' to stop")
    print("="*70)
    
    # Q&A loop
    while True:
        question = input("\n❓ Your question: ").strip()
        
        if question.lower() in ['quit', 'exit', 'q']:
            show_session_stats()
            print("\n👋 Thanks for using Document Q&A!")
            break
        
        if question.lower() == 'stats':
            show_session_stats()
            continue
        
        if not question:
            print("⚠️  Please enter a question!")
            continue
        
        # Answer question
        result = answer_question(question)
        display_qa(question, result)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Program interrupted")
        show_session_stats()