"""
LM Studio CSV Processor
A Gradio interface for processing CSV files using LM Studio's local server
"""

import gradio as gr
import pandas as pd
import requests
import json
from typing import Optional, Tuple
import io
import tempfile
import os


class LMStudioClient:
    """Client for interacting with LM Studio's local server"""

    def __init__(self, base_url: str = "http://localhost:1234"):
        self.base_url = base_url
        self.chat_endpoint = f"{base_url}/v1/chat/completions"
        self.models_endpoint = f"{base_url}/v1/models"

    def get_available_models(self) -> list:
        """Get list of available models from LM Studio"""
        try:
            response = requests.get(self.models_endpoint, timeout=5)
            response.raise_for_status()
            data = response.json()
            return [model['id'] for model in data.get('data', [])]
        except Exception as e:
            print(f"Error fetching models: {e}")
            return []

    def chat_completion(self, prompt: str, model: str = None, temperature: float = 0.7) -> Optional[str]:
        """Send a chat completion request to LM Studio"""
        try:
            payload = {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that analyzes data and provides concise summaries."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": temperature,
                "max_tokens": 500
            }

            # Only add model if specified
            if model:
                payload["model"] = model

            response = requests.post(
                self.chat_endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            response.raise_for_status()

            data = response.json()
            return data['choices'][0]['message']['content'].strip()

        except Exception as e:
            return f"Error: {str(e)}"


def detect_primary_key(df: pd.DataFrame) -> str:
    """Detect the most likely primary key column"""
    # Check for common primary key column names
    common_pk_names = ['id', 'ID', 'Id', 'key', 'Key', 'primary_key', 'pk',
                       'index', 'Index', 'record_id', 'row_id']

    for col in df.columns:
        if col.lower() in [name.lower() for name in common_pk_names]:
            return col

    # If no common name found, use the first column
    return df.columns[0]


def sanitize_for_csv(text: str) -> str:
    """
    Sanitize text to ensure it fits in a single CSV cell
    Replaces newlines, special characters, and fixes encoding issues
    """
    if not isinstance(text, str):
        return str(text)

    # Replace common Unicode characters that cause encoding issues
    replacements = {
        '\u2014': '-',      # em dash
        '\u2013': '-',      # en dash
        '\u2018': "'",      # left single quote
        '\u2019': "'",      # right single quote
        '\u201c': '"',      # left double quote
        '\u201d': '"',      # right double quote
        '\u2026': '...',    # ellipsis
        '\u2022': '*',      # bullet
        '\u00a0': ' ',      # non-breaking space
        '\u00ad': '-',      # soft hyphen
    }

    for old_char, new_char in replacements.items():
        text = text.replace(old_char, new_char)

    # Replace newlines, carriage returns, and tabs with spaces
    cleaned = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')

    # Replace multiple spaces with single space
    cleaned = ' '.join(cleaned.split())

    return cleaned.strip()


def process_csv(
    file,
    prompt_template: str,
    model_name: str = None,
    temperature: float = 0.7,
    progress=gr.Progress()
) -> Tuple[Optional[str], str]:
    """
    Process CSV file through LM Studio

    Args:
        file: Uploaded CSV file
        prompt_template: Template for prompts (use {row_data} as placeholder)
        model_name: Name of the model to use
        temperature: Temperature for generation
        progress: Gradio progress tracker

    Returns:
        Tuple of (output CSV path, status message)
    """
    try:
        # Read the CSV file
        df = pd.read_csv(file.name)

        if df.empty:
            return None, "Error: The uploaded CSV file is empty."

        # Detect primary key
        pk_column = detect_primary_key(df)
        status_msg = f"Processing {len(df)} rows. Detected primary key: '{pk_column}'\n\n"

        # Initialize LM Studio client
        client = LMStudioClient()

        # Prepare results
        summaries = []
        primary_keys = []

        # Process each row
        for idx, row in progress.tqdm(df.iterrows(), total=len(df), desc="Processing rows"):
            # Get primary key value
            pk_value = row[pk_column]
            primary_keys.append(pk_value)

            # Create row data string
            row_data = "\n".join([f"{col}: {val}" for col, val in row.items()])

            # Create prompt from template
            if "{row_data}" in prompt_template:
                prompt = prompt_template.replace("{row_data}", row_data)
            else:
                # If no placeholder, just append the row data
                prompt = f"{prompt_template}\n\nData:\n{row_data}"

            # Get summary from LM Studio
            summary = client.chat_completion(prompt, model=model_name, temperature=temperature)

            # Sanitize the summary to ensure it's a single line (no page breaks)
            sanitized_summary = sanitize_for_csv(summary)
            summaries.append(sanitized_summary)

            progress((idx + 1) / len(df), desc=f"Processed {idx + 1}/{len(df)} rows")

        # Create output DataFrame
        output_df = pd.DataFrame({
            pk_column: primary_keys,
            'Summary': summaries
        })

        # Save to CSV in system temp directory (cross-platform compatible)
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, "processed_output.csv")
        # Use utf-8-sig encoding (UTF-8 with BOM) for proper Windows/Excel compatibility
        output_df.to_csv(output_path, index=False, encoding='utf-8-sig')

        status_msg += f"✓ Successfully processed {len(df)} rows!\n"
        status_msg += f"✓ Output saved with primary key '{pk_column}' for cross-matching."

        return output_path, status_msg

    except Exception as e:
        return None, f"Error processing CSV: {str(e)}"


def create_interface():
    """Create and configure the Gradio interface"""

    # Initialize client to check connection
    client = LMStudioClient()

    with gr.Blocks(title="LM Studio CSV Processor") as demo:
        gr.Markdown("# 🤖 LM Studio CSV Processor")
        gr.Markdown(
            "Upload a CSV file and process each row through your local LM Studio model. "
            "The output will include the primary key for easy cross-matching."
        )

        with gr.Row():
            with gr.Column():
                # Input components
                file_input = gr.File(
                    label="Upload CSV File",
                    file_types=[".csv"],
                    type="filepath"
                )

                prompt_input = gr.Textbox(
                    label="Prompt Template",
                    placeholder="Enter your prompt here. Use {row_data} to insert the row data.",
                    value="Please provide a concise summary of the following data:\n\n{row_data}",
                    lines=5
                )

                model_input = gr.Textbox(
                    label="Model Name (optional)",
                    placeholder="Leave empty to use the loaded model",
                    value=""
                )

                temperature_input = gr.Slider(
                    label="Temperature",
                    minimum=0.0,
                    maximum=2.0,
                    value=0.7,
                    step=0.1
                )

                process_btn = gr.Button("Process CSV", variant="primary")

            with gr.Column():
                # Output components
                status_output = gr.Textbox(
                    label="Status",
                    lines=10,
                    interactive=False
                )

                file_output = gr.File(
                    label="Download Processed CSV"
                )

        # Add examples
        gr.Markdown("### 💡 Tips")
        gr.Markdown(
            "- The app will automatically detect the primary key (ID column)\n"
            "- Use `{row_data}` in your prompt template to insert row data\n"
            "- Adjust temperature for more creative (higher) or focused (lower) responses\n"
            "- Make sure LM Studio server is running at http://localhost:1234"
        )

        # Example prompts
        gr.Examples(
            examples=[
                ["Summarize this data in one sentence:\n\n{row_data}"],
                ["Analyze the following record and provide key insights:\n\n{row_data}"],
                ["Extract the most important information from:\n\n{row_data}"],
            ],
            inputs=prompt_input,
            label="Example Prompts"
        )

        # Connect the processing function
        process_btn.click(
            fn=process_csv,
            inputs=[file_input, prompt_input, model_input, temperature_input],
            outputs=[file_output, status_output]
        )

    return demo


if __name__ == "__main__":
    # Create and launch the interface
    demo = create_interface()
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True
    )
