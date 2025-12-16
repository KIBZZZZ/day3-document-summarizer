import os
from openai import OpenAI
from dotenv import load_dotenv
from text_extraction import read_document

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def chunk_text(text, chunk_size=3000):
    """
    Split text into chunks of approximately chunk_size characters
    Try to split at paragraph boundaries for better context
    """
    # Split by paragraphs
    paragraphs = text.split('\n\n')
    
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        # If adding this paragraph exceeds chunk_size, save current chunk
        if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = paragraph
        else:
            current_chunk += "\n\n" + paragraph if current_chunk else paragraph
    
    # Add the last chunk
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def summarize_chunk(chunk, chunk_number, total_chunks):
    """Summarize a single chunk"""
    prompt = f"""Summarize this section (part {chunk_number} of {total_chunks}) of a document.
Focus on key points, important data, and main ideas.
Keep it concise (3-5 sentences).

Text:
{chunk}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are summarizing a section of a larger document. Be concise and focus on key information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=200
        )
        
        summary = response.choices[0].message.content
        tokens = response.usage.total_tokens
        cost = (response.usage.prompt_tokens / 1000) * 0.00015 + \
               (response.usage.completion_tokens / 1000) * 0.0006
        
        return {
            "success": True,
            "summary": summary,
            "tokens": tokens,
            "cost": cost
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def combine_summaries(chunk_summaries):
    """Combine multiple chunk summaries into one coherent summary"""
    combined_text = "\n\n".join(chunk_summaries)
    
    prompt = f"""Here are summaries of different sections of a document.
Combine them into one coherent, comprehensive summary.
Remove redundancy and organize logically.
Keep it 2-4 paragraphs.

Section summaries:
{combined_text}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are creating a final summary by combining section summaries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=500
        )
        
        final_summary = response.choices[0].message.content
        tokens = response.usage.total_tokens
        cost = (response.usage.prompt_tokens / 1000) * 0.00015 + \
               (response.usage.completion_tokens / 1000) * 0.0006
        
        return {
            "success": True,
            "summary": final_summary,
            "tokens": tokens,
            "cost": cost
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def extract_key_info(text):
    """Extract key information like dates, numbers, action items"""
    prompt = f"""Extract key information from this document:

1. Important dates (if any)
2. Key numbers/statistics
3. Action items or recommendations
4. Main entities (people, companies, locations)

Format as a structured list. If any category has no relevant info, write "None found".

Document:
{text[:8000]}"""  # Limit to avoid token limits

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You extract structured information from documents."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Low temperature for accurate extraction
            max_tokens=400
        )
        
        extraction = response.choices[0].message.content
        tokens = response.usage.total_tokens
        cost = (response.usage.prompt_tokens / 1000) * 0.00015 + \
               (response.usage.completion_tokens / 1000) * 0.0006
        
        return {
            "success": True,
            "extraction": extraction,
            "tokens": tokens,
            "cost": cost
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def advanced_summarize(text):
    """
    Advanced summarization that handles long documents
    by chunking and combining summaries
    """
    print("\n" + "="*70)
    print("🔄 ADVANCED SUMMARIZATION PROCESS")
    print("="*70)
    
    # Check document length
    word_count = len(text.split())
    char_count = len(text)
    
    print(f"\n📊 Document stats:")
    print(f"   - Words: {word_count:,}")
    print(f"   - Characters: {char_count:,}")
    
    total_cost = 0.0
    
    # Step 1: Extract key information first
    print(f"\n📋 Step 1: Extracting key information...")
    
    extraction_result = extract_key_info(text)
    
    if extraction_result['success']:
        print(f"✅ Extracted key info")
        print(f"   Tokens: {extraction_result['tokens']} | Cost: ${extraction_result['cost']:.6f}")
        total_cost += extraction_result['cost']
    else:
        print(f"❌ Extraction failed: {extraction_result['error']}")
    
    # Step 2: Handle based on length
    if char_count < 12000:  # Short document
        print(f"\n📝 Step 2: Document is short enough for direct summarization")
        
        prompt = """Provide a comprehensive summary of this document.
Include: main topic, key points, important details, and conclusions.
Format: 3-4 paragraphs."""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert document summarizer."},
                    {"role": "user", "content": f"{prompt}\n\nDocument:\n{text}"}
                ],
                temperature=0.5,
                max_tokens=600
            )
            
            summary = response.choices[0].message.content
            tokens = response.usage.total_tokens
            cost = (response.usage.prompt_tokens / 1000) * 0.00015 + \
                   (response.usage.completion_tokens / 1000) * 0.0006
            
            total_cost += cost
            
            print(f"✅ Generated summary")
            print(f"   Tokens: {tokens} | Cost: ${cost:.6f}")

            final_summary = summary
            
            chunk_summaries = [summary]
            
        except Exception as e:
            print(f"❌ Summarization failed: {e}")
            return None
    
    else:  # Long document - needs chunking
        print(f"\n📝 Step 2: Document is long, splitting into chunks...")
        
        chunks = chunk_text(text, chunk_size=10000)
        print(f"   Created {len(chunks)} chunks")
        
        chunk_summaries = []
        
        for i, chunk in enumerate(chunks, 1):
            print(f"\n   Processing chunk {i}/{len(chunks)}...")
            
            result = summarize_chunk(chunk, i, len(chunks))
            
            if result['success']:
                chunk_summaries.append(result['summary'])
                total_cost += result['cost']
                print(f"   ✅ Chunk {i} summarized | Tokens: {result['tokens']} | Cost: ${result['cost']:.6f}")
            else:
                print(f"   ❌ Chunk {i} failed: {result['error']}")
        
        if not chunk_summaries:
            print("\n❌ No chunks were successfully summarized!")
            return None
        
        # Step 3: Combine chunk summaries
        if len(chunks) > 1:
            print(f"\n🔗 Step 3: Combining {len(chunk_summaries)} chunk summaries...")
            
            combine_result = combine_summaries(chunk_summaries)
            
            if combine_result['success']:
                final_summary = combine_result['summary']
                total_cost += combine_result['cost']
                print(f"✅ Combined into final summary")
                print(f"   Tokens: {combine_result['tokens']} | Cost: ${combine_result['cost']:.6f}")
            else:
                print(f"❌ Combining failed: {combine_result['error']}")
                final_summary = "\n\n".join(chunk_summaries)
        else:
            final_summary = chunk_summaries[0]
    
    # Prepare final result
    result = {
        "summary": final_summary,
        "key_info": extraction_result.get('extraction', 'Not available') if extraction_result['success'] else 'Extraction failed',
        "total_cost": total_cost,
        "chunks_processed": len(chunks) if char_count >= 12000 else 1,
        "original_words": word_count
    }
    
    return result

def display_advanced_summary(result):
    """Display the advanced summary result"""
    if not result:
        print("\n❌ No summary to display!")
        return
    
    print("\n" + "┏" + "━"*68 + "┓")
    print("┃ 📄 DOCUMENT SUMMARY" + " "*48 + "┃")
    print("┣" + "━"*68 + "┫")
    
    # Display summary
    lines = result['summary'].split('\n')
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
    
    print("┗" + "━"*68 + "┛")
    
    # Display key information
    print("\n" + "┏" + "━"*68 + "┓")
    print("┃ 🔍 KEY INFORMATION EXTRACTED" + " "*39 + "┃")
    print("┣" + "━"*68 + "┫")
    
    key_lines = result['key_info'].split('\n')
    for line in key_lines:
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
    
    print("┗" + "━"*68 + "┛")
    
    # Display statistics
    print("\n" + "┏" + "━"*68 + "┓")
    print("┃ 📊 PROCESSING STATISTICS" + " "*43 + "┃")
    print("┣" + "━"*68 + "┫")
    print(f"┃ Original document: {result['original_words']:,} words" + " "*(41-len(f"{result['original_words']:,}")) + "┃")
    print(f"┃ Chunks processed: {result['chunks_processed']}" + " "*51 + "┃")
    print(f"┃ Total cost: ${result['total_cost']:.6f}" + " "*47 + "┃")
    print("┗" + "━"*68 + "┛")

def main():
    """Main function"""
    print("\n" + "="*70)
    print("          🚀 ADVANCED DOCUMENT SUMMARIZER 🚀")
    print("          Handles Long Documents with Chunking")
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
    
    # Read document
    print(f"\n📖 Reading: {selected_file}")
    doc_result = read_document(file_path)
    
    if not doc_result['success']:
        print(f"❌ Failed to read document: {doc_result['error']}")
        return
    
    # Advanced summarization
    result = advanced_summarize(doc_result['text'])
    
    if result:
        display_advanced_summary(result)
        
        # Save option
        save_choice = input("\n💾 Save this summary? (y/n): ").strip().lower()
        
        if save_choice == 'y':
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"advanced_summary_{timestamp}_{selected_file}"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("="*70 + "\n")
                f.write("ADVANCED DOCUMENT SUMMARY\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*70 + "\n\n")
                f.write(f"Original Document: {file_path}\n")
                f.write(f"Original Length: {result['original_words']:,} words\n")
                f.write(f"Chunks Processed: {result['chunks_processed']}\n")
                f.write(f"Total Cost: ${result['total_cost']:.6f}\n")
                f.write("\n" + "-"*70 + "\n\n")
                f.write("SUMMARY:\n\n")
                f.write(result['summary'])
                f.write("\n\n" + "-"*70 + "\n\n")
                f.write("KEY INFORMATION EXTRACTED:\n\n")
                f.write(result['key_info'])
                f.write("\n\n" + "="*70 + "\n")
            
            print(f"✅ Saved to: {output_file}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Program interrupted")