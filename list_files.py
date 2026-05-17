from pathlib import Path

# Define the files in the order you want them structured
CORE_FILES = [
    "main.py",
    "src/core/config.py",
    "src/api/dependencies.py",
]

SERVICES = [
    "src/services/auth_service.py",
    "src/services/chat_service.py",
    "src/services/htl_service.py",
    "src/services/booking_service.py",
    "src/services/provider_service.py",
]

ROUTES = [
    "src/api/v1/auth.py",
    "src/api/v1/chat.py",
    "src/api/v1/htl.py",
    "src/api/v1/bookings.py",
]

MODELS_AND_DB = [
    "src/models/auth.py",
    "src/models/chat.py",
    "src/models/htl.py",
    "src/models/booking.py",
    "src/database/models.py",
    "src/database/connection.py",
]

# Group them into conceptual parts so you can easily break down prompts
PROMPT_PARTS = {
    "Part 1: Core Setup & Models": CORE_FILES + MODELS_AND_DB,
    "Part 2: Business Logic Services": SERVICES,
    "Part 3: API Routing Endpoints": ROUTES,
}

OUTPUT_FILE = "juvo_context.txt"

def generate_llm_context():
    output_path = Path(OUTPUT_FILE)
    
    with open(output_path, "w", encoding="utf-8") as outfile:
        outfile.write("# JUVO PROJECT CODE CONTEXT\n")
        outfile.write("This file contains the architectural layout and source code for the Juvo service orchestration engine.\n\n")
        
        for part_name, file_list in PROMPT_PARTS.items():
            outfile.write(f"\n{'='*50}\n")
            outfile.write(f"## {part_name}\n")
            outfile.write(f"{'='*50}\n\n")
            
            print(f"Processing {part_name}...")
            
            for file_str in file_list:
                file_path = Path(file_str)
                
                outfile.write(f"### File: `{file_str}`\n")
                if not file_path.exists():
                    outfile.write("*(File missing or not found in local path)*\n\n")
                    print(f"  ⚠️ Missing: {file_str}")
                    continue
                    
                try:
                    content = file_path.read_text(encoding="utf-8")
                    # Wrap inside markdown backticks with python syntax highlighting
                    outfile.write("```python\n")
                    outfile.write(content)
                    outfile.write("\n```\n\n")
                    print(f"  ✓ Added: {file_str}")
                except Exception as e:
                    outfile.write(f"*(Error reading file: {str(e)})*\n\n")
                    print(f"  ❌ Error reading: {file_str}")

    # Estimate character/token limits roughly
    total_chars = output_path.stat().st_size
    print(f"\nDone! Everything combined into: {OUTPUT_FILE}")
    print(f"Total file size: ~{total_chars / 1024:.2f} KB")
    
    if total_chars > 80000:
        print("\n💡 Tip: The output is quite large. Use the labeled markdown sections ('Part 1', 'Part 2', etc.) to copy-paste into Claude in chunks!")

if __name__ == "__main__":
    generate_llm_context()