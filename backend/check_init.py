import logging
import sys

# Configure basic logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

print("Starting initialization check...")

try:
    print("Importing faster_whisper...")
    from faster_whisper import WhisperModel
    print("Import successful.")
    
    print("Initializing WhisperModel (base.en, CPU, INT8)...")
    model = WhisperModel("base.en", device="cpu", compute_type="int8")
    print("WhisperModel initialized.")

    print("Importing kokoro...")
    from kokoro import KPipeline
    print("Import successful.")

    print("Initializing Kokoro pipeline (American English)...")
    pipeline = KPipeline(lang_code='a')
    print("Kokoro pipeline initialized.")

    print("\n--- ALL SYSTEMS NOMINAL ---")

except Exception as e:
    print(f"\n!!! ERROR DURING INITIALIZATION !!!\n{e}")
    sys.exit(1)
