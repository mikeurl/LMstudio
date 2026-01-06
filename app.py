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
    """Create and configure the Gradio interface with modern glass-morphism design"""

    # Custom CSS for glass-morphism and modern look
    custom_css = """
    body {
        background: #0b0f19;
    }
    .gradio-container {
        background: #0b0f19 !important;
    }
    /* Glassmorphism for the main panels */
    .glass-panel {
        background: rgba(255, 255, 255, 0.04) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
    }
    /* The Orange Action Button */
    #process-btn {
        background: linear-gradient(90deg, #ff6b3d, #ff9e75) !important;
        border: none;
        color: white;
        font-weight: bold;
        box-shadow: 0 4px 15px rgba(255, 107, 61, 0.4);
        transition: 0.3s;
    }
    #process-btn:hover {
        box-shadow: 0 6px 20px rgba(255, 107, 61, 0.6);
        transform: translateY(-2px);
    }
    /* Text coloring */
    label { color: #ccc !important; }
    span { color: #ccc !important; }
    .prose { color: #ddd !important; }
    /* Input fields background */
    textarea, input {
        background-color: rgba(0, 0, 0, 0.3) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: white !important;
    }
    /* Example buttons styling */
    .example-btn {
        background: rgba(255, 107, 61, 0.1) !important;
        border: 1px solid rgba(255, 107, 61, 0.3) !important;
        color: #ff9e75 !important;
    }
    .example-btn:hover {
        background: rgba(255, 107, 61, 0.2) !important;
    }
    """

    with gr.Blocks(theme=gr.themes.Soft(), css=custom_css, title="LM Studio CSV Processor") as demo:

        # Header
        with gr.Row():
            gr.Markdown("## 🤖 LM Studio CSV Processor\nUpload a CSV file and process each row through your local LM Studio model.")

        with gr.Row():

            # LEFT COLUMN (Inputs)
            with gr.Column(scale=2, elem_classes="glass-panel"):

                # File Upload
                file_input = gr.File(
                    label="Upload CSV File",
                    file_types=[".csv"],
                    type="filepath",
                    height=100
                )

                # Prompt Template
                prompt_input = gr.Textbox(
                    label="Prompt Template",
                    placeholder="Enter your prompt here. Use {row_data} to insert data...",
                    lines=5,
                    value="Please provide a concise summary of the following data:\n\n{row_data}"
                )

                # Model & Temperature
                model_input = gr.Textbox(
                    label="Model Name (optional)",
                    placeholder="Leave empty to use loaded model"
                )

                temperature_input = gr.Slider(
                    minimum=0.0,
                    maximum=2.0,
                    value=0.7,
                    step=0.1,
                    label="Temperature"
                )

                # The Big Orange Button
                process_btn = gr.Button("Process CSV", elem_id="process-btn", size="lg")

                # Tips Section
                gr.Markdown("### 💡 Tips")
                gr.Markdown(
                    """
                    * The app automatically detects the ID column.
                    * Use `{row_data}` in your prompt to insert the CSV row.
                    * Ensure LM Studio server is running at `http://localhost:1234`.
                    """
                )

                # Example Prompts (Clickable buttons)
                gr.Markdown("### 📝 Example Prompts")
                with gr.Row():
                    ex_btn1 = gr.Button("Summarize", size="sm", elem_classes="example-btn")
                    ex_btn2 = gr.Button("Analyze Sentiment", size="sm", elem_classes="example-btn")
                    ex_btn3 = gr.Button("Extract Key Info", size="sm", elem_classes="example-btn")

            # RIGHT COLUMN (Outputs)
            with gr.Column(scale=2):

                # Status Box
                with gr.Group(elem_classes="glass-panel"):
                    gr.Markdown("### Status")
                    status_output = gr.Textbox(
                        label="",
                        placeholder="Waiting for process to start...",
                        lines=10,
                        interactive=False,
                        show_copy_button=True
                    )

                # Spacer
                gr.Markdown("<br>")

                # Download Box
                with gr.Group(elem_classes="glass-panel"):
                    gr.Markdown("### 📄 Download Processed CSV")
                    file_output = gr.File(label="Output", interactive=False)

        # Event Wiring - Main Process Button
        process_btn.click(
            fn=process_csv,
            inputs=[file_input, prompt_input, model_input, temperature_input],
            outputs=[file_output, status_output]
        )

        # Example Prompt Buttons
        ex_btn1.click(
            lambda: "Summarize this data in one sentence:\n\n{row_data}",
            None,
            prompt_input
        )
        ex_btn2.click(
            lambda: "Analyze the sentiment of the following data:\n\n{row_data}",
            None,
            prompt_input
        )
        ex_btn3.click(
            lambda: "Extract the most important information from:\n\n{row_data}",
            None,
            prompt_input
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
