# Report summary imports
from pathlib import Path
import json
from datetime import datetime
import csv
import os

# Model inference imports
from unsloth import FastLanguageModel
from unsloth.chat_templates import get_chat_template
import torch
import pandas as pd
from transformers import AutoTokenizer

from set_descriptions import EXAMPLES

def run_inference(ai_input: str) -> str:

    MODEL_NAME = "unsloth/Llama-3.2-3B-Instruct"

    # Load model + tokenizer via Unsloth
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = MODEL_NAME,
        max_seq_length = 4096,     # adjust if needed
        dtype = None,              # auto
        load_in_4bit = False,      # set True if VRAM constrained
    )
    # Enable inference optimizations
    FastLanguageModel.for_inference(model)

    # Set up tokenizer template
    tokenizer = get_chat_template(
        tokenizer,
        chat_template="llama-3.1",
        mapping={"role": "from", "content": "value", "user": "human", "assistant": "gpt"},
    )

    # Enable faster inference
    FastLanguageModel.for_inference(model)

    messages = [
        {
            "role": "user",
            "content": f"""
You are an AI penetration test summarizing assistant. Summarize the given Security Evaluation Tests (SETs) according to the rules below, strictly based on the provided input.

1. Produce exactly two sentences total.
2. Sentence 1 MUST start with "## Issue Summary:\n" and present the weaknesses demonstrated by the SETs and their descriptions.
   - Do NOT introduce impacts, consequences, or behaviors not directly stated or clearly inferable from the descriptions.
3. Sentence 2 must start with "\n### Remediation Recommendation:\n" and include all recommended_remediations present in the input, expressed together as a single coherent sentence.
   - The sentence MUST NOT introduce remediations not present in the input, and MUST NOT generalize beyond them.
4. Use neutral, formal, technical language suitable for a security assessment report.
5. Do NOT include explanations, meta-commentary, or generation details.
6. Do NOT claim data access, exfiltration, system compromise, or real-world harm unless explicitly stated in the input.
7. Do NOT introduce speculative attack chains or inferred consequences beyond the SET descriptions.

STRICT OUTPUT TEMPLATE (MANDATORY):
- Sentence 1 MUST start with "## Issue Summary:".
- Sentence 2 MUST start with "### Remediation Recommendation:".
- The output MUST contain exactly two sentences and no additional text.


Example inputs and summaries:

Correct Input 1:
{EXAMPLES[0]["input"]}
Correct Summary 1:
{EXAMPLES[0]["output"]}

Correct Input 2:
{EXAMPLES[1]["input"]}
Correct Summary 2:
{EXAMPLES[1]["output"]}


Penetration test summary JSON:\n{ai_input}"""
        }
    ]


    inputs = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=False,
        return_tensors="pt",
    )

    if isinstance(inputs, dict):
        input_ids = inputs["input_ids"].to("cuda")
        attention_mask = inputs["attention_mask"].to("cuda")
    else:
        input_ids = inputs.to("cuda")
        attention_mask = None


    with torch.no_grad():
        output_ids = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=400,
            do_sample=False,
            temperature=0.0,
            top_p=1.0,
            repetition_penalty=1.2,
            use_cache=True,
        )

    return tokenizer.decode(output_ids[0], skip_special_tokens=True)


def run(ai_input: str) -> str:
    if "No vulnerabilities were found in the evaluated SETs." in ai_input:
        remediation_note = "## Issue Summary:\nNo vulnerabilities were found in the evaluated SETs."
    else:
        remediation_note = run_inference(ai_input)
        remediation_note = remediation_note.split("assistant\n")[1]
        remediation_note = remediation_note.split("<|eot_id|>")[0]

    return remediation_note