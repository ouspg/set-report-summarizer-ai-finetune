# Security Evaluation Test Report Summarizing Fine-Tune Pipeline

This project presents a workflow for creating a dataset of AI pentest reports and fine-tuning a LLM (`unsloth/gemma-3-4b-it`) using Unsloth, as well as provides a pipeline for creating a human-readable document from a SET run result.

The dataset creation and finetune workflow consists of:
1. Generating synthetic AI pentest reports.
2. Summarizing real or synthetic reports and creating instruction-output CSVs.
3. Fine-tuning a model to summarize AI pentest JSON reports into human-readable reports.
4. Validating fine-tuned model with inference

#### The SET report summarizing pipeline can be found from [`final_eval_pipeline`](final_eval_pipeline)

---

## Finetune Setup

1. Clone the repo:

       git clone https://github.com/ouspg/llm-finetune-set-report-eval.git
       cd llm-finetune-set-report-eval

2. Create a virtual environment:

       python -m venv .venv
       source venv/bin/activate   # Linux/Mac
       .venv\Scripts\activate      # Windows

3. Install dependencies:

       pip install -r requirements.txt

4. Open project/Start jupyter lab using VS 2022 CMD (For fine-tuning on Windows)

> On Windows, some notebooks require compilation of extensions or access to build tools.  
> To avoid errors, open the **Developer Command Prompt for VS 2022**, then start Jupyter from there:  
> 1. Search for **Developer Command Prompt for VS 2022** in the Start menu.  
> 2. Open it and navigate to your project folder.  
> 3. Open virtual environnent and run `jupyter lab` to start the notebooks with the correct environment and PATH settings.  
> This ensures any required C/C++ build tools are available during dataset tokenization or model fine-tuning.

5. Run dataset and finetuning notebooks

       1. `create_dataset.ipynb` to create a dataset containing synthetic data input entries
       2. `generate_report.ipynb` to generate output entries either using a LLM or programmatically
       3. `Gemma-3_SET_eval_finetune.ipynb` to fineune the model using the generated dataset
       4.  `Gemma-3_SET_model_eval.ipynb` to run inference on the finetuned model and to validate the results by comparing the generated result with the output field in a dataset

---

## Workflow

### 1. Create Dataset input entries
Run the notebook `notebooks/create_dataset.ipynb`. This will generate:
- `data/generated_csv/instruction_output.csv`containing synthetic data inputs

### 2. Generate dataset outputs and format dataset to .csv format
Run `generate_report.ipynb` to generate output entries either using a LLM or programmatically

### 3. Fine-tune the Model
Run the notebook `notebooks/Gemma-3_SET_eval_finetune.ipynb`:
- Make sure the input dataset exists in `data/` in csv format
- This notebook will tokenize and add instructions to dataset entries and fine-tune `gemma-3-4b-it` using Unsloth.

> This notebook can also be found on Google Colab at https://colab.research.google.com/drive/1RIQwgIiwN8ROi8WxWH0NIh7vrSu-08Sq?usp=sharing

### 4. Inference and Validation
Test report generation and validity using  `notebooks/Gemma-3_SET_model_eval.ipynb` where you can use a generated validation dataset with input and output columns, compares output column with generated result.

---

## Results and future improvements

### 1. Dataset creation

First move to reduce JSON length reduced hallucinations and inference times drastically after going from full JSON reports to summaries containing only basic details about run like id, model, type, length, and probes with their detector results along with a final summary. Reducing the JSON length makes it easier for language models with small context windows to find and retain information.

The first attempts did not yield good results, tested using `meta-llama/Llama-2-7b`, `microsoft/Phi-4-medium-instruct` to generate full reports for output but due to inference times, datasets were only about 200-500 entries in length which led to model underfitting and poor performance due to small models hallucinating. Moved on due to long finetuning times

Next attempts worked out better to create consistent and large-scale datasets by implementing them fully using the programmatical approach and moving only the final summary field to be produced by the LLM. This time, 1500 train and 200 test entries were generated which is a good balance between full coverage and faster fine-tuning times for the vairety and format of the instruction entries. Using a smaller model like the `Phi-3.5-mini-inference` produced unreliable results most likely due to the small size of the model. 

Best results were yielded using `unsloth/gemma-3-4b-it`, which balances good results and reasonable training times and run performance. By only generating the report summary with the model, reliable and usable results were achieved.

### 2. Fine-tuning

Trying to run the fine-tuning script in Google Colab resulted in unnecessary wait times and loss of progress with larger models. Switching to run fine-tuning locally resulted in shorter training times and also fixed the issue with Colab of unnecessary restarts and runtime disconnects. Adding Unsloth to the fine-tuning script reduced time to train a single iteration from around 4 hours (during peak hours) down to around 2.5 hours using a Nvidia RTX 3080 Graphics card. With more complex datasets and larger models, Azure AI Foundry is suggested for fine-tuning.

Resulting fine-tunes are easy to upload and use through Hugging Face, and using `llama.cpp`, models can be easily translated to be used by Ollama. Future improvements should include testing other models with longer context limits and optimized handling of structured instructions, like `LLaMA 3 / 7B–13B`,  `Falcon 7B / 40B`, or `Qwen 7B / Gemma 7B`. 

### 3. Inference

Better results can be yielded from the AI model by setting it strict guidelines to follow when generating text with strong format requirements. When the output is required to follow a certain format, it is best to keep the inference parameters tight. 

The script for comparing the expected output and model output using `all-MiniLM-L6-v2 SentenceTransformer` makes comparing the strings easier than straight up comparing two strings. While still not perfect, it gives a general idea of the models accuracy as they rarely produce exactly the results that they are taught e.g. indentation lengths vary along with exact wording. This is also what makes the resulting comparison to always give results between around 72-92% for the correct matches. The comparison script needs to be improved to give a better validation score, as it resulted in giving false positives and false negatives in a couple of cases. Future implementation could check that all results are mentioned with their correct evaluators, and entries with hallucinations could be discarded by checking for repeating patterns or unnecessary newlines.
