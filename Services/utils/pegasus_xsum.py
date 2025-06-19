from transformers import PegasusTokenizer, PegasusForConditionalGeneration
from FastAPIProject.config.config_loader import config

local_dir = config["services"]["pegasus-xsum"]["path"]

tokenizer = PegasusTokenizer.from_pretrained(local_dir)
model = PegasusForConditionalGeneration.from_pretrained(local_dir)

def abstractive_summarization(text: str) -> str:
    """Generate an abstract summary of the input text using Pegasus model."""
    inputs = tokenizer(text, truncation=True, padding="longest", return_tensors="pt")
    summary_ids = model.generate(**inputs, max_length=60, num_beams=5, early_stopping=True)
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return summary

