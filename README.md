# AI Pentest Report Fine-Tuning Pipeline

This project shows how to create a dataset of AI pentest reports and fine-tune a model (Phi-3.5-mini-instruct) using Unsloth.

The pipeline consists of:
1. Generating synthetic AI pentest reports.
2. Summarizing real or synthetic reports and creating instruction-output CSVs.
3. Fine-tuning a model to summarize AI pentest JSON reports into human-readable reports.
4. Validating fine-tuned model with inference

---

## Setup

1. Clone the repo:

       git clone https://github.com/yourusername/ai-pentest-report-pipeline.git
       cd ai-pentest-report-pipeline

2. Create a virtual environment:

       python -m venv .venv
       source venv/bin/activate   # Linux/Mac
       .venv\Scripts\activate      # Windows

3. Install dependencies:

       pip install -r requirements.txt

4. Start jupyter lab using VS 2022 CMD (For fine-tuning on Windows)

> On Windows, some notebooks require compilation of extensions or access to build tools.  
> To avoid errors, open the **Developer Command Prompt for VS 2022**, then start Jupyter from there:  
> 1. Search for **Developer Command Prompt for VS 2022** in the Start menu.  
> 2. Open it and navigate to your project folder.  
> 3. Open virtual environnent and run `jupyter lab` to start the notebooks with the correct environment and PATH settings.  
> This ensures any required C/C++ build tools are available during dataset tokenization or model fine-tuning.


5. Installing llama.cpp for converting files for Ollama

    If you need to import your model to be used with Ollama, you can install `llama.cpp` directly from the GitHub repository:

        pip install git+https://github.com/ggml-org/llama.cpp

---

## Pipeline

### 1. Create Dataset
Run the notebook `notebooks/create_dataset.ipynb`. This will generate:
- `data/generated_csv/instruction_output.csv`

### 2. Fine-tune the Model
Run the notebook `notebooks/Phi_3_5_Mini_unsloth_finetune.ipynb`:
- Make sure `instruction_output.csv` exists in `data/generated_csv/`
- This notebook will tokenize and add instructions to dataset entries and fine-tune Phi-3.5-mini-instruct using Unsloth.

### 3. Inference
After fine-tuning, you can generate human-readable summaries of AI pentest reports.

### 4. Validation
Test report validity using  `notebooks/AI_pentest_ft_eval.ipynb` where you can use a generated dataset with instruction, output columns, compares output column with generated result.

---

## Results and future improvements

### 1. Dataset creation

First move to reduce JSON length reduced hallucinations and inference times drastically after going from full JSON reports to summaries containing only basic details about run like id, model, type, length, and probes with their detector results along with a final summary. Reducing the JSON length makes it easier for language models with small context windows to find and retain information.

The first attempts did not yield good results, tested using **meta-llama/Llama-2-7b, microsoft/Phi-4-mini-instruct** to generate full reports for output but due to inference times, datasets were only about 200-500 entries in length which led to model underfitting and poor performance due to small models hallucinating. 

Next attempts worked out better to create consistent and large-scale datasets by implementing them fully using the programmatical approach. This time, 5000 entries were generated which is a good balance between full coverage and faster fine-tuning times for the vairety and format of the instruction entries. Better results could be yielded by generating e.g. the final summary and next steps to take using an AI model, and the rest of the report should be done programmatically. After these are merged, the end result will yield a consistent, varying, and informative dataset. However, dataset currently weighs more towards entries with a smaller amount of probes, which might be the reason the model breaks when trying to give it 7 or more probes in a report.

### 2. Fine-tuning

Trying to run the fine-tuning script in Google Colab resulted in unnecessary wait times and loss of progress. Switching to run fine-tuning locally resulted in shorter training times and also fixed the issue with Colab of unnecessary restarts and runtime disconnects. Adding Unsloth to the fine-tuning script reduced time to train a single iteration from around 4 hours down to around 2.5 hours using a Nvidia RTX 3080 Graphics card. With more complex datasets and larger models, Azure AI Foundry is suggested for fine-tuning. 

Resulting fine-tunes are easy to upload and use through Hugging Face, and using `llama.cpp`, models can be easily translated to be used by Ollama. Future improvements should include testing other models with longer context limits and optimized handling of structured instructions, like `LLaMA 3 / 7B–13B`,  `Falcon 7B / 40B`, or `Qwen 7B / Gemma 7B`. 

### 3. Inference

Better results can be yielded from the AI model by setting it strict guidelines to follow when generating text. `data\eval_result_100_temp0_dosample_false.txt` showcases that when using `temperature = 0` and `do_sample = False`, the guidelines are too strict and especially with longer reports, even one wrongly generated token can send the model to hallucinate. Loosening the inference parameters to `temperature = 0.2`, `do_sample = True`, `top_p = 0.9` and `repetition_penalty=1.2` gave over 90% success rate, as shown in `data\eval_result_100_temp0.2_dosample_true_topp0.9reppen1.2.txt`. When the output is required to follow a certain format, it is best to keep the inference parameters tight, like in the second run, to keep the structure intact but also giving it room for errors makes it stay on track better. 

The script for comparing the expected output and model output using `all-MiniLM-L6-v2 SentenceTransformer` makes comparing the strings easier than straight up comparing two strings, as models rarely produce exactly correct results. This is shown well in the eval_result_xxx.txt files, as e.g. indentation lengths vary along with exact wording. This is also what makes the resulting comparison to always give results between around 72-92% for the correct matches. The comparison script needs to be improved to give a better validation score, as it resulted in giving false positives and false negatives in a couple of cases. Future implementation could check that all probes are mentioned with their correct evaluators, and entries with hallucinations could be discarded by checking for repeating patterns or unnecessary newlines.

It is good to note that entries that showcase model continuing after giving the response like `...<end><assistant>...` instead of ending with `...<end><endoftext>` will not happen in actual usage, as the model is cut off after giving the end-of-text token `<end>`. This is also why the same is done before the comparison is done in the evaluation script.
