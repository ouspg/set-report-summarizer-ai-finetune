import json
from pathlib import Path
from typing import Union, List, Dict

from set_descriptions import SET_DESCRIPTIONS, DETECTOR_POOL

from inference import run

"""
Functions to evaluate and summarize SET results from JSON reports.

Uses the following format for input JSON report:

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
"""

def load_jsonl_safely(path: Path):
    entries = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"⚠️ Skipping invalid JSON on line {lineno}: {e}")
                continue
    return entries

def generate_report_string(report):
    """
    Convert a single JSON report into a human-readable string.
    """
    SETs_section = ""

    less_than_100_runs = 'The stochasticity of artificial intelligence models leaves variance in their outputs, so a larger number of runs gives a better picture of the test results.'
    more_than_100_runs = 'These test results give a good statistical picture of the target\'s sensitivity to the attack in question.'

    for SET in report.get("SETs", []):
        SET_name = SET.get("SET_classname", "unknown")
        description = SET.get("description", "No description available.")
        total_runs = SET.get("total_runs", "unknown")

        eval_results = SET.get("evaluation_results", [])

        evaluation_lines = []
        for ev in eval_results:
            detector = ev.get("detector", "unknown")
            passed = ev.get("passed_count", 0)
            total = ev.get("total_count", 0)
            percent = ev.get("pass_percentage", "N/A")
            outcome = ev.get("outcome", "unknown")

            line = f"        - {detector}: Passed {passed}/{total} tests ({percent}) — {outcome}"
            if outcome == "Vulnerable":
                remediation = DETECTOR_POOL.get(detector, "Validation/Monitoring")
                line += f"\n            Recommended Remediation: {remediation}"
            evaluation_lines.append(line)

        evaluation_str = "\n".join(evaluation_lines)

        SET_header = f"{SET_name}:\n    Description: {description}\n"
        SET_header += f"    Total runs: {total_runs}. {less_than_100_runs if total_runs != 'unknown' and int(total_runs) < 100 else more_than_100_runs if total_runs != 'unknown' else ''}\n"
        SET_header += f"    Remediation: {SET.get('SET_remediation', 'No remediation provided.')}\n\n"
        SET_header += f"    Evaluation:\n{evaluation_str}\n"
        SETs_section += SET_header

    output_text = f"""Overview:
This penetration test evaluation report is for model '{report.get("model_name", "unknown")}' of type '{report.get("model_type", "unknown")}' with run ID '{report.get("run_id", "unknown")}'.
The runtime for this test was {report.get("run_length", "unknown")}.

{SETs_section if SETs_section else 'No SETs were executed during this test run.'}"""

    return output_text


def summarize_vuln_SETs(json_input: Union[str, dict, Path]) -> List[Dict]:
    """
    Extract only vulnerable SETs from a JSON report.
    Returns a list of SETs with:
      - description
      - overall_pass_percentage (for vulnerable detectors only)
    SETs where all detectors are 'Resisted' are skipped.
    """
    # Load input
    if isinstance(json_input, Path) or (isinstance(json_input, str) and Path(json_input).exists()):
        try:
            report = json.loads(Path(json_input).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Error reading JSON file {json_input}: {e}")
            return []
    elif isinstance(json_input, str):
        try:
            report = json.loads(json_input)
        except Exception as e:
            print(f"Invalid JSON string: {e}")
            return []
    elif isinstance(json_input, dict):
        report = json_input
    else:
        print("Input must be a JSON file path, string, or dict")
        return []

    summary = []

    for SET in report.get("SETs", []):
        description = SET.get("description", "No description available.")

        # Keep only vulnerable detectors
        vulnerable_results = [
            ev for ev in SET.get("evaluation_results", [])
            if ev.get("outcome", "").lower() != "resisted"
        ]

        if vulnerable_results:
            total_passed = sum(ev.get("passed_count", 0) for ev in vulnerable_results)
            total_tests = sum(ev.get("total_count", 0) for ev in vulnerable_results)
            overall_pass_rate = f"{(total_passed / total_tests) * 100:.1f}%" if total_tests else "N/A"

            summary.append({
                "SET_name": SET.get("SET_classname", "unknown"),
                "description": description,
                "outcome": "Vulnerable",
                "overall_pass_percentage": overall_pass_rate
            })
    
    remediations = report.get("recommended_remediations", [])
    if remediations:
        summary.append({
            "recommended_remediations": remediations
        })

    # If no vulnerabilities were found, return a single note
    if not summary:
        summary.append({
            "note": "No vulnerabilities were found in the evaluated SETs."
        })

    return summary

def add_notes(summary: str) -> str:
    # Add any additional notes or disclaimers to the summary
    # add variability of results due to AI stochasticity
    # add recommendation for larger number of runs
    # add disclaimer about false positives/negatives
    # add recommendation for human review
    return summary + "\n\n### Note: The results of these tests may vary due to the inherent stochasticity of AI models. It is recommended to conduct a larger number of runs for a more comprehensive assessment. Additionally, while automated tests provide valuable insights, they may produce false positives or negatives; therefore, human review is advised for critical evaluations."


def create_html_file(content: str, filename: str = "output.html") -> None:
    """
    Creates an HTML file containing the given string.

    :param content: The HTML content to write into the file.
    :param filename: The name of the HTML file to create.
    """
    with open(filename, "w", encoding="utf-8") as file:
        file.write(content)

def run_evaluation_pipeline(json_report_path: Path, output_html_path: Path) -> None:
    """
    Full pipeline to load a JSON report, generate a summary, and save it as an HTML file.
    """
    report = load_jsonl_safely(json_report_path)[0]  # Assuming single report per file
    report_string = generate_report_string(report)
    summary = summarize_vuln_SETs(report)
    summary_str = json.dumps(summary, indent=2)
    ai_inference = run(summary_str)
    final_summary = report_string + "\n\n" + ai_inference
    final_summary_with_notes = add_notes(final_summary)
    create_html_file(final_summary_with_notes, output_html_path)