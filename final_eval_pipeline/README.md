# Security Evaluation Test (SET) Reporting Pipeline

This pipeline processes JSON reports from Security Evaluation Tests, summarizes vulnerabilities, and produces a human-readable and AI-assisted report in HTML format. It consists of the following steps:

## 1. Input Handling
- **Load JSON report safely**: Read the input JSON report line by line to handle potential formatting errors. Invalid or malformed JSON entries are skipped with a warning.
- **Supported input types**: The report can be provided as:
  - A file path (`Path` or string)
  - A JSON string
  - A Python dictionary


- Uses the following format for input JSON report:

        {
        'run_id', 
        'model_type', 
        'model_name', 
        'run_length', 
        'SETs': [{
            'SET_classname',
            'description',
            'total_runs',
            'evaluation_results': [{
                'detector',
                'passed_count',
                'total_count',
                'pass_percentage',
                'pass_percentage_value',
                'outcome': 'Vulnerable'/'Resisted',
                'detector_remediation'
                },
            'SET_remediation'
            }],
            'recommended_remediations': []
        }

## 2. Human-Readable Report Generation
- **Generate descriptive summary**:
  - Extract SET names, descriptions, total runs, and individual detector results.
  - Include warnings about stochastic variability for runs with fewer than 100 repetitions.
  - Present recommended remediations for vulnerable detectors, referencing the appropriate remediation category from a predefined detector pool.
- **Format evaluation results**:
  - Each detector’s result is shown with the number of tests passed, total tests, percentage, and outcome (Vulnerable/Resisted).
  - Vulnerable results include remediation suggestions.
- **Overview section**:
  - Model name, type, run ID, and runtime.
  - Consolidated SET evaluations and relevant warnings.

## 3. AI-Oriented Input Formatting
- **Extract vulnerable SETs**:
  - Skip SETs where all detectors are `Resisted`.
  - Collect SET name, description, and overall pass percentage for vulnerable detectors.
  - Include any recommended remediations from the report.
- **JSON serialization**: The extracted data is converted into a compact JSON string suitable for AI inference.

## 4. AI Inference
- **Run inference** using a language model:
  - The AI receives only the vulnerable SET summary JSON.
  - Strict rules ensure the AI:
    - Produces exactly two sentences.
    - Summarizes issues without introducing speculative impacts.
    - Lists all recommended remediations exactly as provided.
    - Uses formal, technical language appropriate for security assessments.
- **Inference output handling**:
  - If no vulnerabilities are present, a pre-defined summary note is used instead.
  - Output is cleaned of template artifacts and unnecessary text.

## 5. Final Summary Construction
- **Combine human-readable and AI outputs**:
  - Append AI-generated summary to the descriptive SET report.
- **Add disclaimers and notes**:
  - Variability of results due to AI stochasticity.
  - Recommendation to perform additional runs for statistical reliability.
  - Warning about potential false positives or negatives.
  - Suggestion for human review of critical assessments.

## 6. HTML Report Generation
- **Save final report as HTML**:
  - Encapsulate the combined human-readable report and AI summary in an HTML file.
  - Include all warnings, notes, and remediation recommendations.
  - Ensure a clean and readable presentation for end users.

## 7. Full Evaluation Pipeline
- **Pipeline function**:
  1. Load JSON report safely.
  2. Generate human-readable summary.
  3. Extract and format vulnerable SETs for AI input.
  4. Run AI inference.
  5. Append notes and disclaimers.
  6. Generate HTML report for final output.
- **Outcome**:
  - A complete evaluation report in HTML containing:
    - Full human-readable SET summaries
    - AI-assisted vulnerability analysis
    - Relevant warnings, notes, and recommended remediations
