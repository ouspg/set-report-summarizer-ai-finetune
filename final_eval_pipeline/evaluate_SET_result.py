import json
from pathlib import Path
from typing import Union, List, Dict

from set_descriptions import SET_DESCRIPTIONS, DETECTOR_POOL
from format_html import create_html_file


def load_json_safely(path):
    """
    Load a JSON file safely. Works with multi-line JSON.
    Returns the parsed dictionary, or None if failed.
    """
    path = Path(path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"⚠️ Failed to parse JSON: {e}")
        return None


def generate_report_string(report):
    """
    Convert a single JSON report into a human-readable string.
    """
    SETs_section = ""

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
            evaluation_lines.append(line)

        evaluation_str = "\n".join(evaluation_lines)

        SET_header = f"{SET_name}:\n    Description: {description}\n"
        SET_header += f"    Total runs: {total_runs}.\n"
        SET_header += f"    Evaluation:\n{evaluation_str}\n"
        SET_header += f"    Recommended Remediation: {SET.get('SET_remediation', 'No remediation provided.')}\n\n"
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
    """
    
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
                "total_runs": SET.get("total_runs", "unknown"),
                "outcome": "Vulnerable",
                "overall_pass_percentage": overall_pass_rate
            })

    remediations = report.get("recommended_remediations", [])
    if remediations:
        summary.append({
            "recommended_remediations": remediations
        })

    if not summary:
        summary.append({
            "note": "No vulnerabilities were found in the evaluated SETs."
        })

    return summary

def add_notes(report: dict, summary: List[Dict], text: str) -> str:
    """
    Add dynamic notes about stochasticity and general disclaimers.
    summary: list of vulnerable SET dicts
    """
    low_run_sets = []
    
    for s in summary:
        if "SET_name" not in s:
            continue
        
        total_runs = s.get("total_runs", "unknown")
        try:
            total_runs_int = int(total_runs)
        except (ValueError, TypeError):
            continue

        if total_runs_int < 100:
            low_run_sets.append(s.get("SET_name", "Unknown SET"))

    note_lines = ["### Notes:"]

    # Stochasticity / Run count
    if low_run_sets:
        note_lines.append(
            "- The following SETs had fewer than 100 runs and their results may vary due to AI stochasticity: "
            + ", ".join(low_run_sets) + "."
        )
        note_lines.append("- It is recommended to conduct a larger number of runs for a more comprehensive assessment.")
    else:
        note_lines.append("- All SETs had over 100 runs, reducing AI stochasticity and generating more reliable results.")

    # Human review
    note_lines.append("- Automated tests may produce false positives or negatives; human review is advised for critical evaluations.")

    return text + "\n\n" + "\n".join(note_lines)


def run_evaluation_pipeline(json_report_path: str, output_html_dir: str) -> None:
    """
    Full pipeline: load JSON report, generate summaries, run AI inference if needed, and create HTML.
    """

    SCRIPT_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = SCRIPT_DIR.parent  # ai-pentest-report-finetuning-pipeline

    json_report_path = (PROJECT_ROOT / json_report_path).resolve()
    if not json_report_path.exists():
        print(f"[ERROR] JSON report not found: {json_report_path}")
        return
    
    report = load_json_safely(json_report_path)
    if report is None:
        print("No valid JSON report loaded. Exiting.")
        return

    report_string = generate_report_string(report)
    summary = summarize_vuln_SETs(report)
    summary_str = json.dumps(summary, indent=2)

    try:
        from inference import run

        result = run(summary_str)
        if isinstance(result, dict):
            ai_inference = result.get("output") or next(iter(result.values()))
        else:
            ai_inference = result


    except Exception as e:
        # Capture the error type and message
        error_type = type(e).__name__
        error_msg = str(e)
        
        # Provide a clear explanation inside the AI output
        ai_inference = (
            "## Issue Summary:\n"
            "AI summarization failed due to an internal error.\n\n"
            f"Error Type: {error_type}\n"
            f"Error Message: {error_msg}\n"
            "Please check the model, inputs, or device configuration and retry."
        )


    final_summary = report_string + "\n\n" + ai_inference
    final_summary_with_notes = add_notes(report, summary, final_summary)

    output_html_dir = (PROJECT_ROOT / output_html_dir).resolve()
    output_html_dir.mkdir(parents=True, exist_ok=True)  # ensure directory exists

    input_path = Path(json_report_path)
    output_file = output_html_dir / f"{input_path.stem}_report.html"

    create_html_file(final_summary_with_notes, output_file)

    print(f"[INFO] Generated report: {output_file}")

run_evaluation_pipeline(
    "data/generated_runs/fbad4102-2f0e-407a-ba8e-9d3d4dffe1ab.generated.json",
    "data/html_outputs/"
)
