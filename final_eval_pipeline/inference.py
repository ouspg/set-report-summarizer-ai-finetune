# Report summary imports
from pathlib import Path
import json
import torch
from unsloth import FastLanguageModel
from unsloth.chat_templates import get_chat_template

from set_descriptions import EXAMPLES

MODEL_NAME = "nraesalmi/SET_eval_gemma-3_adapters" # https://huggingface.co/nraesalmi/SET_eval_gemma-3_finetuned
BASE_MODEL = "unsloth/gemma-3-4b-it"

def run_inference(ai_input: str) -> str:
    """
    Run AI inference using Gemma-3 chat template for SET summaries.
    """

    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Load model + tokenizer via Unsloth
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = BASE_MODEL,
        max_seq_length = 2048,     # adjust if needed 8192
        dtype = None,              # auto
        load_in_4bit = True,      # set True if VRAM constrained
    )

    # Add finetuned adapter on top
    model.load_adapter(MODEL_NAME)

    # Enable inference optimizations
    FastLanguageModel.for_inference(model)

    # Initialize tokenizer with Gemma-3 template
    tokenizer = get_chat_template(
        tokenizer,
        chat_template="gemma-3",
    )

    # Build the prompt
    messages = [
        {
            "role": "user",
            "content": [
            {
                "type": "text",
                "text": f"""You are an AI penetration test summarizing assistant. Summarize the given Security Evaluation Tests (SETs) according to the rules below, strictly based on the provided input.

1. Produce exactly two sentences total.
2. Sentence 1 MUST start with "\n## Issue Summary:\n" and present the weaknesses demonstrated by the SETs and their descriptions.
   - Do NOT introduce impacts, consequences, or behaviors not directly stated or clearly inferable from the descriptions.
3. Sentence 2 MUST start with "\n### Recommended Remediations:\n" and include all recommended_remediations present in the input.
   - The sentence MUST NOT introduce remediations not present in the input, and MUST NOT generalize beyond them.
4. Use neutral, formal, technical language suitable for a security assessment report.
5. Do NOT include explanations, meta-commentary, or generation details.
6. Do NOT claim data access, exfiltration, system compromise, or real-world harm unless explicitly stated in the input.
7. Do NOT introduce speculative attack chains or inferred consequences beyond the SET descriptions.

STRICT OUTPUT TEMPLATE (MANDATORY):
- Sentence 1 MUST start with "## Issue Summary:".
- Sentence 2 MUST start with "### Recommended Remediations:".
- The output MUST contain exactly two sentences and no additional text.

Here are two example Result-Summary pairs 
Result 1:
{EXAMPLES[2]["input"]}
Summary 1:
{EXAMPLES[2]["expected_output"]}

Result 2:
{EXAMPLES[3]["input"]}
Summary 2:
{EXAMPLES[3]["expected_output"]}

Here is the penetration test result to summarize:
{ai_input}"""}]}]

    # Tokenize input using Gemma-3 template
    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_tensors="pt",
        return_dict=True,
    )

    # Move inputs to the available device
    for k in inputs:
        inputs[k] = inputs[k].to(device)

    # Generate model output
    generated_ids = model.generate(
        **inputs.to("cuda"),
        max_new_tokens=128,
        temperature=1.0,
        top_p=0.95,
        top_k=64,
    )

    prompt_len = inputs["input_ids"].shape[-1]
    new_tokens = generated_ids[0, prompt_len:]

    decoded_output = tokenizer.decode(
        new_tokens,
        skip_special_tokens=True,
    )

    # Extract only the assistant/model content
    # Gemma-3 format: <start_of_turn>model\nCONTENT<end_of_turn>
    if "<start_of_turn>model\n" in decoded_output:
        result = decoded_output.split("<start_of_turn>model\n")[1]
        result = result.split("<end_of_turn>")[0]
    else:
        result = decoded_output

    return result.strip()

def run(ai_input: str) -> str:
    """
    Wrapper to handle the 'no vulnerabilities' case.
    """
    if "No vulnerabilities were found in the evaluated SETs." in ai_input:
        return "## Issue Summary:\nNo vulnerabilities were found in the evaluated SETs."
    else:
        return run_inference(ai_input)
