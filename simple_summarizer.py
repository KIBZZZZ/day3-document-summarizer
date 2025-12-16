import os
from openai import OpenAI
from dotenv import load_dotenv
from text_extraction import read_document

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def count_tokens_estimate(text):
    """
    Rough estimate: 1 token ≈ 4 characters
    This is approximate - actual tokenization is more complex
    """
    return len(text) // 4

def summarize_document(text, summary_type="executive"):
    """
    Summarize a document using OpenAI
    
    Args:
        text: The document text to summarize
        summary_type: Type of summary (executive, bullet, detailed)
    """
    
    # Check if text is too long
    estimated_tokens = count_tokens_estimate(text)
    
    if estimated_tokens > 12000:  # Leave room for response
        print(f"⚠️  Warning: Document is very long ({estimated_tokens} estimated tokens)")
        print("   Truncating to first 12,000 tokens worth of text...")
        text = text[:48000]  # Roughly 12,000 tokens
    
    # Different prompts for different summary types
    prompts = {
        "executive": """Provide an executive summary of this document. 
                       Include: main topic, key points (3-5), and conclusion.
                       Format: 2-3 paragraphs, professional tone.
                       Keep it concise but comprehensive.""",
        
        "bullet": """Summarize this document as bullet points.
                    Include:
                    - Main topic
                    - Key findings (5-7 points)
                    - Important numbers/statistics
                    - Conclusions or recommendations
                    Be clear and concise.""",
        
        "detailed": """Provide a detailed summary of this document.
                      Include all major sections, key arguments, important data,
                      and conclusions. Maintain the document's structure.
                      Be thorough but don't reproduce the entire document."""
    }
    
    prompt = prompts.get(summary_type, prompts["executive"])
    
    print(f"\n🔄 Generating {summary_type} summary...")
    print(f"📊 Estimated input tokens: ~{estimated_tokens}")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert document analyst and summarizer."},
                {"role": "user", "content": f"{prompt}\n\nDocument:\n{text}"}
            ],
            temperature=0.5,  # Balanced for summaries
            max_tokens=800
        )
        
        summary = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        
        # Calculate cost
        cost = (response.usage.prompt_tokens / 1000) * 0.00015 + \
               (response.usage.completion_tokens / 1000) * 0.0006
        
        return {
            "success": True,
            "summary": summary,
            "tokens": tokens_used,
            "cost": cost,
            "summary_type": summary_type
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def display_summary(result):
    """Display summary in a nice format"""
    if not result['success']:
        print(f"\n❌ Error: {result['error']}")
        return
    
    print("\n" + "┏" + "━"*68 + "┓")
    print(f"┃ 📄 {result['summary_type'].upper()} SUMMARY" + " "*(55-len(result['summary_type'])) + "┃")
    print("┣" + "━"*68 + "┫")
    
    # Display summary with word wrapping
    lines = result['summary'].split('\n')
    for line in lines:
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
    print("┗" + "━"*68 + "┛")

def save_summary(filename, original_file, summary_text, metadata):
    """Save summary to a text file"""
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"summary_{timestamp}_{filename}"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("DOCUMENT SUMMARY\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*70 + "\n\n")
        f.write(f"Original Document: {original_file}\n")
        f.write(f"Summary Type: {metadata['summary_type']}\n")
        f.write(f"Tokens Used: {metadata['tokens']}\n")
        f.write(f"Cost: ${metadata['cost']:.6f}\n")
        f.write("\n" + "-"*70 + "\n\n")
        f.write(summary_text)
        f.write("\n\n" + "="*70 + "\n")
    
    return output_file

def main():
    """Main function"""
    print("\n" + "="*70)
    print("          📄 DOCUMENT SUMMARIZER 📄")
    print("          Generate AI-Powered Summaries")
    print("="*70)
    
    # List available documents
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
    
    # Get user choice
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
    
    # Read document
    print(f"\n📖 Reading: {selected_file}")
    doc_result = read_document(file_path)
    
    if not doc_result['success']:
        print(f"❌ Failed to read document: {doc_result['error']}")
        return
    
    # Choose summary type
    print("\n📋 Choose summary type:")
    print("   1. Executive Summary (concise, 2-3 paragraphs)")
    print("   2. Bullet Points (key points listed)")
    print("   3. Detailed Summary (comprehensive)")
    
    summary_choice = input("\nSelect type (1-3) [default: 1]: ").strip()
    
    summary_types = {
        "1": "executive",
        "2": "bullet",
        "3": "detailed"
    }
    
    summary_type = summary_types.get(summary_choice, "executive")
    
    # Generate summary
    result = summarize_document(doc_result['text'], summary_type)
    
    # Display
    display_summary(result)
    
    if result['success']:
        # Ask to save
        save_choice = input("\n💾 Save this summary? (y/n): ").strip().lower()
        
        if save_choice == 'y':
            output_file = save_summary(
                selected_file,
                file_path,
                result['summary'],
                result
            )
            print(f"✅ Saved to: {output_file}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Program interrupted")