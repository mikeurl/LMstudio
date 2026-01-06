# LM Studio CSV Processor

A Gradio-based web interface for processing CSV files using LM Studio's local server. Upload a CSV, and let your local LLM analyze and summarize each row.

## Features

- 📁 Upload CSV files for batch processing
- 🤖 Automatic detection of primary key columns for cross-matching
- ✏️ Customizable prompt templates
- 🎚️ Adjustable temperature settings
- 💾 Download processed results as CSV
- 🔄 Progress tracking for large files

## Prerequisites

1. **LM Studio** installed and running
   - Download from: https://lmstudio.ai/
   - Load a model (e.g., openai/gpt-oss-20b)
   - Start the local server (default: http://localhost:1234)

2. **Python 3.8+** installed

## Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### 1. Start LM Studio Server

1. Open LM Studio
2. Load your preferred model
3. Click on "Local Server" in the left sidebar
4. Click "Start Server"
5. Verify it's running at `http://localhost:1234`

### 2. Run the Application

```bash
python app.py
```

The application will start at: `http://127.0.0.1:7860`

### 3. Process Your CSV

1. **Upload CSV**: Click "Upload CSV File" and select your file
2. **Configure Prompt**: Customize the prompt template (use `{row_data}` placeholder)
3. **Set Parameters**: Adjust temperature and optionally specify model name
4. **Process**: Click "Process CSV" button
5. **Download**: Once complete, download the processed CSV file

## Prompt Templates

Use `{row_data}` as a placeholder for the row data in your prompts:

**Example 1 - Basic Summary**
```
Summarize this data in one sentence:

{row_data}
```

**Example 2 - Structured Analysis**
```
Analyze the following record and provide:
1. Key points
2. Potential issues
3. Recommendations

{row_data}
```

**Example 3 - Specific Extraction**
```
Extract the sentiment and main topic from:

{row_data}
```

## Output Format

The processed CSV will contain:
- **Primary Key Column**: Automatically detected (e.g., 'id', 'ID', 'key', or first column)
- **Summary Column**: LLM-generated summary for each row

This format makes it easy to cross-match results with your original data.

## Configuration

### Temperature
- **0.0-0.3**: More focused and deterministic
- **0.4-0.7**: Balanced (default: 0.7)
- **0.8-2.0**: More creative and varied

### Model Name
- Leave empty to use the currently loaded model
- Or specify a model identifier from LM Studio

## Troubleshooting

### "Connection Error"
- Ensure LM Studio server is running
- Check that the server is at `http://localhost:1234`
- Verify a model is loaded in LM Studio

### "Timeout Error"
- For large prompts, increase the timeout in `app.py`
- Try a smaller batch or simpler prompts

### "Empty Response"
- Check LM Studio console for errors
- Ensure the model is fully loaded
- Try reducing temperature or simplifying the prompt

## Technical Details

### Endpoints Used
- `GET /v1/models` - List available models
- `POST /v1/chat/completions` - Process individual rows

### Primary Key Detection
The app automatically detects primary keys by:
1. Looking for common column names: 'id', 'ID', 'key', 'primary_key', etc.
2. Falling back to the first column if no match found

## Windows-Specific Notes

- Use PowerShell or Command Prompt to run the application
- If you encounter permission issues, run as administrator
- Ensure Python is added to your PATH

## Example Workflow

1. You have `customers.csv` with columns: `customer_id`, `name`, `feedback`
2. Upload the file to the Gradio interface
3. Use prompt: "Analyze this customer feedback and categorize the sentiment: {row_data}"
4. Process and download `processed_output.csv`
5. Result will have: `customer_id` and `Summary` columns
6. Cross-match summaries back to your original data using `customer_id`

## License

MIT License - Feel free to modify and distribute

## Support

For issues with:
- **This application**: Check the error messages in the Status box
- **LM Studio**: Visit https://lmstudio.ai/docs
- **OpenAI API format**: See https://lmstudio.ai/docs/developer/openai-compat

## Credits

Built with:
- [Gradio](https://gradio.app/) - Web interface
- [LM Studio](https://lmstudio.ai/) - Local LLM server
- [Pandas](https://pandas.pydata.org/) - Data processing
